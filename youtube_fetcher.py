"""
YouTube Subtitle/Transcript Downloader
Fetches subtitles from YouTube videos using youtube-transcript-api library
More reliable than direct HTTP requests for most use cases
"""

import json
import re
import os
import requests
from typing import List, Dict, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable


class YouTubeSubtitleFetcher:
    def __init__(self, cookies_file: str = 'cookies.txt'):
        # YouTubeTranscriptApi is a static class, no need to instantiate
        self.cookies_file = cookies_file
        self.session = None
        if os.path.exists(cookies_file):
            self._load_cookies()
        else:
            print(f"⚠️  Cookie file not found: {cookies_file}")
            print("   To fetch real subtitles from YouTube on this server, you need to:")
            print("   1. Export cookies from your browser using 'Get cookies.txt LOCALLY' extension")
            print("   2. Save as 'cookies.txt' in the project directory")
            print("   3. Re-run the script")

    def _load_cookies(self):
        """Load cookies from Netscape format file"""
        try:
            self.session = requests.Session()
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
        Fetch subtitles/transcript from a YouTube video using youtube-transcript-api
        """
        # FORCE DISABLE DEMO MODE - Always fetch real data from YouTube
        if use_demo_data:
            print("⚠️  WARNING: use_demo_data=True ignored. Forcing REAL YouTube API call...")
        
        video_id = self.extract_video_id(video_url_or_id)

        # Define languages to try
        languages_to_try = []
        if language:
            languages_to_try.append(language)
        else:
            languages_to_try.append('vi')
        
        # Add fallback languages
        languages_to_try.extend(['en', 'vi-auto', 'en-auto'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_languages = []
        for lang in languages_to_try:
            if lang not in seen:
                seen.add(lang)
                unique_languages.append(lang)

        print(f"Fetching subtitles for video ID: {video_id}")
        print(f"Trying languages: {unique_languages}")

        # Try each language
        for lang_code in unique_languages:
            try:
                print(f"  → Trying language: {lang_code}")
                
                # Handle auto-generated vs manual captions
                if '-auto' in lang_code:
                    base_lang = lang_code.replace('-auto', '')
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    
                    # Look for auto-generated transcript
                    try:
                        transcript = transcript_list.find_manually_created_transcript([base_lang])
                        print(f"    ✓ Found manual transcript for {base_lang}, using it instead of auto")
                    except NoTranscriptFound:
                        try:
                            transcript = transcript_list.find_generated_transcript([base_lang])
                            print(f"    ✓ Found auto-generated transcript for {base_lang}")
                        except NoTranscriptFound:
                            print(f"    ✗ No transcript found for {base_lang}")
                            continue
                else:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    try:
                        # Try manual first
                        transcript = transcript_list.find_manually_created_transcript([lang_code])
                        print(f"    ✓ Found manual transcript for {lang_code}")
                    except NoTranscriptFound:
                        try:
                            # Fall back to auto-generated
                            transcript = transcript_list.find_generated_transcript([lang_code])
                            print(f"    ✓ Found auto-generated transcript for {lang_code}")
                        except NoTranscriptFound:
                            print(f"    ✗ No transcript found for {lang_code}")
                            continue
                
                # Fetch the actual transcript data
                transcript_data = transcript.fetch()
                
                if transcript_data:
                    print(f"✓ Successfully fetched {len(transcript_data)} subtitle segments in {lang_code}")
                    
                    # Normalize format to match expected structure
                    normalized = []
                    for item in transcript_data:
                        normalized.append({
                            'text': item['text'],
                            'start': item['start'],
                            'duration': item['duration']
                        })
                    
                    return normalized
                    
            except TranscriptsDisabled:
                print(f"  ✗ Transcripts disabled for this video")
                continue
            except VideoUnavailable:
                print(f"  ✗ Video unavailable")
                continue
            except Exception as e:
                print(f"  ✗ Error with {lang_code}: {e}")
                continue
        
        # If all languages fail
        print("✗ No subtitles found in any language")
        
        # Only use demo data if explicitly requested AND all real attempts failed
        if use_demo_data:
            print("📝 Falling back to demo data (all real attempts failed)...")
            return self._get_demo_transcript()
        
        return []

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
