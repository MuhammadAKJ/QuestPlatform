from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.models import db, User, Task, TaskSubmission, Withdrawal, Transaction
from app.utils import get_system_economy, save_proof_screenshot

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    economy = get_system_economy()
    # Fetch top 5 leaders for preview
    top_referrers = User.query.filter(User.is_admin == False).order_by(User.referral_earnings.desc()).limit(5).all()
    recent_tasks_count = Task.query.filter_by(is_active=True).count()
    total_users_count = User.query.filter_by(is_admin=False).count()

    return render_template(
        'user/landing.html',
        top_referrers=top_referrers,
        recent_tasks_count=recent_tasks_count,
        total_users_count=total_users_count,
        economy=economy
    )

@main_bp.route('/dashboard')
@login_required
def dashboard():
    economy = get_system_economy()
    x_price = economy['x_price']
    
    # User stats
    tier1_count = current_user.tier1_count
    tier2_count = current_user.tier2_count
    withdrawal_qualified = current_user.is_withdrawal_qualified(x_price)
    progress_pct = current_user.withdrawal_progress_percentage(x_price)
    
    # Active available tasks (excluding tasks already completed or submitted as pending by this user)
    submitted_task_ids = [
        s.task_id for s in TaskSubmission.query.filter(
            TaskSubmission.user_id == current_user.id,
            TaskSubmission.status.in_(['pending', 'approved'])
        ).all()
    ]
    
    available_tasks = Task.query.filter(
        Task.is_active == True,
        ~Task.id.in_(submitted_task_ids) if submitted_task_ids else True
    ).order_by(Task.created_at.desc()).limit(6).all()

    # Recent transactions
    recent_txs = current_user.transactions.limit(5).all()

    # Recent submissions
    recent_submissions = current_user.submissions.order_by(TaskSubmission.created_at.desc()).limit(5).all()

    return render_template(
        'user/dashboard.html',
        tier1_count=tier1_count,
        tier2_count=tier2_count,
        withdrawal_qualified=withdrawal_qualified,
        progress_pct=progress_pct,
        available_tasks=available_tasks,
        recent_txs=recent_txs,
        recent_submissions=recent_submissions,
        economy=economy
    )

@main_bp.route('/quests')
@login_required
def quests():
    economy = get_system_economy()
    category = request.args.get('category', '').strip()
    
    query = Task.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
        
    tasks = query.order_by(Task.created_at.desc()).all()
    
    # User's submissions map
    user_submissions = {
        s.task_id: s for s in TaskSubmission.query.filter_by(user_id=current_user.id).all()
    }

    # Distinct categories
    categories = [r[0] for r in db.session.query(Task.category).distinct().all() if r[0]]

    return render_template(
        'user/quests.html',
        tasks=tasks,
        user_submissions=user_submissions,
        selected_category=category,
        categories=categories,
        economy=economy
    )

@main_bp.route('/quests/<int:task_id>', methods=['GET', 'POST'])
@login_required
def quest_detail(task_id):
    task = db.get_or_404(Task, task_id)
    if not task.is_active:
        flash('This task is currently inactive.', 'warning')
        return redirect(url_for('main.quests'))

    economy = get_system_economy()
    # Determine reward amount: custom task reward or dynamic X/40
    task_reward = task.reward_amount if task.reward_amount is not None else economy['task_reward']

    # Check if already submitted
    existing_sub = TaskSubmission.query.filter_by(task_id=task.id, user_id=current_user.id).order_by(TaskSubmission.created_at.desc()).first()
    
    if request.method == 'POST':
        if existing_sub and existing_sub.status in ('pending', 'approved'):
            flash('You have already submitted proof for this task.', 'warning')
            return redirect(url_for('main.quest_detail', task_id=task.id))

        if 'screenshot' not in request.files or not request.files['screenshot'].filename:
            flash('Please select a screenshot proof image to upload.', 'danger')
            return render_template('user/quest_detail.html', task=task, task_reward=task_reward, existing_sub=existing_sub)

        file = request.files['screenshot']
        notes = request.form.get('notes', '').strip()

        try:
            filename = save_proof_screenshot(file)
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('user/quest_detail.html', task=task, task_reward=task_reward, existing_sub=existing_sub)
        except Exception as e:
            flash('Error uploading screenshot proof. Please try again.', 'danger')
            return render_template('user/quest_detail.html', task=task, task_reward=task_reward, existing_sub=existing_sub)

        submission = TaskSubmission(
            task_id=task.id,
            user_id=current_user.id,
            screenshot_path=filename,
            notes=notes,
            status='pending'
        )
        db.session.add(submission)
        db.session.commit()

        flash('Screenshot proof submitted successfully! Admin will review and credit your wallet.', 'success')
        return redirect(url_for('main.quests'))

    return render_template('user/quest_detail.html', task=task, task_reward=task_reward, existing_sub=existing_sub)

