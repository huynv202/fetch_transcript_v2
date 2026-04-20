"""
YouTube Subtitle/Transcript Downloader
Fetches subtitles from YouTube videos using direct HTTP requests
Supports cookie-based authentication to bypass IP blocks
"""

import json
import re
import requests
from typing import List, Dict, Optional
from config import YOUTUBE_CONFIG


class YouTubeSubtitleFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
        self.use_cookies = YOUTUBE_CONFIG.get('use_cookies', False)
        self.cookies_file = YOUTUBE_CONFIG.get('cookies_file', 'cookies.txt')
        
        if self.use_cookies:
            self._load_cookies()

    def _load_cookies(self):
        """Load cookies from Netscape format file"""
        try:
            with open(self.cookies_file, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 6:
                        domain, path, secure, expiry, name, value = parts[:6]
                        if domain.startswith('.'):
                            domain = domain[1:]
                        self.session.cookies.set(
                            name, value, domain=domain, path=path, 
                            secure=(secure == 'TRUE')
                        )
            print(f"✓ Loaded cookies from {self.cookies_file}")
        except FileNotFoundError:
            print(f"⚠ Cookie file not found: {self.cookies_file}")
        except Exception as e:
            print(f"⚠ Error loading cookies: {e}")

    def extract_video_id(self, url_or_id: str) -> str:
        """Extract video ID from YouTube URL or return if already an ID"""
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id

        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract video ID from: {url_or_id}")

    def fetch_subtitles(self, video_url_or_id: str,
                       language: Optional[str] = None,
                       use_demo_data: bool = False) -> List[Dict]:
        """
        Fetch subtitles/transcript from a YouTube video
        """
        if use_demo_data:
            print("📝 Using DEMO MODE with sample transcript data...")
            return self._get_demo_transcript()

        video_id = self.extract_video_id(video_url_or_id)

        languages_to_try = []
        if language:
            languages_to_try.append(language)
        else:
            languages_to_try.append(YOUTUBE_CONFIG['default_language'])
        
        languages_to_try.extend(YOUTUBE_CONFIG['fallback_languages'])
        
        seen = set()
        unique_languages = []
        for lang in languages_to_try:
            if lang not in seen:
                seen.add(lang)
                unique_languages.append(lang)

        print(f"Fetching subtitles for video ID: {video_id}")
        print(f"Trying languages: {unique_languages}")

        try:
            # Get video page HTML
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Extract player response from HTML
            player_response = None
            
            # Try multiple patterns to find ytInitialPlayerResponse
            patterns = [
                r'var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\});',
                r'ytInitialPlayerResponse\s*=\s*(\{.+?\});',
            ]
            
            for pattern in patterns:
                for match in re.finditer(pattern, response.text):
                    try:
                        json_str = match.group(1)
                        # Find matching braces
                        brace_count = 0
                        start_idx = 0
                        for i, char in enumerate(json_str):
                            if char == '{':
                                if brace_count == 0:
                                    start_idx = i
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = json_str[start_idx:i+1]
                                    break
                        
                        player_response = json.loads(json_str)
                        break
                    except json.JSONDecodeError:
                        continue
                
                if player_response:
                    break
            
            if not player_response:
                raise Exception("Could not extract player response from video page")
            
            # Check if video is available
            playability = player_response.get('playabilityStatus', {})
            status = playability.get('status', '')
            
            if status != 'OK':
                reason = playability.get('reason', 'Unknown error')
                raise Exception(f"Video not available: {reason}")
            
            # Get caption tracks
            captions = player_response.get('captions', {})
            if not captions:
                raise Exception("No captions found for this video")
            
            caption_renderer = captions.get('playerCaptionsTracklistRenderer', {})
            caption_tracks = caption_renderer.get('captionTracks', [])
            
            if not caption_tracks:
                raise Exception("No caption tracks available")
            
            # Find best language track
            selected_track = None
            for lang in unique_languages:
                for track in caption_tracks:
                    lang_code = track.get('languageCode', '')
                    if lang_code.startswith(lang):
                        selected_track = track
                        print(f"  ✓ Found track for language: {lang_code}")
                        break
                if selected_track:
                    break
            
            if not selected_track:
                # Use first available track
                selected_track = caption_tracks[0]
                lang_code = selected_track.get('languageCode', 'unknown')
                print(f"⚠ Using fallback language: {lang_code}")
            
            # Get caption URL
            caption_url = selected_track.get('baseUrl', '')
            if not caption_url:
                raise Exception("No caption URL found")
            
            # Add format parameter for JSON response
            if '&fmt=' not in caption_url:
                caption_url += '&fmt=json3'
            
            # Fetch caption data
            caption_response = self.session.get(caption_url, timeout=10)
            caption_response.raise_for_status()
            
            caption_data = caption_response.json()
            
            # Parse captions
            subtitles = []
            events = caption_data.get('events', [])
            
            for event in events:
                if 'segs' not in event:
                    continue
                
                text_parts = []
                for seg in event.get('segs', []):
                    utf_text = seg.get('utf8', '')
                    if utf_text:
                        text_parts.append(utf_text)
                
                if text_parts:
                    text = ''.join(text_parts)
                    # Clean up text
                    text = text.replace('\\n', '\n').replace('&#39;', "'")
                    text = text.replace('&quot;', '"').replace('&amp;', '&').strip()
                    
                    if text:
                        start_ms = event.get('tStartMs', 0)
                        duration_ms = event.get('dDurationMs', 0)
                        
                        subtitles.append({
                            'text': text,
                            'start': start_ms / 1000.0,
                            'duration': duration_ms / 1000.0
                        })
            
            if subtitles:
                print(f"✓ Successfully fetched {len(subtitles)} subtitle segments")
                return subtitles
            else:
                raise Exception("No valid subtitle content found")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Network error: {e}")
            raise Exception(f"Network error while fetching subtitles: {e}")
        except json.JSONDecodeError as e:
            print(f"✗ JSON parsing error: {e}")
            raise Exception(f"Error parsing subtitle data: {e}")
        except Exception as e:
            print(f"✗ Error: {e}")
            if use_demo_data:
                print("📝 Falling back to demo data...")
                return self._get_demo_transcript()
            raise

    def _normalize_subtitles(self, transcript: List) -> List[Dict]:
        """Normalize subtitle format"""
        normalized = []
        for segment in transcript:
            if isinstance(segment, dict):
                normalized.append({
                    'text': segment.get('text', ''),
                    'start': segment.get('start', 0),
                    'duration': segment.get('duration', 0)
                })
        return normalized

    def _get_demo_transcript(self) -> List[Dict]:
        """Demo transcript for testing"""
        return [
            {'text': 'Xin chào các bạn, hôm nay chúng ta sẽ đọc cuốn sách rất hay.', 'start': 0.0, 'duration': 4.0},
            {'text': 'Đây là câu chuyện về lòng dũng cảm và sự kiên trì.', 'start': 4.0, 'duration': 3.5},
            {'text': 'Nhân vật chính đã vượt qua nhiều khó khăn để đạt được ước mơ.', 'start': 7.5, 'duration': 4.0},
            {'text': 'Bài học rút ra là không bao giờ từ bỏ trước thất bại.', 'start': 11.5, 'duration': 3.5},
            {'text': 'Hãy cùng nhau khám phá những trang sách đầy cảm hứng này.', 'start': 15.0, 'duration': 4.0},
        ]

    def get_full_text(self, subtitles: List[Dict]) -> str:
        """Combine all subtitle segments into full text"""
        if not subtitles:
            return ""
        
        # Join all text segments
        texts = [seg['text'] for seg in subtitles if seg.get('text')]
        return ' '.join(texts)
