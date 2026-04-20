"""
Database Manager for YouTube Book Reader Data Pipeline
Handles all MySQL operations for videos, paragraphs, and quotes
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from config import DB_CONFIG


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("✓ Connected to MySQL database")
        except Error as e:
            print(f"✗ Error connecting to MySQL: {e}")
            raise
    
    def ensure_connection(self):
        """Ensure database connection is active"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✓ Database connection closed")
    
    # ==================== VIDEO OPERATIONS ====================
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """Get video record by YouTube video_id"""
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM youtube_videos 
                WHERE video_id = %s
            """, (video_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
    
    def create_or_update_video(self, video_data: Dict) -> int:
        """Create new video or update existing one"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        try:
            # Check if video exists
            existing = self.get_video_by_id(video_data['video_id'])
            
            if existing:
                # Update existing video
                cursor.execute("""
                    UPDATE youtube_videos 
                    SET title = %s, description = %s, channel_title = %s,
                        thumbnail = %s, publish_time = %s, published_at = %s,
                        snippet = %s, updated_at = %s
                    WHERE video_id = %s
                """, (
                    video_data.get('title'),
                    video_data.get('description'),
                    video_data.get('channel_title'),
                    video_data.get('thumbnail'),
                    video_data.get('publish_time'),
                    video_data.get('published_at'),
                    json.dumps(video_data.get('snippet', {})),
                    datetime.now(),
                    video_data['video_id']
                ))
                video_id = existing['id']
                print(f"✓ Updated video: {video_data['title']}")
            else:
                # Insert new video
                now = datetime.now()
                cursor.execute("""
                    INSERT INTO youtube_videos 
                    (kind, etag, video_id, channel_id, channel_title, title, 
                     description, thumbnail, publish_time, published_at, 
                     snippet, created_at, updated_at, fahasa_book_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    video_data.get('kind'),
                    video_data.get('etag'),
                    video_data['video_id'],
                    video_data.get('channel_id'),
                    video_data.get('channel_title'),
                    video_data.get('title'),
                    video_data.get('description'),
                    video_data.get('thumbnail'),
                    video_data.get('publish_time'),
                    video_data.get('published_at'),
                    json.dumps(video_data.get('snippet', {})),
                    now,
                    now,
                    video_data.get('fahasa_book_id')
                ))
                video_id = cursor.lastrowid
                print(f"✓ Created video: {video_data['title']}")
            
            self.connection.commit()
            return video_id
        finally:
            cursor.close()
    
    def get_video_db_id(self, video_id: str) -> Optional[int]:
        """Get database ID for a YouTube video"""
        video = self.get_video_by_id(video_id)
        return video['id'] if video else None
    
    # ==================== PARAGRAPH OPERATIONS ====================
    
    def clear_paragraphs(self, video_db_id: int):
        """Clear all paragraphs for a video"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                DELETE FROM youtube_paragraphs 
                WHERE youtube_video_id = %s
            """, (video_db_id,))
            self.connection.commit()
            print(f"✓ Cleared paragraphs for video ID {video_db_id}")
        finally:
            cursor.close()
    
    def save_paragraphs(self, video_db_id: int, paragraphs: List[Dict]):
        """Save multiple paragraphs for a video"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        try:
            # Clear existing paragraphs first
            self.clear_paragraphs(video_db_id)
            
            now = datetime.now()
            for idx, para in enumerate(paragraphs, 1):
                cursor.execute("""
                    INSERT INTO youtube_paragraphs 
                    (ordinal_number, content_raw, content, youtube_video_id, 
                     created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    idx,
                    para.get('content_raw', ''),
                    para.get('content', ''),
                    video_db_id,
                    now,
                    now
                ))
            
            self.connection.commit()
            print(f"✓ Saved {len(paragraphs)} paragraphs for video ID {video_db_id}")
        finally:
            cursor.close()
    
    def get_paragraphs(self, video_db_id: int) -> List[Dict]:
        """Get all paragraphs for a video"""
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM youtube_paragraphs 
                WHERE youtube_video_id = %s 
                ORDER BY ordinal_number ASC
            """, (video_db_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
    
    # ==================== QUOTE OPERATIONS ====================
    
    def clear_quotes(self, video_db_id: int):
        """Clear all quotes for a video"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                DELETE FROM youtube_quotes 
                WHERE youtube_video_id = %s
            """, (video_db_id,))
            self.connection.commit()
            print(f"✓ Cleared quotes for video ID {video_db_id}")
        finally:
            cursor.close()
    
    def save_quotes(self, video_db_id: int, quotes: List[Dict]):
        """Save multiple quotes (AI-generated posts) for a video"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        try:
            # Clear existing quotes first
            self.clear_quotes(video_db_id)
            
            now = datetime.now()
            for idx, quote in enumerate(quotes, 1):
                cursor.execute("""
                    INSERT INTO youtube_quotes 
                    (ordinal_number, content, is_visible, youtube_video_id, 
                     created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    idx,
                    quote.get('content', ''),
                    quote.get('is_visible', 1),
                    video_db_id,
                    now,
                    now
                ))
            
            self.connection.commit()
            print(f"✓ Saved {len(quotes)} quotes for video ID {video_db_id}")
        finally:
            cursor.close()
    
    def get_quotes(self, video_db_id: int, visible_only: bool = False) -> List[Dict]:
        """Get all quotes for a video"""
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        try:
            if visible_only:
                cursor.execute("""
                    SELECT * FROM youtube_quotes 
                    WHERE youtube_video_id = %s AND is_visible = 1
                    ORDER BY ordinal_number ASC
                """, (video_db_id,))
            else:
                cursor.execute("""
                    SELECT * FROM youtube_quotes 
                    WHERE youtube_video_id = %s 
                    ORDER BY ordinal_number ASC
                """, (video_db_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
    
    def update_quote_visibility(self, quote_id: int, is_visible: bool):
        """Update visibility status of a quote"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                UPDATE youtube_quotes 
                SET is_visible = %s, updated_at = %s 
                WHERE id = %s
            """, (is_visible, datetime.now(), quote_id))
            self.connection.commit()
        finally:
            cursor.close()