@main_bp.route('/referrals')
@login_required
def referrals():
    economy = get_system_economy()
    tier1_count = current_user.tier1_count
    tier2_count = current_user.tier2_count
    
    # Referral transactions
    ref_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.tx_type.in_(['tier1_referral', 'tier2_referral'])
    ).order_by(Transaction.created_at.desc()).all()

    # Pre-built share messages
    base_url = request.host_url.rstrip('/')
    share_url = f"{base_url}/register?ref={current_user.referral_code}"
    share_text = f"Join QuestPlatform, complete easy tasks, and earn cash with me! Sign up using my link: {share_url}"

    return render_template(
        'user/referrals.html',
        tier1_count=tier1_count,
        tier2_count=tier2_count,
        ref_transactions=ref_transactions,
        share_url=share_url,
        share_text=share_text,
        economy=economy
    )

@main_bp.route('/leaderboard')
def leaderboard():
    economy = get_system_economy()
    
    # Top referrers (by total referral earnings)
    top_referrers = User.query.filter(User.is_admin == False).order_by(User.referral_earnings.desc()).limit(20).all()
    
    # Top questers (by tasks completed)
    top_questers = User.query.filter(User.is_admin == False).order_by(User.tasks_completed_count.desc()).limit(20).all()

    return render_template(
        'user/leaderboard.html',
        top_referrers=top_referrers,
        top_questers=top_questers,
        economy=economy
    )

@main_bp.route('/wallet', methods=['GET', 'POST'])
@login_required
def wallet():
    economy = get_system_economy()
    x_price = economy['x_price']
    withdrawal_qualified = current_user.is_withdrawal_qualified(x_price)
    can_withdraw_today = economy['can_withdraw_today']
    
    if request.method == 'POST':
        # Withdrawal form submitted
        if not current_user.has_payout_details:
            flash('Please update your bank payout details in your Profile before requesting a withdrawal.', 'danger')
            return redirect(url_for('main.profile'))

        if not withdrawal_qualified:
            needed = (2.0 * x_price) - current_user.referral_earnings
            flash(f'You must accumulate at least {economy["currency_symbol"]}{2.0 * x_price:,.2f} in referral earnings to qualify. You need {economy["currency_symbol"]}{needed:,.2f} more.', 'danger')
            return redirect(url_for('main.wallet'))

        if not can_withdraw_today:
            flash(f'Withdrawals can only be requested on Fridays! Next payout window is {economy["next_friday_date"]}.', 'warning')
            return redirect(url_for('main.wallet'))

        try:
            amount = float(request.form.get('amount', 0))
        except (ValueError, TypeError):
            flash('Please enter a valid withdrawal amount.', 'danger')
            return redirect(url_for('main.wallet'))

        if amount <= 0:
            flash('Withdrawal amount must be greater than zero.', 'danger')
            return redirect(url_for('main.wallet'))

        if amount > current_user.wallet_balance:
            flash('Requested amount exceeds your available wallet balance.', 'danger')
            return redirect(url_for('main.wallet'))

        # Create withdrawal request and deduct balance
        current_user.wallet_balance -= amount
        withdrawal = Withdrawal(
            user_id=current_user.id,
            amount=amount,
            bank_name=current_user.bank_name,
            account_number=current_user.account_number,
            account_name=current_user.account_name,
            status='pending'
        )
        db.session.add(withdrawal)

        # Log debit transaction
        tx = Transaction(
            user_id=current_user.id,
            amount=-amount,
            tx_type='withdrawal',
            description=f'Withdrawal request to {current_user.bank_name} ({current_user.account_number})',
            reference_id=f"W-{withdrawal.id}"
        )
        db.session.add(tx)
        db.session.commit()

        flash(f'Withdrawal request for {economy["currency_symbol"]}{amount:,.2f} submitted! It will be processed during the Friday payout cycle.', 'success')
        return redirect(url_for('main.wallet'))

    transactions = current_user.transactions.all()
    withdrawals = current_user.withdrawals.order_by(Withdrawal.created_at.desc()).all()

    return render_template(
        'user/wallet.html',
        transactions=transactions,
        withdrawals=withdrawals,
        withdrawal_qualified=withdrawal_qualified,
        can_withdraw_today=can_withdraw_today,
        economy=economy
    )

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    economy = get_system_economy()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_bank':
            bank_name = request.form.get('bank_name', '').strip()
            account_number = request.form.get('account_number', '').strip()
            account_name = request.form.get('account_name', '').strip()

            if not bank_name or not account_number or not account_name:
                flash('Please provide Bank Name, Account Number, and Account Name.', 'danger')
            else:
                current_user.bank_name = bank_name
                current_user.account_number = account_number
                current_user.account_name = account_name
                db.session.commit()
                flash('Payout bank details updated successfully!', 'success')
            return redirect(url_for('main.profile'))

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '').strip()
            new_pw = request.form.get('new_password', '').strip()
            confirm_pw = request.form.get('confirm_password', '').strip()

            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'danger')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('main.profile'))

    return render_template('user/profile.html', economy=economy)

@main_bp.route('/rules')
def rules():
    economy = get_system_economy()
    return render_template('user/rules.html', economy=economy)
