"""
Main Pipeline for YouTube Book Reader Data Processing
Orchestrates the entire workflow: fetch subtitles -> segment -> generate posts -> save to DB
"""

import argparse
from typing import Optional
from datetime import datetime

from config import PROCESSING_CONFIG
from database import DatabaseManager
from youtube_fetcher import YouTubeSubtitleFetcher
from text_segmenter import SmartTextSegmenter
from ai_generator import AIContentGenerator


class YouTubeBookPipeline:
    def __init__(self, db_config: dict = None):
        self.db = DatabaseManager()
        self.fetcher = YouTubeSubtitleFetcher()
        self.segmenter = SmartTextSegmenter()
        self.generator = AIContentGenerator()
    
    def process_video(self, video_url_or_id: str, 
                     language: str = 'vi',
                     generate_posts: bool = True,
                     post_limit: int = 10,
                     skip_if_exists: bool = False) -> dict:
        """
        Process a YouTube video end-to-end
        
        Args:
            video_url_or_id: YouTube URL or video ID
            language: Preferred subtitle language
            generate_posts: Whether to generate AI posts
            post_limit: Maximum number of posts to generate
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
            subtitles = self.fetcher.fetch_subtitles(video_url_or_id, language, use_demo_data=True)
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
            
            # Step 4: Generate AI posts (if enabled)
            if generate_posts:
                print("\n🤖 STEP 4: Generating AI posts...")
                print("-" * 50)
                
                # Use best segments for post generation
                segments_to_process = best_segments if best_segments else segments[:post_limit]
                
                posts = self.generator.generate_multiple_posts(
                    segments_to_process,
                    video_info=video_data,
                    limit=post_limit
                )
                
                # Convert to quote format for database
                quotes = [
                    {
                        'content': post['content'],
                        'is_visible': post['is_visible']
                    }
                    for post in posts
                ]
                
                # Save quotes to database
                self.db.save_quotes(video_db_id, quotes)
                results['quotes_count'] = len(quotes)
            
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
    
    def regenerate_posts(self, video_db_id: int, limit: int = 10):
        """Regenerate AI posts for an existing video"""
        print(f"\n🔄 Regenerating posts for video DB ID: {video_db_id}")
        
        # Get video info
        cursor = self.db.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM youtube_videos WHERE id = %s", (video_db_id,))
        video = cursor.fetchone()
        cursor.close()
        
        if not video:
            print(f"❌ Video with ID {video_db_id} not found")
            return
        
        # Get paragraphs
        paragraphs = self.db.get_paragraphs(video_db_id)
        
        if not paragraphs:
            print("❌ No paragraphs found for this video")
            return
        
        # Convert paragraphs back to segment format
        segments = [
            {
                'content': p['content'],
                'content_raw': p['content_raw'],
                'context_before': '',
                'context_after': '',
                'score': 0.5
            }
            for p in paragraphs
        ]
        
        # Generate new posts
        video_info = {
            'title': video.get('title', 'Unknown'),
            'channel_title': video.get('channel_title', 'Unknown')
        }
        
        posts = self.generator.generate_multiple_posts(
            segments,
            video_info=video_info,
            limit=limit
        )
        
        # Save to database
        quotes = [
            {
                'content': post['content'],
                'is_visible': post['is_visible']
            }
            for post in posts
        ]
        
        self.db.save_quotes(video_db_id, quotes)
        print(f"✅ Generated {len(quotes)} new posts")
    
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
  python main.py --video SYwXwiuxO-0 --no-generate-posts
  python main.py --video SYwXwiuxO-0 --post-limit 5
  python main.py --regenerate --video-db-id 1
        """
    )
    
    parser.add_argument('--video', type=str, help='YouTube video URL or ID')
    parser.add_argument('--language', type=str, default='vi', 
                       help='Preferred subtitle language (default: vi)')
    parser.add_argument('--no-generate-posts', action='store_true',
                       help='Skip AI post generation')
    parser.add_argument('--post-limit', type=int, default=10,
                       help='Maximum number of posts to generate (default: 10)')
    parser.add_argument('--skip-if-exists', action='store_true',
                       help='Skip processing if video already exists')
    parser.add_argument('--regenerate', action='store_true',
                       help='Regenerate posts for existing video')
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
            pipeline.regenerate_posts(args.video_db_id, limit=args.post_limit)
        elif args.video:
            results = pipeline.process_video(
                video_url_or_id=args.video,
                language=args.language,
                generate_posts=not args.no_generate_posts,
                post_limit=args.post_limit,
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
