"""
YouTube Subtitle/Transcript Downloader
Fetches subtitles from YouTube videos using youtube-transcript-api
Supports cookie-based authentication to bypass IP blocks
"""

from typing import List, Dict, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled, 
    NoTranscriptFound, 
    VideoUnavailable,
    RequestBlocked
)
import re

from config import YOUTUBE_CONFIG


class YouTubeSubtitleFetcher:
    def __init__(self):
        self.api = YouTubeTranscriptApi()  # New API uses instance method
        self.use_cookies = YOUTUBE_CONFIG.get('use_cookies', False)
        self.cookies_file = YOUTUBE_CONFIG.get('cookies_file', 'cookies.txt')
    
    def extract_video_id(self, url_or_id: str) -> str:
        """Extract video ID from YouTube URL or return if already an ID"""
        # If it's already a video ID (11 characters, alphanumeric with _ and -)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id
        
        # Handle various YouTube URL formats
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
        
        Args:
            video_url_or_id: YouTube URL or video ID
            language: Preferred language code (e.g., 'vi', 'en')
            use_demo_data: If True, use sample data for testing without API call
        
        Returns:
            List of subtitle segments with 'text', 'start', 'duration'
        """
        # Demo mode for testing when YouTube blocks IP
        if use_demo_data:
            print("📝 Using DEMO MODE with sample transcript data...")
            return self._get_demo_transcript()
        
        video_id = self.extract_video_id(video_url_or_id)
        
        # Determine languages to try
        languages_to_try = []
        if language:
            languages_to_try.append(language)
        else:
            languages_to_try.append(YOUTUBE_CONFIG['default_language'])
        
        # Add fallback languages
        languages_to_try.extend(YOUTUBE_CONFIG['fallback_languages'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_languages = []
        for lang in languages_to_try:
            if lang not in seen:
                seen.add(lang)
                unique_languages.append(lang)
        
        print(f"Fetching subtitles for video ID: {video_id}")
        print(f"Trying languages: {unique_languages}")
        if self.use_cookies:
            print(f"Using cookies from: {self.cookies_file}")
        
        last_error = None
        for lang in unique_languages:
            try:
                # New API: use fetch method directly with languages parameter
                transcript = self.api.fetch(video_id, languages=[lang])
                print(f"✓ Successfully fetched {len(transcript)} subtitle segments in '{lang}'")
                return self._normalize_subtitles(transcript)
            
            except NoTranscriptFound:
                print(f"  - No transcript found for language: {lang}")
                continue
            except TranscriptsDisabled:
                print(f"  - Transcripts are disabled for this video")
                break
            except RequestBlocked as e:
                error_msg = str(e)
                print(f"  ⚠ YouTube blocked request for '{lang}': IP may be blocked")
                last_error = e
                if not self.use_cookies:
                    print(f"  💡 TIP: Set use_cookies=True in config and provide cookies.txt to bypass this")
                continue
            except Exception as e:
                error_msg = str(e)
                print(f"  - Error fetching '{lang}': {str(e)[:100]}...")
                last_error = e
                continue
        
        # If all attempts failed, try to get any available transcript
        try:
            print("  - Trying to fetch any available transcript (no language filter)...")
            transcript = self.api.fetch(video_id)
            print(f"✓ Fetched auto-selected transcript: success ({len(transcript)} segments)")
            return self._normalize_subtitles(transcript)
        
        except Exception as e:
            error_msg = str(e)
            print(f"✗ Failed to fetch any transcript: {error_msg[:200]}")
            
            if isinstance(e, RequestBlocked) or "IP has been blocked" in error_msg or "cloud provider" in error_msg:
                print("\n" + "="*60)
                print("YOUTUBE IP BLOCK DETECTED!")
                print("="*60)
                print("\nTo fix this, you have two options:")
                print("\n1. USE COOKIES (Recommended for development):")
                print("   - Install browser extension: 'Get cookies.txt LOCALLY'")
                print("   - Go to youtube.com and export cookies to cookies.txt")
                print("   - Set use_cookies=True in config.py")
                print("\n2. USE A PROXY:")
                print("   - Configure proxy in your environment")
                print("   - Or run this script from a non-cloud IP address")
                print("="*60 + "\n")
            
            # Raise the last error encountered
            if last_error:
                raise last_error
            raise
        
        raise NoTranscriptFound(f"No transcripts available for video: {video_id}")
    
    def _normalize_subtitles(self, subtitles: List) -> List[Dict]:
        """Normalize subtitle format"""
        normalized = []
        for sub in subtitles:
            if isinstance(sub, dict):
                normalized.append({
                    'text': sub.get('text', '').strip(),
                    'start': sub.get('start', 0),
                    'duration': sub.get('duration', 0)
                })
            else:
                # Handle tuple/list format from API
                normalized.append({
                    'text': sub.text if hasattr(sub, 'text') else str(sub),
                    'start': sub.start if hasattr(sub, 'start') else 0,
                    'duration': sub.duration if hasattr(sub, 'duration') else 0
                })
        
        # Filter out empty segments
        return [s for s in normalized if s['text']]
    
    def get_full_text(self, subtitles: List[Dict]) -> str:
        """Combine all subtitle segments into full text"""
        return ' '.join([sub['text'] for sub in subtitles])
    
    def get_metadata(self, video_url_or_id: str) -> Dict:
        """Get basic metadata about available transcripts"""
        video_id = self.extract_video_id(video_url_or_id)
        
        try:
            transcript_list = self.api.list_transcripts(video_id)
            transcripts_info = []
            
            for transcript in transcript_list:
                transcripts_info.append({
                    'language_code': transcript.language_code,
                    'language_name': transcript.language,
                    'is_generated': transcript.is_generated,
                    'is_translatable': transcript.is_translatable
                })
            
            return {
                'video_id': video_id,
                'available_transcripts': transcripts_info,
                'count': len(transcripts_info)
            }
        
        except Exception as e:
            return {
                'video_id': video_id,
                'error': str(e),
                'available_transcripts': []
            }


    def _get_demo_transcript(self) -> List[Dict]:
        """Demo transcript data for testing when YouTube API is blocked."""
        demo_segments = [
            {"text": "Xin chào các bạn, hôm nay mình sẽ đọc cho các bạn nghe một đoạn trích rất hay từ cuốn sách Đắc Nhân Tâm.", "start": 0.0, "duration": 5.5},
            {"text": "Đây là cuốn sách đã thay đổi cuộc đời của hàng triệu người trên thế giới.", "start": 5.5, "duration": 4.0},
            {"text": "Tác giả Dale Carnegie đã đúc kết những nguyên tắc vàng trong giao tiếp và ứng xử.", "start": 9.5, "duration": 5.0},
            {"text": "Nguyên tắc đầu tiên: Không chỉ trích, không than phiền, không oán trách.", "start": 14.5, "duration": 5.5},
            {"text": "Vì sao vậy? Vì chỉ trích giống như bắn chim bồ câu, nó không giải quyết được gì mà chỉ làm tổn thương người khác.", "start": 20.0, "duration": 7.0},
            {"text": "Thay vào đó, hãy tìm hiểu và thông cảm với hoàn cảnh của họ.", "start": 27.0, "duration": 4.5},
            {"text": "Một ví dụ điển hình là Abraham Lincoln. Thời trẻ ông hay chỉ trích người khác.", "start": 31.5, "duration": 5.5},
            {"text": "Nhưng sau nhiều trải nghiệm, ông nhận ra rằng chỉ trích như ong đốt, chỉ làm đau mà không có lợi.", "start": 37.0, "duration": 6.0},
            {"text": "Từ đó ông thay đổi và trở thành một trong những tổng thống vĩ đại nhất nước Mỹ.", "start": 43.0, "duration": 5.0},
            {"text": "Nguyên tắc thứ hai: Thành thật khen ngợi người khác.", "start": 48.0, "duration": 4.0},
            {"text": "Ai cũng khao khát được công nhận và trân trọng.", "start": 52.0, "duration": 3.5},
            {"text": "Một lời khen chân thành có thể thay đổi cả ngày của một người.", "start": 55.5, "duration": 4.5},
            {"text": "Nhưng hãy nhớ, khen phải chân thành, không nịnh hót.", "start": 60.0, "duration": 4.0},
            {"text": "Hãy tìm điểm tốt thực sự trong người khác và khen từ trái tim.", "start": 64.0, "duration": 4.5},
            {"text": "Cuối cùng, hãy luôn mỉm cười khi gặp gỡ người khác.", "start": 68.5, "duration": 4.0},
            {"text": "Nụ cười là ngôn ngữ chung mà ai cũng hiểu được.", "start": 72.5, "duration": 3.5},
            {"text": "Nó nói lên rằng: Tôi thích bạn, tôi vui khi gặp bạn.", "start": 76.0, "duration": 4.0},
            {"text": "Đó là cách đơn giản nhất để tạo ấn tượng tốt đẹp ngay từ lần đầu gặp mặt.", "start": 80.0, "duration": 5.0},
            {"text": "Cảm ơn các bạn đã lắng nghe. Hẹn gặp lại trong những video tiếp theo!", "start": 85.0, "duration": 5.0}
        ]
        return demo_segments

# Example usage
if __name__ == "__main__":
    fetcher = YouTubeSubtitleFetcher()
    
    # Test with the provided video
    video_id = "SYwXwiuxO-0"
    
    print("=" * 60)
    print("Testing YouTube Subtitle Fetcher")
    print("=" * 60)
    
    # Get metadata first
    metadata = fetcher.get_metadata(video_id)
    print(f"\nMetadata for video {video_id}:")
    print(f"  Available transcripts: {metadata.get('count', 0)}")
    for t in metadata.get('available_transcripts', []):
        print(f"    - {t['language_name']} ({t['language_code']}) - {'Auto' if t['is_generated'] else 'Manual'}")
    
    # Fetch subtitles
    try:
        subtitles = fetcher.fetch_subtitles(video_id, language='vi')
        
        print(f"\nFetched {len(subtitles)} subtitle segments")
        print("\nFirst 5 segments:")
        for i, sub in enumerate(subtitles[:5], 1):
            print(f"  {i}. [{sub['start']:.1f}s] {sub['text'][:80]}...")
        
        full_text = fetcher.get_full_text(subtitles)
        print(f"\nFull text length: {len(full_text)} characters")
        print(f"First 200 chars: {full_text[:200]}...")
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")

    def _get_demo_transcript(self) -> List[Dict]:
        """
        Demo transcript data for testing when YouTube API is blocked.
        This simulates a Vietnamese book reading video transcript.
        """
        demo_segments = [
            {"text": "Xin chào các bạn, hôm nay mình sẽ đọc cho các bạn nghe một đoạn trích rất hay từ cuốn sách Đắc Nhân Tâm.", "start": 0.0, "duration": 5.5},
            {"text": "Đây là cuốn sách đã thay đổi cuộc đời của hàng triệu người trên thế giới.", "start": 5.5, "duration": 4.0},
            {"text": "Tác giả Dale Carnegie đã đúc kết những nguyên tắc vàng trong giao tiếp và ứng xử.", "start": 9.5, "duration": 5.0},
            {"text": "Nguyên tắc đầu tiên: Không chỉ trích, không than phiền, không oán trách.", "start": 14.5, "duration": 5.5},
            {"text": "Vì sao vậy? Vì chỉ trích giống như bắn chim bồ câu, nó không giải quyết được gì mà chỉ làm tổn thương người khác.", "start": 20.0, "duration": 7.0},
            {"text": "Thay vào đó, hãy tìm hiểu và thông cảm với hoàn cảnh của họ.", "start": 27.0, "duration": 4.5},
            {"text": "Một ví dụ điển hình là Abraham Lincoln. Thời trẻ ông hay chỉ trích người khác.", "start": 31.5, "duration": 5.5},
            {"text": "Nhưng sau nhiều trải nghiệm, ông nhận ra rằng chỉ trích như ong đốt, chỉ làm đau mà không có lợi.", "start": 37.0, "duration": 6.0},
            {"text": "Từ đó ông thay đổi và trở thành một trong những tổng thống vĩ đại nhất nước Mỹ.", "start": 43.0, "duration": 5.0},
            {"text": "Nguyên tắc thứ hai: Thành thật khen ngợi người khác.", "start": 48.0, "duration": 4.0},
            {"text": "Ai cũng khao khát được công nhận và trân trọng.", "start": 52.0, "duration": 3.5},
            {"text": "Một lời khen chân thành có thể thay đổi cả ngày của một người.", "start": 55.5, "duration": 4.5},
            {"text": "Nhưng hãy nhớ, khen phải chân thành, không nịnh hót.", "start": 60.0, "duration": 4.0},
            {"text": "Hãy tìm điểm tốt thực sự trong người khác và khen từ trái tim.", "start": 64.0, "duration": 4.5},
            {"text": "Cuối cùng, hãy luôn mỉm cười khi gặp gỡ người khác.", "start": 68.5, "duration": 4.0},
            {"text": "Nụ cười là ngôn ngữ chung mà ai cũng hiểu được.", "start": 72.5, "duration": 3.5},
            {"text": "Nó nói lên rằng: Tôi thích bạn, tôi vui khi gặp bạn.", "start": 76.0, "duration": 4.0},
            {"text": "Đó là cách đơn giản nhất để tạo ấn tượng tốt đẹp ngay từ lần đầu gặp mặt.", "start": 80.0, "duration": 5.0},
            {"text": "Cảm ơn các bạn đã lắng nghe. Hẹn gặp lại trong những video tiếp theo!", "start": 85.0, "duration": 5.0}
        ]
        return demo_segments
