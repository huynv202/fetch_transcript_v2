"""
Configuration for YouTube Book Reader Data Pipeline
Update these settings with your actual credentials
"""

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '0202',
    'database': 'treebook'
}

# Use SQLite for local testing (set to True if MySQL unavailable)
USE_SQLITE = True  # Changed to True to use SQLite for testing
SQLITE_DB_PATH = 'youtube_books.db'

# AI API Configuration (currently empty - to be filled later)
AI_CONFIG = {
    'api_key': '',  # OpenAI/Gemini/Claude API key
    'model': 'gpt-4o-mini',  # or 'gemini-pro', 'claude-3-haiku', etc.
    'provider': 'openai'  # 'openai', 'gemini', 'claude', 'local'
}

# Processing Configuration
PROCESSING_CONFIG = {
    'min_segment_length': 50,  # Minimum characters per segment
    'max_segment_length': 500,  # Maximum characters per segment
    'context_window': 3,  # Number of sentences to include for context
    'quote_selection_threshold': 0.7,  # Threshold for quote quality scoring
}

# YouTube Configuration
YOUTUBE_CONFIG = {
    'default_language': 'vi',  # Preferred subtitle language
    'fallback_languages': ['en', 'vi-auto'],  # Fallback languages if preferred not available
    'use_cookies': False,  # Set to True if using cookies to bypass IP blocks
    'cookies_file': 'cookies.txt',  # Path to cookies file if use_cookies is True
}
