import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask
from flask_login import LoginManager
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure instance and upload directories exist
    upload_dir = Path(app.config['UPLOAD_FOLDER'])
    upload_dir.mkdir(parents=True, exist_ok=True)
    instance_dir = Path(app.root_path).parent / 'instance'
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Context processors and global template helpers
    from app.utils import get_system_economy, format_currency

    @app.context_processor
    def inject_globals():
        try:
            economy = get_system_economy()
        except Exception:
            economy = {
                'x_price': 5000.0,
                'currency_symbol': '₦',
                'site_name': 'QuestPlatform',
                'tier1_reward': 1000.0,
                'tier2_reward': 250.0,
                'task_reward': 125.0,
                'min_withdrawal': 10000.0,
                'is_friday': False,
                'can_withdraw_today': False,
                'next_friday_date': 'Friday',
                'google_ads_enabled': False,
                'google_ads_client_id': '',
            }
        return {
            'economy': economy,
            'format_currency': format_currency,
            'now_year': datetime.now(timezone.utc).year
        }

    @app.template_filter('currency')
    def currency_filter(amount, symbol=None):
        return format_currency(amount, symbol)

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%b %d, %Y • %I:%M %p'):
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        return value.strftime(format)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
