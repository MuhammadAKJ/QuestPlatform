from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Referral system
    referral_code = db.Column(db.String(24), unique=True, nullable=False, index=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Financial state
    wallet_balance = db.Column(db.Float, default=0.0)       # Available to withdraw
    referral_earnings = db.Column(db.Float, default=0.0)    # Lifetime referral commissions earned
    total_earned = db.Column(db.Float, default=0.0)         # Lifetime all earnings (referral + tasks)
    tasks_completed_count = db.Column(db.Integer, default=0)
    
    # Payout details
    bank_name = db.Column(db.String(128), nullable=True)
    account_number = db.Column(db.String(64), nullable=True)
    account_name = db.Column(db.String(128), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Self-referencing referral relationship (Tier 1 direct downline)
    direct_referrals = db.relationship(
        'User',
        backref=db.backref('sponsor', remote_side=[id]),
        foreign_keys=[referred_by_id],
        lazy='dynamic'
    )
    
    # Other relationships
    submissions = db.relationship('TaskSubmission', backref='user', foreign_keys='TaskSubmission.user_id', lazy='dynamic')
    withdrawals = db.relationship('Withdrawal', backref='user', foreign_keys='Withdrawal.user_id', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='user', foreign_keys='Transaction.user_id', lazy='dynamic', order_by='Transaction.created_at.desc()')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def tier1_count(self) -> int:
        """Returns direct referral count."""
        return self.direct_referrals.count()

    @property
    def tier2_count(self) -> int:
        """Returns second-tier referral count (referrals of direct referrals)."""
        direct_ids = [u.id for u in self.direct_referrals.all()]
        if not direct_ids:
            return 0
        return User.query.filter(User.referred_by_id.in_(direct_ids)).count()

    @property
    def has_payout_details(self) -> bool:
        return bool(self.bank_name and self.account_number and self.account_name)

    def is_withdrawal_qualified(self, base_x_price: float) -> bool:
        """User qualifies for withdrawal once they have accumulated at least 2X from referrals."""
        threshold = 2.0 * base_x_price
        return self.referral_earnings >= threshold

    def withdrawal_progress_percentage(self, base_x_price: float) -> float:
        """Progress percentage towards the 2X referral milestone."""
        threshold = 2.0 * base_x_price
        if threshold <= 0:
            return 100.0
        pct = (self.referral_earnings / threshold) * 100.0
        return min(100.0, max(0.0, round(pct, 1)))

    def __repr__(self):
        return f'<User {self.username}>'


class AccessCode(db.Model):
    __tablename__ = 'access_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False, index=True)
    batch_id = db.Column(db.String(32), nullable=True, index=True)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    used_at = db.Column(db.DateTime, nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    used_by = db.relationship('User', foreign_keys=[used_by_id])

    def __repr__(self):
        return f'<AccessCode {self.code} used={self.is_used}>'


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(64), default='Social')
    url = db.Column(db.String(512), nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    reward_amount = db.Column(db.Float, nullable=True)  # If None, dynamically calculated as X/40
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    submissions = db.relationship('TaskSubmission', backref='task', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Task {self.title}>'


class TaskSubmission(db.Model):
    __tablename__ = 'task_submissions'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    screenshot_path = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(32), default='pending', index=True)  # 'pending', 'approved', 'rejected'
    rejection_reason = db.Column(db.String(255), nullable=True)
    reward_paid = db.Column(db.Float, default=0.0)
    
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f'<TaskSubmission #{self.id} task={self.task_id} user={self.user_id} status={self.status}>'


class Withdrawal(db.Model):
    __tablename__ = 'withdrawals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    bank_name = db.Column(db.String(128), nullable=False)
    account_number = db.Column(db.String(64), nullable=False)
    account_name = db.Column(db.String(128), nullable=False)
    
    status = db.Column(db.String(32), default='pending', index=True)  # 'pending', 'paid', 'rejected'
    admin_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    processed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Withdrawal #{self.id} user={self.user_id} amount={self.amount} status={self.status}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tx_type = db.Column(db.String(32), nullable=False, index=True)  
    # Types: 'tier1_referral', 'tier2_referral', 'task_reward', 'withdrawal', 'refund', 'admin_adjustment'
    description = db.Column(db.String(255), nullable=False)
    reference_id = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f'<Transaction #{self.id} user={self.user_id} amount={self.amount} type={self.tx_type}>'


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    @classmethod
    def get(cls, key: str, default: str = '') -> str:
        setting = db.session.get(cls, key)
        return setting.value if setting else default

    @classmethod
    def set(cls, key: str, value: str, description: str = None):
        setting = db.session.get(cls, key)
        if not setting:
            setting = cls(key=key, value=str(value), description=description)
            db.session.add(setting)
        else:
            setting.value = str(value)
            if description:
                setting.description = description
        db.session.commit()

    def __repr__(self):
        return f'<SystemSetting {self.key}={self.value}>'
