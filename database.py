"""
Database Manager - Supports both MySQL and SQLite
Handles youtube_videos, youtube_paragraphs, youtube_quotes tables
"""

import mysql.connector
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from config import DB_CONFIG, USE_SQLITE, SQLITE_DB_PATH


class DatabaseManager:
    def __init__(self):
        self.use_sqlite = USE_SQLITE
        self.connection = None
        self.cursor = None
        
        if self.use_sqlite:
            self._init_sqlite()
        else:
            self._connect_mysql()
    
    def _init_sqlite(self):
        """Initialize SQLite database and create tables if not exist"""
        self.connection = sqlite3.connect(SQLITE_DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        
        # Create youtube_videos table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS youtube_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT,
                etag TEXT,
                video_id TEXT UNIQUE,
                channel_id TEXT,
                channel_title TEXT,
                title TEXT,
                description TEXT,
                thumbnail TEXT,
                publish_time TIMESTAMP,
                published_at TIMESTAMP,
                snippet TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                fahasa_book_id INTEGER
            )
        ''')
        
        # Create youtube_paragraphs table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS youtube_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ordinal_number INTEGER,
                content_raw TEXT,
                content TEXT,
                youtube_video_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (youtube_video_id) REFERENCES youtube_videos(id)
            )
        ''')
        
        # Create youtube_quotes table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS youtube_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ordinal_number INTEGER,
                content TEXT,
                is_visible INTEGER DEFAULT 1,
                youtube_video_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (youtube_video_id) REFERENCES youtube_videos(id)
            )
        ''')
        
        # Create youtube_subtitle_cues table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS youtube_subtitle_cues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                youtube_video_id TEXT NOT NULL,
                cue_index INTEGER NOT NULL,
                start_time_seconds DECIMAL(10,3) NOT NULL,
                end_time_seconds DECIMAL(10,3) NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        
        # Create indexes
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON youtube_videos(video_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_paragraph_video ON youtube_paragraphs(youtube_video_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_quote_video ON youtube_quotes(youtube_video_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_cue_video ON youtube_subtitle_cues(youtube_video_id)')
        
        self.connection.commit()
        print(f"✓ SQLite database initialized at {SQLITE_DB_PATH}")
    
    def _connect_mysql(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            print("✓ Connected to MySQL database")
        except mysql.connector.Error as err:
            print(f"✗ Error connecting to MySQL: {err}")
            print("→ Falling back to SQLite...")
            self.use_sqlite = True
            self._init_sqlite()
    
    def ensure_connection(self):
        """Ensure database connection is active"""
        if self.use_sqlite:
            return
        if not self.connection or not self.connection.is_connected():
            self._connect_mysql()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            if self.use_sqlite:
                self.connection.close()
            elif self.connection.is_connected():
                self.connection.close()
            print("✓ Database connection closed")

    # ==================== VIDEO OPERATIONS ====================

    def get_video_by_youtube_id(self, video_id: str) -> Optional[Dict]:
        """Get video record by YouTube video_id"""
        self.ensure_connection()
        if self.use_sqlite:
            self.cursor.execute("SELECT * FROM youtube_videos WHERE video_id = ?", (video_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        else:
            self.cursor.execute("SELECT * FROM youtube_videos WHERE video_id = %s", (video_id,))
            return self.cursor.fetchone()

    def create_or_update_video(self, video_data: Dict) -> int:
        """Create new video or update existing one, returns video ID"""
        self.ensure_connection()
        now = datetime.now()
        
        if self.use_sqlite:
            # Check if exists
            existing = self.get_video_by_youtube_id(video_data['video_id'])
            if existing:
                self.cursor.execute("""
                    UPDATE youtube_videos SET 
                        title=?, channel_title=?, description=?, thumbnail=?,
                        publish_time=?, published_at=?, snippet=?, updated_at=?
                    WHERE video_id=?
                """, (
                    video_data.get('title'), video_data.get('channel_title'),
                    video_data.get('description'), video_data.get('thumbnail'),
                    video_data.get('publish_time'), video_data.get('published_at'),
                    json.dumps(video_data.get('snippet', {})) if video_data.get('snippet') else None,
                    now, video_data['video_id']
                ))
                self.connection.commit()
                return existing['id']
            else:
                self.cursor.execute("""
                    INSERT INTO youtube_videos 
                    (kind, etag, video_id, channel_id, channel_title, title, description, 
                     thumbnail, publish_time, published_at, snippet, created_at, updated_at, fahasa_book_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_data.get('kind'), video_data.get('etag'), video_data['video_id'],
                    video_data.get('channel_id'), video_data.get('channel_title'),
                    video_data.get('title'), video_data.get('description'),
                    video_data.get('thumbnail'), video_data.get('publish_time'),
                    video_data.get('published_at'),
                    json.dumps(video_data.get('snippet', {})) if video_data.get('snippet') else None,
                    now, now, video_data.get('fahasa_book_id')
                ))
                self.connection.commit()
                return self.cursor.lastrowid
        else:
            # MySQL version
            self.cursor.execute("""
                SELECT id FROM youtube_videos WHERE video_id = %s
            """, (video_data['video_id'],))
            existing = self.cursor.fetchone()
            
            if existing:
                self.cursor.execute("""
                    UPDATE youtube_videos SET 
                        title=%s, channel_title=%s, description=%s, thumbnail=%s,
                        publish_time=%s, published_at=%s, snippet=%s, updated_at=%s
                    WHERE video_id=%s
                """, (
                    video_data.get('title'), video_data.get('channel_title'),
                    video_data.get('description'), video_data.get('thumbnail'),
                    video_data.get('publish_time'), video_data.get('published_at'),
                    json.dumps(video_data.get('snippet', {})) if video_data.get('snippet') else None,
                    now, video_data['video_id']
                ))
                self.connection.commit()
                return existing['id']
            else:
                self.cursor.execute("""
                    INSERT INTO youtube_videos 
                    (kind, etag, video_id, channel_id, channel_title, title, description, 
                     thumbnail, publish_time, published_at, snippet, created_at, updated_at, fahasa_book_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    video_data.get('kind'), video_data.get('etag'), video_data['video_id'],
                    video_data.get('channel_id'), video_data.get('channel_title'),
                    video_data.get('title'), video_data.get('description'),
                    video_data.get('thumbnail'), video_data.get('publish_time'),
                    video_data.get('published_at'),
                    json.dumps(video_data.get('snippet', {})) if video_data.get('snippet') else None,
                    now, now, video_data.get('fahasa_book_id')
                ))
                self.connection.commit()
                return self.cursor.lastrowid

    # ==================== PARAGRAPH OPERATIONS ====================

    def save_paragraphs(self, video_id: int, paragraphs: List[Dict]) -> int:
        """Save multiple paragraphs for a video"""
        self.ensure_connection()
        now = datetime.now()
        count = 0
        
        # Delete existing paragraphs for this video
        if self.use_sqlite:
            self.cursor.execute("DELETE FROM youtube_paragraphs WHERE youtube_video_id = ?", (video_id,))
        else:
            self.cursor.execute("DELETE FROM youtube_paragraphs WHERE youtube_video_id = %s", (video_id,))
        
        for para in paragraphs:
            if self.use_sqlite:
                self.cursor.execute("""
                    INSERT INTO youtube_paragraphs 
                    (ordinal_number, content_raw, content, youtube_video_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    para.get('ordinal_number'), para.get('content_raw'),
                    para.get('content'), video_id, now, now
                ))
            else:
                self.cursor.execute("""
                    INSERT INTO youtube_paragraphs 
                    (ordinal_number, content_raw, content, youtube_video_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    para.get('ordinal_number'), para.get('content_raw'),
                    para.get('content'), video_id, now, now
                ))
            count += 1
        
        if self.use_sqlite:
            self.connection.commit()
        else:
            self.connection.commit()
        
        return count

    # ==================== SUBTITLE CUE OPERATIONS ====================

    def save_subtitle_cues(self, video_id: str, cues: List[Dict]) -> int:
        """Save multiple subtitle cues for a video"""
        self.ensure_connection()
        now = datetime.now()
        count = 0
        
        # Delete existing cues for this video
        if self.use_sqlite:
            self.cursor.execute("DELETE FROM youtube_subtitle_cues WHERE youtube_video_id = ?", (video_id,))
        else:
            self.cursor.execute("DELETE FROM youtube_subtitle_cues WHERE youtube_video_id = %s", (video_id,))
        
        for idx, cue in enumerate(cues):
            if self.use_sqlite:
                self.cursor.execute("""
                    INSERT INTO youtube_subtitle_cues 
                    (youtube_video_id, cue_index, start_time_seconds, end_time_seconds, text, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id, 
                    idx, 
                    cue.get('start'), 
                    cue.get('start') + cue.get('duration'),
                    cue.get('text'), 
                    now, 
                    now
                ))
            else:
                self.cursor.execute("""
                    INSERT INTO youtube_subtitle_cues 
                    (youtube_video_id, cue_index, start_time_seconds, end_time_seconds, text, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    video_id, 
                    idx, 
                    cue.get('start'), 
                    cue.get('start') + cue.get('duration'),
                    cue.get('text'), 
                    now, 
                    now
                ))
            count += 1
        
        if self.use_sqlite:
            self.connection.commit()
        else:
            self.connection.commit()
        
        return count

    def get_cues_by_video(self, video_id: str) -> List[Dict]:
        """Get all subtitle cues for a specific video"""
        self.ensure_connection()
        if self.use_sqlite:
            self.cursor.execute(
                "SELECT * FROM youtube_subtitle_cues WHERE youtube_video_id = ? ORDER BY cue_index", 
                (video_id,)
            )
            return [dict(row) for row in self.cursor.fetchall()]
        else:
            self.cursor.execute(
                "SELECT * FROM youtube_subtitle_cues WHERE youtube_video_id = %s ORDER BY cue_index", 
                (video_id,)
            )
            return self.cursor.fetchall()

    # ==================== QUOTE OPERATIONS ====================

    def save_quotes(self, video_id: int, quotes: List[Dict]) -> int:
        """Save multiple quotes for a video"""
        self.ensure_connection()
        now = datetime.now()
        count = 0
        
        for quote in quotes:
            if self.use_sqlite:
                self.cursor.execute("""
                    INSERT INTO youtube_quotes 
                    (ordinal_number, content, is_visible, youtube_video_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    quote.get('ordinal_number'), quote.get('content'),
                    quote.get('is_visible', 1), video_id, now, now
                ))
            else:
                self.cursor.execute("""
                    INSERT INTO youtube_quotes 
                    (ordinal_number, content, is_visible, youtube_video_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    quote.get('ordinal_number'), quote.get('content'),
                    quote.get('is_visible', 1), video_id, now, now
                ))
            count += 1
        
        if self.use_sqlite:
            self.connection.commit()
        else:
            self.connection.commit()
        
        return count

    def get_quotes_by_video(self, video_id: int, limit: int = None) -> List[Dict]:
        """Get quotes for a specific video"""
        self.ensure_connection()
        if self.use_sqlite:
            query = "SELECT * FROM youtube_quotes WHERE youtube_video_id = ? ORDER BY ordinal_number"
            params = (video_id,)
            if limit:
                query += " LIMIT ?"
                params = (video_id, limit)
            self.cursor.execute(query, params)
            return [dict(row) for row in self.cursor.fetchall()]
        else:
            query = "SELECT * FROM youtube_quotes WHERE youtube_video_id = %s ORDER BY ordinal_number"
            params = [video_id]
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()

    def get_all_quotes(self, limit: int = None) -> List[Dict]:
        """Get all quotes with video info"""
        self.ensure_connection()
        if self.use_sqlite:
            query = """
                SELECT q.*, v.title as video_title, v.channel_title
                FROM youtube_quotes q
                JOIN youtube_videos v ON q.youtube_video_id = v.id
                WHERE q.is_visible = 1
                ORDER BY q.created_at DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            self.cursor.execute(query)
            return [dict(row) for row in self.cursor.fetchall()]
        else:
            query = """
                SELECT q.*, v.title as video_title, v.channel_title
                FROM youtube_quotes q
                JOIN youtube_videos v ON q.youtube_video_id = v.id
                WHERE q.is_visible = 1
                ORDER BY q.created_at DESC
            """
            if limit:
                query += " LIMIT %s"
                self.cursor.execute(query, (limit,))
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
