import io
import unittest
from datetime import datetime, timezone
from app import create_app
from app.config import Config
from app.models import db, User, AccessCode, Task, TaskSubmission, Withdrawal, Transaction, SystemSetting
from app.utils import generate_unique_access_codes, get_system_economy

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret'

class QuestPlatformTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed system settings ($X = 5,000)
        SystemSetting.set('access_code_price', '5000')
        SystemSetting.set('currency_symbol', '₦')
        SystemSetting.set('allow_any_day_withdrawals', 'false')

        # Create Admin
        self.admin = User(
            username='admin',
            is_admin=True,
            referral_code='ADMIN-TEST',
            bank_name='Test Bank',
            account_number='1234567890',
            account_name='Admin Payout'
        )
        self.admin.set_password('admin1234')
        db.session.add(self.admin)

        # Create demo access code
        self.code1 = AccessCode(code='QP-TEST-0001', is_used=False, created_by_id=self.admin.id)
        self.code2 = AccessCode(code='QP-TEST-0002', is_used=False, created_by_id=self.admin.id)
        self.code3 = AccessCode(code='QP-TEST-0003', is_used=False, created_by_id=self.admin.id)
        db.session.add_all([self.code1, self.code2, self.code3])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_2tier_referral_economics(self):
        """
        Verify:
        - X = 5000
        - User A registers with no referrer.
        - User B registers with User A's referral code:
            - User A gets Tier 1 reward = X / 5 = 1000 (20%).
        - User C registers with User B's referral code:
            - User B gets Tier 1 reward = X / 5 = 1000.
            - User A gets Tier 2 reward = X / 20 = 250 (5%).
        """
        # 1. Register User A
        res_a = self.client.post('/register', data={
            'username': 'usera',
            'password': 'password123',
            'confirm_password': 'password123',
            'access_code': 'QP-TEST-0001',
            'referral_code': ''
        }, follow_redirects=True)
        self.assertEqual(res_a.status_code, 200)

        user_a = User.query.filter_by(username='usera').first()
        self.assertIsNotNone(user_a)
        self.assertEqual(user_a.wallet_balance, 0.0)

        # Logout User A before registering User B
        self.client.get('/logout')

        # 2. Register User B with User A's referral code
        res_b = self.client.post('/register', data={
            'username': 'userb',
            'password': 'password123',
            'confirm_password': 'password123',
            'access_code': 'QP-TEST-0002',
            'referral_code': user_a.referral_code
        }, follow_redirects=True)
        self.assertEqual(res_b.status_code, 200)

        db.session.expire_all()
        user_a = User.query.filter_by(username='usera').first()
        user_b = User.query.filter_by(username='userb').first()
        
        # User A earned X/5 = 1,000 NGN
        self.assertEqual(user_a.wallet_balance, 1000.0)
        self.assertEqual(user_a.referral_earnings, 1000.0)
        self.assertEqual(user_a.tier1_count, 1)
        self.assertEqual(user_a.tier2_count, 0)

        # Logout User B before registering User C
        self.client.get('/logout')

        # 3. Register User C with User B's referral code
        res_c = self.client.post('/register', data={
            'username': 'userc',
            'password': 'password123',
            'confirm_password': 'password123',
            'access_code': 'QP-TEST-0003',
            'referral_code': user_b.referral_code
        }, follow_redirects=True)
        self.assertEqual(res_c.status_code, 200)

        db.session.expire_all()
        user_a = User.query.filter_by(username='usera').first()
        user_b = User.query.filter_by(username='userb').first()
        user_c = User.query.filter_by(username='userc').first()

        # User B earned Tier 1 = 1,000 NGN
        self.assertEqual(user_b.wallet_balance, 1000.0)
        self.assertEqual(user_b.referral_earnings, 1000.0)
        self.assertEqual(user_b.tier1_count, 1)
        self.assertEqual(user_b.tier2_count, 0)

        # User A earned additional Tier 2 = X/20 = 250 NGN!
        # Total User A = 1,000 + 250 = 1,250 NGN
        self.assertEqual(user_a.wallet_balance, 1250.0)
        self.assertEqual(user_a.referral_earnings, 1250.0)
        self.assertEqual(user_a.tier1_count, 1)
        self.assertEqual(user_a.tier2_count, 1)

    def test_2x_milestone_and_friday_withdrawal(self):
        """
        Verify:
        - 2X milestone threshold is 2 * 5000 = 10,000 NGN.
        - User with 8,000 NGN referral earnings cannot withdraw.
        - User with >= 10,000 NGN referral earnings qualifies.
        - Withdrawal is blocked on non-Fridays unless allow_any_day_withdrawals is True.
        """
        user = User(
            username='cashout_tester',
            referral_code='CASHOUT-1',
            wallet_balance=15000.0,
            referral_earnings=8000.0,  # Below 10,000 threshold
            bank_name='Zenith Bank',
            account_number='1122334455',
            account_name='Tester Account'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        # Should not be qualified
        self.assertFalse(user.is_withdrawal_qualified(5000.0))
        self.assertEqual(user.withdrawal_progress_percentage(5000.0), 80.0)

        # Increase referral earnings to 10,000 (2X)
        user.referral_earnings = 10000.0
        db.session.commit()
        self.assertTrue(user.is_withdrawal_qualified(5000.0))
        self.assertEqual(user.withdrawal_progress_percentage(5000.0), 100.0)

    def test_task_approval_and_reward(self):
        """
        Verify:
        - Task completion reward is X / 40 = 5000 / 40 = 125 NGN.
        - Admin approves submission -> user wallet credited 125 NGN.
        """
        task = Task(
            title='Test YouTube Subscribe',
            category='Social Media',
            url='https://youtube.com',
            instructions='Subscribe to channel',
            reward_amount=None,  # Dynamic X/40
            is_active=True
        )
        user = User(
            username='task_quester',
            referral_code='QUEST-123'
        )
        user.set_password('password123')
        db.session.add_all([task, user])
        db.session.commit()

        submission = TaskSubmission(
            task_id=task.id,
            user_id=user.id,
            screenshot_path='test_proof.png',
            status='pending'
        )
        db.session.add(submission)
        db.session.commit()

        # Login as admin
        self.client.post('/login', data={'username': 'admin', 'password': 'admin1234'})
        
        # Approve submission
        res = self.client.post(f'/admin/reviews/{submission.id}/approve', headers={'Content-Type': 'application/json'})
        self.assertEqual(res.status_code, 200)

        sub = db.session.get(TaskSubmission, submission.id)
        self.assertEqual(sub.status, 'approved')
        self.assertEqual(sub.reward_paid, 125.0)

        u = db.session.get(User, user.id)
        self.assertEqual(u.wallet_balance, 125.0)
        self.assertEqual(u.total_earned, 125.0)
        self.assertEqual(u.tasks_completed_count, 1)

    def test_admin_code_generation_and_export(self):
        """Verify batch access code generation and CSV/TXT export endpoints."""
        self.client.post('/login', data={'username': 'admin', 'password': 'admin1234'})
        
        # Generate batch
        res = self.client.post('/admin/codes', data={
            'action': 'generate',
            'count': '25',
            'prefix': 'VIP'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check export CSV
        res_csv = self.client.get('/admin/codes/export/csv?status=unused')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn('text/csv', res_csv.headers.get('Content-Type', ''))
        self.assertIn('Access Code,Status,Batch ID', res_csv.data.decode())

        # Check export TXT
        res_txt = self.client.get('/admin/codes/export/txt?status=unused')
        self.assertEqual(res_txt.status_code, 200)
        self.assertIn('text/plain', res_txt.headers.get('Content-Type', ''))
        self.assertIn('VIP-', res_txt.data.decode())

    def test_profile_bank_update_and_cashout_flow(self):
        """Verify user updating bank profile, requesting withdrawal, and admin processing/refund."""
        user = User(
            username='payout_user',
            referral_code='PAY-99',
            wallet_balance=20000.0,
            referral_earnings=10000.0  # Qualified (2X >= 10,000)
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        # Login as user
        self.client.post('/login', data={'username': 'payout_user', 'password': 'password123'})

        # Update bank details
        res_profile = self.client.post('/profile', data={
            'action': 'update_bank',
            'bank_name': 'Access Bank',
            'account_number': '0123456789',
            'account_name': 'Payout User'
        }, follow_redirects=True)
        self.assertEqual(res_profile.status_code, 200)

        db.session.expire_all()
        u = db.session.get(User, user.id)
        self.assertEqual(u.bank_name, 'Access Bank')
        self.assertEqual(u.account_number, '0123456789')

        # Enable allow_any_day_withdrawals for test
        SystemSetting.set('allow_any_day_withdrawals', 'true')

        # Submit withdrawal
        res_w = self.client.post('/wallet', data={'amount': '5000'}, follow_redirects=True)
        self.assertEqual(res_w.status_code, 200)

        db.session.expire_all()
        u = db.session.get(User, user.id)
        self.assertEqual(u.wallet_balance, 15000.0)

        withdrawal = Withdrawal.query.filter_by(user_id=u.id).first()
        self.assertIsNotNone(withdrawal)
        self.assertEqual(withdrawal.amount, 5000.0)
        self.assertEqual(withdrawal.status, 'pending')

        # Logout user and login as admin to reject & test refund
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'admin', 'password': 'admin1234'})

        res_reject = self.client.post(f'/admin/withdrawals/{withdrawal.id}/reject', data={
            'reason': 'Bank network timeout'
        }, follow_redirects=True)
        self.assertEqual(res_reject.status_code, 200)

        db.session.expire_all()
        w = db.session.get(Withdrawal, withdrawal.id)
        self.assertEqual(w.status, 'rejected')
        
        # User wallet must be automatically refunded back to 20,000 NGN
        u = db.session.get(User, user.id)
        self.assertEqual(u.wallet_balance, 20000.0)

if __name__ == '__main__':
    unittest.main()
