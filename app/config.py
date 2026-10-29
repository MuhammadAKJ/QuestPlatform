import os
from pathlib import Path
# pyrefly: ignore[missing-import]
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'quest-platform-super-secret-key-2026-change-in-prod')

    # Database: Turso (libSQL) in production, SQLite locally
    QUEST_TURSO_DATABASE_URL = os.environ.get('QUEST_TURSO_DATABASE_URL', '')
    QUEST_TURSO_AUTH_TOKEN = os.environ.get('QUEST_TURSO_AUTH_TOKEN', '')

    if QUEST_TURSO_DATABASE_URL:
        # Convert  libsql://your-db-name.turso.io  →  sqlite+libsql://your-db-name.turso.io
        _db_url = QUEST_TURSO_DATABASE_URL.replace('libsql://', 'sqlite+libsql://')
        if  QUEST_TURSO_AUTH_TOKEN:
            _db_url += f'?authToken={QUEST_TURSO_AUTH_TOKEN}&secure=true'
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get(
            'DATABASE_URL',
            f"sqlite:///{BASE_DIR / 'instance' / 'quest_platform.db'}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    UPLOAD_FOLDER = BASE_DIR / 'app' / 'static' / 'uploads' / 'proofs'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    
    # Default Platform Economics ($X = Base Access Code Price)
    DEFAULT_ACCESS_CODE_PRICE = float(os.environ.get('DEFAULT_ACCESS_CODE_PRICE', 5000.0))
    DEFAULT_CURRENCY_SYMBOL = os.environ.get('DEFAULT_CURRENCY_SYMBOL', '₦')
    DEFAULT_SITE_NAME = os.environ.get('DEFAULT_SITE_NAME', 'QuestPlatform')
