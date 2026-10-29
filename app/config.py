import os
from pathlib import Path

# Load .env if present (local dev only – not available in Cloudflare Workers)
try:
    # pyrefly: ignore[missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect runtime environment
IS_CLOUDFLARE = bool(os.environ.get('CF_PAGES') or os.environ.get('WORKERS_RS_VERSION'))
IS_VERCEL = bool(os.environ.get('VERCEL'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'quest-platform-super-secret-key-2026-change-in-prod')

    # ── Database ──────────────────────────────────────────────
    # Cloudflare D1: handled dynamically via sqlalchemy-cloudflare-d1
    #   → the D1 binding is injected at runtime by the worker;
    #     we set a placeholder URI that the dialect will override.
    # Turso (libSQL): for Vercel or self-hosted.
    # Local SQLite: default fallback for development.

    QUEST_TURSO_DATABASE_URL = os.environ.get('QUEST_TURSO_DATABASE_URL', '')
    QUEST_TURSO_AUTH_TOKEN = os.environ.get('QUEST_TURSO_AUTH_TOKEN', '')

    if IS_CLOUDFLARE:
        # sqlalchemy-cloudflare-d1 uses a special dialect URI
        SQLALCHEMY_DATABASE_URI = 'sqlite+d1://DB'
    elif QUEST_TURSO_DATABASE_URL:
        _db_url = QUEST_TURSO_DATABASE_URL.replace('libsql://', 'sqlite+libsql://')
        if QUEST_TURSO_AUTH_TOKEN:
            _db_url += f'?authToken={QUEST_TURSO_AUTH_TOKEN}&secure=true'
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get(
            'DATABASE_URL',
            f"sqlite:///{BASE_DIR / 'instance' / 'quest_platform.db'}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Upload settings ───────────────────────────────────────
    UPLOAD_FOLDER = BASE_DIR / 'app' / 'static' / 'uploads' / 'proofs'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

    # ── Default Platform Economics ($X = Base Access Code Price) ─
    DEFAULT_ACCESS_CODE_PRICE = float(os.environ.get('DEFAULT_ACCESS_CODE_PRICE', 5000.0))
    DEFAULT_CURRENCY_SYMBOL = os.environ.get('DEFAULT_CURRENCY_SYMBOL', '₦')
    DEFAULT_SITE_NAME = os.environ.get('DEFAULT_SITE_NAME', 'QuestPlatform')
