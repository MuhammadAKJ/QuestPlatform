from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, AccessCode, Transaction
from app.utils import get_system_economy, generate_referral_code

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Check for referral query parameter e.g. /register?ref=QUEST-ABCD
    ref_param = request.args.get('ref', '').strip()

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        access_code_str = request.form.get('access_code', '').strip().upper()
        referral_code_str = request.form.get('referral_code', '').strip().upper()

        # Basic validations
        if not username or not password or not access_code_str:
            flash('Username, password, and an access code are required.', 'danger')
            return render_template('auth/register.html', ref_code=referral_code_str or ref_param)

        if len(username) < 3 or len(username) > 30 or not username.isalnum():
            flash('Username must be 3-30 alphanumeric characters (letters and numbers only).', 'danger')
            return render_template('auth/register.html', ref_code=referral_code_str or ref_param)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', ref_code=referral_code_str or ref_param)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', ref_code=referral_code_str or ref_param)

        # Check existing username
        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('auth/register.html', ref_code=referral_code_str or ref_param)

        # Validate Access Code
        access_code = AccessCode.query.filter_by(code=access_code_str).first()
        if not access_code:
            flash('Invalid Access Code. Please check and try again.', 'danger')
            return render_template('auth/register.html', ref_code=referral_code_str or ref_param)

        if access_code.is_used:
            flash('This Access Code has already been activated.', 'danger')
            return render_template('auth/register.html', ref_code=referral_code_str or ref_param)

        # Validate Sponsor (Referrer)
        sponsor = None
        if referral_code_str:
            sponsor = User.query.filter_by(referral_code=referral_code_str).first()
            if not sponsor:
                flash(f'Referral code "{referral_code_str}" was not found. Proceeding without a referrer.', 'warning')

        # Create new User
        new_ref_code = generate_referral_code(username)
        user = User(
            username=username,
            referral_code=new_ref_code,
            referred_by_id=sponsor.id if sponsor else None
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Generates user.id

        # Mark Access Code as consumed
        access_code.is_used = True
        access_code.used_by_id = user.id
        access_code.used_at = datetime.now(timezone.utc)

        # Distribute Referral Commissions based on Platform Economics
        economy = get_system_economy()
        tier1_amount = economy['tier1_reward']  # X / 5
        tier2_amount = economy['tier2_reward']  # X / 20

        if sponsor:
            # Tier 1 Commission
            sponsor.wallet_balance += tier1_amount
            sponsor.referral_earnings += tier1_amount
            sponsor.total_earned += tier1_amount

            tx1 = Transaction(
                user_id=sponsor.id,
                amount=tier1_amount,
                tx_type='tier1_referral',
                description=f'Direct Referral Commission from @{user.username}',
                reference_id=str(user.id)
            )
            db.session.add(tx1)

            # Check Tier 2 Commission (Sponsor of Sponsor)
            if sponsor.referred_by_id:
                tier2_sponsor = db.session.get(User, sponsor.referred_by_id)
                if tier2_sponsor:
                    tier2_sponsor.wallet_balance += tier2_amount
                    tier2_sponsor.referral_earnings += tier2_amount
                    tier2_sponsor.total_earned += tier2_amount

                    tx2 = Transaction(
                        user_id=tier2_sponsor.id,
                        amount=tier2_amount,
                        tx_type='tier2_referral',
                        description=f'Tier-2 Referral Commission from @{user.username} (via @{sponsor.username})',
                        reference_id=str(user.id)
                    )
                    db.session.add(tx2)

        db.session.commit()

        login_user(user)
        flash(f'Welcome aboard, @{user.username}! Your account has been activated.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', ref_code=ref_param)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            flash(f'Welcome back, @{user.username}!', 'success')
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.dashboard'))

        flash('Invalid username or password. Please try again.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))
