"""
Seed script to initialize the SQLite database, default Admin account, system settings,
sample tasks, and demo access codes.
"""
from datetime import datetime, timezone
from app import create_app
from app.models import db, User, AccessCode, Task, TaskSubmission, Transaction, SystemSetting
from app.utils import generate_unique_access_codes, generate_referral_code

app = create_app()

def seed_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables initialized.")

        # Seed System Settings
        default_settings = [
            ('access_code_price', '5000', 'Base access code price X'),
            ('currency_symbol', '₦', 'Platform currency symbol'),
            ('site_name', 'QuestPlatform', 'Brand name'),
            ('allow_any_day_withdrawals', 'false', 'Unlock withdrawals on any day'),
            ('google_ads_enabled', 'false', 'Toggle Google Ads'),
            ('google_ads_client_id', '', 'Google AdSense Publisher ID'),
        ]
        for key, val, desc in default_settings:
            if not db.session.get(SystemSetting, key):
                setting = SystemSetting(key=key, value=val, description=desc)
                db.session.add(setting)
        db.session.commit()
        print("✓ System economic settings seeded.")

        # Seed Admin Account
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                is_admin=True,
                referral_code='ADMIN-MASTER',
                bank_name='Standard Bank',
                account_number='0011223344',
                account_name='Platform Admin'
            )
            admin.set_password('admin1234')
            db.session.add(admin)
            db.session.commit()
            print("✓ Default Admin created -> Username: 'admin' | Password: 'admin1234'")
        else:
            print("✓ Admin user already exists.")

        # Seed Sample Tasks
        if Task.query.count() == 0:
            sample_tasks = [
                Task(
                    title="Subscribe to Official YouTube Channel",
                    category="Social Media",
                    url="https://youtube.com",
                    instructions="1. Click the link above to open our YouTube channel.\n2. Click the Subscribe button and ring the notification bell.\n3. Take a screenshot showing you are subscribed and upload it below.",
                    reward_amount=None,  # Dynamic X/40 (₦125.00)
                    is_active=True
                ),
                Task(
                    title="Join Official Telegram Community",
                    category="Telegram/Discord",
                    url="https://t.me",
                    instructions="1. Open the Telegram link and click 'Join Channel'.\n2. Take a clear screenshot of the Telegram group interface showing you joined.\n3. Upload screenshot proof below.",
                    reward_amount=None,
                    is_active=True
                ),
                Task(
                    title="Follow & Retweet on X (Twitter)",
                    category="Social Media",
                    url="https://x.com",
                    instructions="1. Follow the official profile on X.\n2. Like & Repost our pinned quest announcement tweet.\n3. Take a screenshot showing your repost on your timeline and upload proof.",
                    reward_amount=None,
                    is_active=True
                ),
                Task(
                    title="5-Star Rating & Review on App Store",
                    category="Review & Rating",
                    url="https://play.google.com",
                    instructions="1. Visit the app store page.\n2. Leave a 5-star rating with an honest 1-2 sentence positive review.\n3. Screenshot your published review and upload proof.",
                    reward_amount=250.0,  # Custom bonus quest reward
                    is_active=True
                ),
            ]
            db.session.add_all(sample_tasks)
            db.session.commit()
            print("✓ Sample quests seeded.")

        # Seed Demo Access Codes
        if AccessCode.query.count() == 0:
            demo_codes = generate_unique_access_codes(count=15, prefix="QP", batch_id="DEMO-LAUNCH", admin_id=admin.id)
            db.session.add_all(demo_codes)
            db.session.commit()
            print(f"✓ Seeded 15 demo access codes (Batch: DEMO-LAUNCH).")
            print(f"   Sample usable code: {demo_codes[0].code}")

        # Seed Demo Users for rich referral tree & leaderboard demo
        user1 = User.query.filter_by(username='victor_quest').first()
        if not user1:
            user1 = User(
                username='victor_quest',
                referral_code='VICTOR-7890',
                referred_by_id=admin.id,
                wallet_balance=15000.0,
                referral_earnings=12000.0,  # Qualified for 2X milestone (12000 >= 10000)
                total_earned=15000.0,
                tasks_completed_count=12,
                bank_name='Access Bank',
                account_number='0123456789',
                account_name='Victor Quest'
            )
            user1.set_password('password123')
            db.session.add(user1)
            db.session.flush()

            user2 = User(
                username='sarah_pro',
                referral_code='SARAH-4321',
                referred_by_id=user1.id,  # Referred by Victor (Tier 1 for Victor)
                wallet_balance=8500.0,
                referral_earnings=7000.0,
                total_earned=8500.0,
                tasks_completed_count=8,
                bank_name='GTBank',
                account_number='9876543210',
                account_name='Sarah Johnson'
            )
            user2.set_password('password123')
            db.session.add(user2)
            db.session.flush()

            user3 = User(
                username='emmanuel_k',
                referral_code='EMMA-9988',
                referred_by_id=user2.id,  # Referred by Sarah -> Tier 2 for Victor!
                wallet_balance=4000.0,
                referral_earnings=3000.0,
                total_earned=4000.0,
                tasks_completed_count=5,
                bank_name='Zenith Bank',
                account_number='2233445566',
                account_name='Emmanuel K'
            )
            user3.set_password('password123')
            db.session.add(user3)
            db.session.commit()
            print("✓ Seeded sample users: 'victor_quest', 'sarah_pro', 'emmanuel_k' (password: 'password123')")

        print("\n🎉 Seed complete! Ready to launch QuestPlatform.")

if __name__ == '__main__':
    seed_database()
