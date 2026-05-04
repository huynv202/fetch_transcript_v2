"""
Main Pipeline for YouTube Book Reader Data Processing
Orchestrates the entire workflow: fetch subtitles -> segment -> save paragraphs -> extract quotes -> save to DB
"""

import argparse
from typing import Optional
from datetime import datetime

from config import PROCESSING_CONFIG
from database import DatabaseManager
from youtube_fetcher import YouTubeSubtitleFetcher
from text_segmenter import SmartTextSegmenter
from quote_extractor import QuoteExtractor


class YouTubeBookPipeline:
    def __init__(self, db_config: dict = None):
        self.db = DatabaseManager()
        self.fetcher = YouTubeSubtitleFetcher()
        self.segmenter = SmartTextSegmenter()
        self.quote_extractor = QuoteExtractor()
    
    def process_video(self, video_url_or_id: str, 
                     language: str = 'vi',
                     extract_quotes: bool = True,
                     max_quotes: int = 10,
                     skip_if_exists: bool = False) -> dict:
        """
        Process a YouTube video end-to-end
        
        Args:
            video_url_or_id: YouTube URL or video ID
            language: Preferred subtitle language
            extract_quotes: Whether to extract quotes using AI
            max_quotes: Maximum number of quotes to extract
            skip_if_exists: Skip if video already processed
        
        Returns:
            Dict with processing results and statistics
        """
        print("\n" + "=" * 70)
        print(f"PROCESSING VIDEO: {video_url_or_id}")
        print("=" * 70 + "\n")
        
        results = {
            'video_id': None,
            'video_db_id': None,
            'video_info': {},
            'subtitles_count': 0,
            'paragraphs_count': 0,
            'quotes_count': 0,
            'success': False,
            'errors': []
        }
        
        try:
            # Step 1: Fetch subtitles
            print("📥 STEP 1: Fetching subtitles...")
            print("-" * 50)
            print(f"Fetching REAL subtitles for video: {video_url_or_id} (language: {language})")
            print("⚠️  DEMO MODE DISABLED - Calling YouTube API directly...")
            
            # Force fetch real data (use_demo_data=True will be ignored)
            subtitles = self.fetcher.fetch_subtitles(video_url_or_id, language, use_demo_data=True)
            
            if not subtitles:
                raise Exception("No subtitles found for this video")
            
            # Print raw subtitle info
            print(f"\n✅ SUCCESS! Received {len(subtitles)} subtitle segments.")
            full_text_list = [item['text'] for item in subtitles]
            full_text_combined = " ".join(full_text_list)
            print(f"📊 Total characters: {len(full_text_combined)}")
            if subtitles:
                last_end = subtitles[-1]['start'] + subtitles[-1]['duration']
                print(f"⏱️  Estimated duration: {last_end:.0f} seconds ({last_end/60:.1f} minutes)")
            
            # Print first few segments as sample
            print("\n📄 SAMPLE RAW SEGMENTS (First 5):")
            print("-" * 30)
            for i, sub in enumerate(subtitles[:5]):
                print(f"[{i}] {sub['start']:.2f}s: {sub['text']}")
            if len(subtitles) > 5:
                print(f"... (and {len(subtitles) - 5} more segments)")
            print("-" * 30)
            
            results['subtitles_count'] = len(subtitles)
            
            if not subtitles:
                raise Exception("No subtitles found for this video")
            
            # Extract video ID for later use
            video_id = self.fetcher.extract_video_id(video_url_or_id)
            results['video_id'] = video_id
            
            # Get full text for processing
            full_text = self.fetcher.get_full_text(subtitles)
            
            # Step 2: Save/Update video metadata
            print("\n💾 STEP 2: Saving video metadata...")
            print("-" * 50)
            
            # Check if video exists
            existing_video = self.db.get_video_by_youtube_id(video_id)
            
            video_data = {
                'video_id': video_id,
                'title': f"Video {video_id}",  # Will be updated if YouTube API available
                'channel_title': 'Unknown',
                'description': full_text[:500] if len(full_text) > 500 else full_text,
                'published_at': datetime.now(),
                'publish_time': datetime.now(),
                'snippet': {'subtitles_language': language}
            }
            
            video_db_id = self.db.create_or_update_video(video_data)
            results['video_db_id'] = video_db_id
            results['video_info'] = video_data
            
            if existing_video and skip_if_exists:
                print("⚠ Video already exists and skip_if_exists is True. Skipping...")
                return results
            
            # Step 3: Create smart segments
            print("\n✂️ STEP 3: Creating smart text segments...")
            print("-" * 50)
            
            segments = self.segmenter.create_segments_from_subtitles(subtitles)
            print(f"Created {len(segments)} segments")
            
            # Score and filter segments
            best_segments = self.segmenter.get_best_segments(
                segments, 
                threshold=PROCESSING_CONFIG['quote_selection_threshold']
            )
            print(f"Best segments (score >= {PROCESSING_CONFIG['quote_selection_threshold']}): {len(best_segments)}")
            
            # Prepare paragraphs for database
            all_paragraphs = self.segmenter.export_for_display(segments)
            
            # Save paragraphs to database
            self.db.save_paragraphs(video_db_id, all_paragraphs)
            results['paragraphs_count'] = len(all_paragraphs)
            
            # Step 4: Extract quotes from paragraphs using AI (if enabled)
            if extract_quotes:
                print("\n🤖 STEP 4: Extracting quotes from paragraphs using AI...")
                print("-" * 50)
                
                # Extract quotes from all paragraphs
                quotes = self.quote_extractor.extract_quotes_from_paragraphs(
                    all_paragraphs,
                    video_info=video_data,
                    max_quotes_total=max_quotes
                )
                
                # Save quotes to database
                if quotes:
                    self.db.save_quotes(video_db_id, quotes)
                    results['quotes_count'] = len(quotes)
                    print(f"✓ Saved {len(quotes)} quotes to database")
                else:
                    print("⚠ No quotes were extracted")
            
            results['success'] = True
            
            # Print summary
            print("\n" + "=" * 70)
            print("✅ PROCESSING COMPLETE!")
            print("=" * 70)
            print(f"Video ID: {video_id}")
            print(f"Database ID: {video_db_id}")
            print(f"Subtitles fetched: {results['subtitles_count']} segments")
            print(f"Paragraphs saved: {results['paragraphs_count']}")
            print(f"Quotes/Posts generated: {results['quotes_count']}")
            print("=" * 70 + "\n")
        
        except Exception as e:
            results['errors'].append(str(e))
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def regenerate_quotes(self, video_db_id: int, max_quotes: int = 10):
        """Regenerate quotes for an existing video"""
        print(f"\n🔄 Regenerating quotes for video DB ID: {video_db_id}")
        
        # Get video info
        cursor = self.db.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM youtube_videos WHERE id = %s", (video_db_id,))
        video = cursor.fetchone()
        cursor.close()
        
        if not video:
            print(f"❌ Video with ID {video_db_id} not found")
            return
        
        # Get paragraphs
        cursor = self.db.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM youtube_paragraphs WHERE youtube_video_id = %s ORDER BY ordinal_number", (video_db_id,))
        paragraphs = cursor.fetchall()
        cursor.close()
        
        if not paragraphs:
            print("❌ No paragraphs found for this video")
            return
        
        # Extract new quotes
        video_info = {
            'title': video.get('title', 'Unknown'),
            'channel_title': video.get('channel_title', 'Unknown')
        }
        
        quotes = self.quote_extractor.extract_quotes_from_paragraphs(
            paragraphs,
            video_info=video_info,
            max_quotes_total=max_quotes
        )
        
        # Save to database
        if quotes:
            self.db.save_quotes(video_db_id, quotes)
            print(f"✅ Generated {len(quotes)} new quotes")
        else:
            print("⚠ No quotes were extracted")
    
    def close(self):
        """Clean up resources"""
        self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description='YouTube Book Reader Data Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --video SYwXwiuxO-0
  python main.py --video https://youtube.com/watch?v=SYwXwiuxO-0 --language vi
  python main.py --video SYwXwiuxO-0 --no-extract-quotes
  python main.py --video SYwXwiuxO-0 --max-quotes 5
  python main.py --regenerate --video-db-id 1
        """
    )
    
    parser.add_argument('--video', type=str, help='YouTube video URL or ID')
    parser.add_argument('--language', type=str, default='vi', 
                       help='Preferred subtitle language (default: vi)')
    parser.add_argument('--no-extract-quotes', action='store_true',
                       help='Skip AI quote extraction')
    parser.add_argument('--max-quotes', type=int, default=10,
                       help='Maximum number of quotes to extract (default: 10)')
    parser.add_argument('--skip-if-exists', action='store_true',
                       help='Skip processing if video already exists')
    parser.add_argument('--regenerate', action='store_true',
                       help='Regenerate quotes for existing video')
    parser.add_argument('--video-db-id', type=int,
                       help='Database video ID (for regeneration)')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = YouTubeBookPipeline()
    
    try:
        if args.regenerate:
            if not args.video_db_id:
                print("❌ Error: --video-db-id is required for regeneration")
                return
            pipeline.regenerate_quotes(args.video_db_id, max_quotes=args.max_quotes)
        elif args.video:
            results = pipeline.process_video(
                video_url_or_id=args.video,
                language=args.language,
                extract_quotes=not args.no_extract_quotes,
                max_quotes=args.max_quotes,
                skip_if_exists=args.skip_if_exists
            )
            
            if not results['success']:
                print("\n❌ Processing failed with errors:")
                for error in results['errors']:
                    print(f"  - {error}")
        else:
            parser.print_help()
    
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
