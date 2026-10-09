import os
import secrets
import string
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import SystemSetting, AccessCode, User

def get_system_economy():
    """Fetches dynamic economic values configured in the platform settings."""
    # Base X price
    x_price_str = SystemSetting.get('access_code_price', str(current_app.config.get('DEFAULT_ACCESS_CODE_PRICE', 5000.0)))
    try:
        x_price = float(x_price_str)
    except (ValueError, TypeError):
        x_price = 5000.0

    currency_symbol = SystemSetting.get('currency_symbol', current_app.config.get('DEFAULT_CURRENCY_SYMBOL', '₦'))
    site_name = SystemSetting.get('site_name', current_app.config.get('DEFAULT_SITE_NAME', 'QuestPlatform'))
    
    # Withdrawal rules
    allow_any_day = SystemSetting.get('allow_any_day_withdrawals', 'false').lower() == 'true'
    now_utc = datetime.now(timezone.utc)
    # Friday is weekday() == 4 (Monday is 0, Sunday is 6)
    is_friday = (now_utc.weekday() == 4)
    can_withdraw_today = allow_any_day or is_friday
    
    # Calculate next Friday if today is not Friday
    days_until_friday = (4 - now_utc.weekday()) % 7
    if days_until_friday == 0 and not is_friday:
        days_until_friday = 7
    next_friday_date = (now_utc + timedelta(days=days_until_friday)).strftime('%A, %b %d, %Y')
    
    # Ads settings
    google_ads_enabled = SystemSetting.get('google_ads_enabled', 'false').lower() == 'true'
    google_ads_client_id = SystemSetting.get('google_ads_client_id', '')

    # Computed commission rates
    tier1_reward = x_price / 5.0    # X / 5 (20%)
    tier2_reward = x_price / 20.0   # X / 20 (5%)
    task_reward = x_price / 40.0    # X / 40 (2.5%)
    min_withdrawal = x_price * 2.0  # 2X referral accumulation threshold

    return {
        'x_price': x_price,
        'currency_symbol': currency_symbol,
        'site_name': site_name,
        'tier1_reward': tier1_reward,
        'tier2_reward': tier2_reward,
        'task_reward': task_reward,
        'min_withdrawal': min_withdrawal,
        'allow_any_day_withdrawals': allow_any_day,
        'is_friday': is_friday,
        'can_withdraw_today': can_withdraw_today,
        'next_friday_date': next_friday_date,
        'google_ads_enabled': google_ads_enabled,
        'google_ads_client_id': google_ads_client_id,
    }

def format_currency(amount, symbol=None):
    """Formats numeric amount into pretty currency string."""
    if amount is None:
        amount = 0.0
    if symbol is None:
        symbol = SystemSetting.get('currency_symbol', current_app.config.get('DEFAULT_CURRENCY_SYMBOL', '₦'))
    return f"{symbol}{amount:,.2f}"

def generate_random_code_segment(length=4):
    chars = string.ascii_uppercase + string.digits
    # Exclude ambiguous characters (0, O, 1, I)
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_access_code(prefix="QP"):
    """Generates a formatted access code like QP-7X4A-9B2C"""
    return f"{prefix}-{generate_random_code_segment(4)}-{generate_random_code_segment(4)}"

def generate_unique_access_codes(count=1, prefix="QP", batch_id=None, admin_id=None):
    """Generates a list of unique AccessCode instances ready to be added to DB session."""
    codes = []
    generated_strings = set()
    
    # Also fetch existing codes to prevent collision
    existing_codes = {c.code for c in AccessCode.query.with_entities(AccessCode.code).all()}
    
    while len(codes) < count:
        code_str = generate_access_code(prefix=prefix)
        if code_str not in existing_codes and code_str not in generated_strings:
            generated_strings.add(code_str)
            ac = AccessCode(
                code=code_str,
                is_used=False,
                batch_id=batch_id,
                created_by_id=admin_id
            )
            codes.append(ac)
            
    return codes

def generate_referral_code(username: str) -> str:
    """Generates a unique, friendly referral code for a new user."""
    clean_user = ''.join(c for c in username if c.isalnum()).upper()[:6]
    if not clean_user:
        clean_user = "QUEST"
    
    for _ in range(20):
        suffix = generate_random_code_segment(4)
        candidate = f"{clean_user}-{suffix}"
        if not User.query.filter_by(referral_code=candidate).first():
            return candidate
            
    # Fallback to high-entropy hex
    return f"REF-{secrets.token_hex(4).upper()}"

def allowed_file(filename: str) -> bool:
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp', 'gif'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def save_proof_screenshot(file_storage) -> str:
    """Validates, compresses/resizes, and saves user screenshot proof."""
    if not file_storage or not allowed_file(file_storage.filename):
        raise ValueError("Invalid file format. Please upload a PNG, JPG, or WEBP image.")
    
    upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    # Generate secure filename
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    random_id = secrets.token_hex(6)
    filename = f"proof_{timestamp}_{random_id}.{ext}"
    target_path = upload_folder / filename
    
    # Open with PIL to sanitize, strip EXIF and optionally resize huge images
    try:
        image = Image.open(file_storage)
        # Convert RGBA/P to RGB if saving as JPEG
        if image.mode in ("RGBA", "P") and ext in ('jpg', 'jpeg'):
            image = image.convert('RGB')
        
        # Max dimensions 1920x1920
        image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
        image.save(target_path, quality=85, optimize=True)
    except Exception as e:
        # Fallback to direct save if PIL fails for some format
        file_storage.seek(0)
        file_storage.save(str(target_path))
        
    return filename
