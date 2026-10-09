import io
import csv
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify, abort
from flask_login import login_required, current_user
from app.models import db, User, AccessCode, Task, TaskSubmission, Withdrawal, Transaction, SystemSetting
from app.utils import get_system_economy, generate_unique_access_codes

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin privilege required to access this area.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def dashboard():
    economy = get_system_economy()
    x_price = economy['x_price']
    
    total_users = User.query.filter_by(is_admin=False).count()
    total_codes_count = AccessCode.query.count()
    used_codes_count = AccessCode.query.filter_by(is_used=True).count()
    unused_codes_count = total_codes_count - used_codes_count
    
    # Financial metrics
    gross_code_revenue = used_codes_count * x_price
    
    # Total commissions paid out
    total_tier1_paid = db.session.query(db.func.sum(Transaction.amount)).filter_by(tx_type='tier1_referral').scalar() or 0.0
    total_tier2_paid = db.session.query(db.func.sum(Transaction.amount)).filter_by(tx_type='tier2_referral').scalar() or 0.0
    total_commissions_paid = total_tier1_paid + total_tier2_paid
    
    total_task_rewards_paid = db.session.query(db.func.sum(Transaction.amount)).filter_by(tx_type='task_reward').scalar() or 0.0
    total_withdrawn_paid = db.session.query(db.func.sum(Withdrawal.amount)).filter_by(status='paid').scalar() or 0.0
    
    house_net_margin = gross_code_revenue - total_commissions_paid - total_task_rewards_paid
    
    # Queue counts
    pending_submissions_count = TaskSubmission.query.filter_by(status='pending').count()
    pending_withdrawals_count = Withdrawal.query.filter_by(status='pending').count()
    pending_withdrawals_amount = db.session.query(db.func.sum(Withdrawal.amount)).filter_by(status='pending').scalar() or 0.0
    
    # Recent pending submissions for quick review snippet
    recent_pending_submissions = TaskSubmission.query.filter_by(status='pending').order_by(TaskSubmission.created_at.asc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_codes_count=total_codes_count,
        used_codes_count=used_codes_count,
        unused_codes_count=unused_codes_count,
        gross_code_revenue=gross_code_revenue,
        total_commissions_paid=total_commissions_paid,
        total_task_rewards_paid=total_task_rewards_paid,
        total_withdrawn_paid=total_withdrawn_paid,
        house_net_margin=house_net_margin,
        pending_submissions_count=pending_submissions_count,
        pending_withdrawals_count=pending_withdrawals_count,
        pending_withdrawals_amount=pending_withdrawals_amount,
        recent_pending_submissions=recent_pending_submissions,
        economy=economy
    )

@admin_bp.route('/codes', methods=['GET', 'POST'])
@admin_required
def codes():
    economy = get_system_economy()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate':
            try:
                count = int(request.form.get('count', 10))
                if count < 1 or count > 1000:
                    flash('Please generate between 1 and 1,000 codes per batch.', 'danger')
                    return redirect(url_for('admin.codes'))
            except (ValueError, TypeError):
                count = 10
                
            prefix = request.form.get('prefix', 'QP').strip().upper() or 'QP'
            batch_id = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            
            new_codes = generate_unique_access_codes(count=count, prefix=prefix, batch_id=batch_id, admin_id=current_user.id)
            db.session.add_all(new_codes)
            db.session.commit()
            
            flash(f'Successfully generated {count} access codes (Batch ID: {batch_id})! You can download them below.', 'success')
            return redirect(url_for('admin.codes', batch_id=batch_id))

    # Query codes
    filter_status = request.args.get('status', 'all')
    batch_filter = request.args.get('batch_id', '').strip()
    search = request.args.get('q', '').strip()
    
    query = AccessCode.query
    if filter_status == 'unused':
        query = query.filter_by(is_used=False)
    elif filter_status == 'used':
        query = query.filter_by(is_used=True)
        
    if batch_filter:
        query = query.filter_by(batch_id=batch_filter)
        
    if search:
        query = query.filter(AccessCode.code.ilike(f'%{search}%'))
        
    all_codes = query.order_by(AccessCode.created_at.desc()).limit(200).all()
    
    # Get distinct batches
    batches = [r[0] for r in db.session.query(AccessCode.batch_id).distinct().order_by(AccessCode.batch_id.desc()).all() if r[0]]

    return render_template(
        'admin/codes.html',
        codes=all_codes,
        filter_status=filter_status,
        batch_filter=batch_filter,
        search=search,
        batches=batches,
        economy=economy
    )

@admin_bp.route('/codes/export/<format_type>')
@admin_required
def export_codes(format_type):
    filter_status = request.args.get('status', 'unused')
    batch_filter = request.args.get('batch_id', '').strip()
    
    query = AccessCode.query
    if filter_status == 'unused':
        query = query.filter_by(is_used=False)
    elif filter_status == 'used':
        query = query.filter_by(is_used=True)
        
    if batch_filter:
        query = query.filter_by(batch_id=batch_filter)
        
    codes = query.order_by(AccessCode.created_at.desc()).all()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    if format_type == 'txt':
        content = "\n".join(c.code for c in codes)
        filename = f"access_codes_{filter_status}_{timestamp}.txt"
        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
    else:  # CSV format
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Access Code', 'Status', 'Batch ID', 'Created At', 'Used By', 'Used At'])
        
        for c in codes:
            used_by_name = c.used_by.username if c.used_by else ''
            used_at_str = c.used_at.strftime('%Y-%m-%d %H:%M:%S') if c.used_at else ''
            created_at_str = c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else ''
            status_str = 'Used' if c.is_used else 'Available'
            writer.writerow([c.code, status_str, c.batch_id or '', created_at_str, used_by_name, used_at_str])
            
        filename = f"access_codes_{filter_status}_{timestamp}.csv"
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )

@admin_bp.route('/reviews')
@admin_required
def reviews():
    economy = get_system_economy()
    filter_status = request.args.get('status', 'pending')
    
    query = TaskSubmission.query
    if filter_status in ('pending', 'approved', 'rejected'):
        query = query.filter_by(status=filter_status)
        
    submissions = query.order_by(TaskSubmission.created_at.asc() if filter_status == 'pending' else TaskSubmission.created_at.desc()).all()
    pending_count = TaskSubmission.query.filter_by(status='pending').count()

    return render_template(
        'admin/reviews.html',
        submissions=submissions,
        filter_status=filter_status,
        pending_count=pending_count,
        economy=economy
    )

@admin_bp.route('/reviews/<int:submission_id>/approve', methods=['POST'])
@admin_required
def approve_submission(submission_id):
    submission = db.get_or_404(TaskSubmission, submission_id)
    if submission.status == 'approved':
        if request.is_json:
            return jsonify({'success': False, 'message': 'Already approved'}), 400
        flash('This submission is already approved.', 'info')
        return redirect(url_for('admin.reviews'))

    economy = get_system_economy()
    reward = submission.task.reward_amount if submission.task.reward_amount is not None else economy['task_reward']

    # Credit user
    user = submission.user
    user.wallet_balance += reward
    user.total_earned += reward
    user.tasks_completed_count += 1

    submission.status = 'approved'
    submission.reward_paid = reward
    submission.reviewed_by_id = current_user.id
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.rejection_reason = None

    tx = Transaction(
        user_id=user.id,
        amount=reward,
        tx_type='task_reward',
        description=f'Reward for completing quest: "{submission.task.title}"',
        reference_id=str(submission.id)
    )
    db.session.add(tx)
    db.session.commit()

    if request.is_json:
        return jsonify({
            'success': True,
            'message': f'Approved! {economy["currency_symbol"]}{reward:,.2f} credited to @{user.username}.',
            'reward': reward,
            'submission_id': submission.id
        })

    flash(f'Submission #{submission.id} approved! {economy["currency_symbol"]}{reward:,.2f} credited to @{user.username}.', 'success')
    return redirect(url_for('admin.reviews'))

@admin_bp.route('/reviews/<int:submission_id>/reject', methods=['POST'])
@admin_required
def reject_submission(submission_id):
    submission = db.get_or_404(TaskSubmission, submission_id)
    
    reason = request.form.get('reason') or (request.json.get('reason') if request.is_json else None) or 'Task requirements not satisfied or invalid screenshot'

    submission.status = 'rejected'
    submission.rejection_reason = reason
    submission.reviewed_by_id = current_user.id
    submission.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()

    if request.is_json:
        return jsonify({
            'success': True,
            'message': f'Submission #{submission.id} rejected.',
            'submission_id': submission.id,
            'reason': reason
        })

    flash(f'Submission #{submission.id} rejected with reason: "{reason}".', 'warning')
    return redirect(url_for('admin.reviews'))

@admin_bp.route('/tasks', methods=['GET', 'POST'])
@admin_required
def tasks():
    economy = get_system_economy()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            title = request.form.get('title', '').strip()
            category = request.form.get('category', 'Social').strip()
            url = request.form.get('url', '').strip()
            instructions = request.form.get('instructions', '').strip()
            reward_str = request.form.get('reward_amount', '').strip()

            if not title or not url or not instructions:
                flash('Title, target link URL, and instructions are required.', 'danger')
            else:
                reward_val = float(reward_str) if reward_str else None
                task = Task(
                    title=title,
                    category=category,
                    url=url,
                    instructions=instructions,
                    reward_amount=reward_val,
                    is_active=True
                )
                db.session.add(task)
                db.session.commit()
                flash(f'Task "{title}" created successfully!', 'success')
            return redirect(url_for('admin.tasks'))

    all_tasks = Task.query.order_by(Task.created_at.desc()).all()
    return render_template('admin/tasks.html', tasks=all_tasks, economy=economy)

@admin_bp.route('/tasks/<int:task_id>/toggle', methods=['POST'])
@admin_required
def toggle_task(task_id):
    task = db.get_or_404(Task, task_id)
    task.is_active = not task.is_active
    db.session.commit()
    status_str = "activated" if task.is_active else "paused"
    flash(f'Task "{task.title}" has been {status_str}.', 'info')
    return redirect(url_for('admin.tasks'))

@admin_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@admin_required
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    title = task.title
    db.session.delete(task)
    db.session.commit()
    flash(f'Task "{title}" deleted successfully.', 'info')
    return redirect(url_for('admin.tasks'))

@admin_bp.route('/withdrawals', methods=['GET', 'POST'])
@admin_required
def withdrawals():
    economy = get_system_economy()
    filter_status = request.args.get('status', 'pending')

    query = Withdrawal.query
    if filter_status in ('pending', 'paid', 'rejected'):
        query = query.filter_by(status=filter_status)

    all_withdrawals = query.order_by(Withdrawal.created_at.asc() if filter_status == 'pending' else Withdrawal.created_at.desc()).all()
    pending_count = Withdrawal.query.filter_by(status='pending').count()

    return render_template(
        'admin/withdrawals.html',
        withdrawals=all_withdrawals,
        filter_status=filter_status,
        pending_count=pending_count,
        economy=economy
    )

@admin_bp.route('/withdrawals/<int:withdrawal_id>/pay', methods=['POST'])
@admin_required
def pay_withdrawal(withdrawal_id):
    w = db.get_or_404(Withdrawal, withdrawal_id)
    if w.status == 'paid':
        flash('Withdrawal is already marked as paid.', 'info')
        return redirect(url_for('admin.withdrawals'))

    notes = request.form.get('notes', '').strip()
    w.status = 'paid'
    w.admin_notes = notes
    w.processed_at = datetime.now(timezone.utc)
    db.session.commit()

    flash(f'Withdrawal #{w.id} marked as PAID for @{w.user.username} ({w.bank_name} - {w.account_number}).', 'success')
    return redirect(url_for('admin.withdrawals'))

@admin_bp.route('/withdrawals/<int:withdrawal_id>/reject', methods=['POST'])
@admin_required
def reject_withdrawal(withdrawal_id):
    w = db.get_or_404(Withdrawal, withdrawal_id)
    if w.status != 'pending':
        flash('Only pending withdrawals can be rejected and refunded.', 'warning')
        return redirect(url_for('admin.withdrawals'))

    reason = request.form.get('reason', 'Invalid bank details or fraud check').strip()
    
    # Refund user wallet balance
    user = w.user
    user.wallet_balance += w.amount
    
    w.status = 'rejected'
    w.admin_notes = reason
    w.processed_at = datetime.now(timezone.utc)

    # Create refund transaction
    tx = Transaction(
        user_id=user.id,
        amount=w.amount,
        tx_type='refund',
        description=f'Refund for rejected withdrawal #{w.id}: {reason}',
        reference_id=f"REFUND-{w.id}"
    )
    db.session.add(tx)
    db.session.commit()

    flash(f'Withdrawal #{w.id} rejected and {economy_symbol_helper()}{w.amount:,.2f} refunded back to @{user.username}\'s wallet.', 'warning')
    return redirect(url_for('admin.withdrawals'))

def economy_symbol_helper():
    return SystemSetting.get('currency_symbol', '₦')

@admin_bp.route('/withdrawals/export/csv')
@admin_required
def export_withdrawals_csv():
    pending_only = request.args.get('pending_only', 'true') == 'true'
    query = Withdrawal.query
    if pending_only:
        query = query.filter_by(status='pending')
    
    items = query.order_by(Withdrawal.created_at.asc()).all()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Username', 'Amount', 'Bank Name', 'Account Number', 'Account Name', 'Status', 'Requested Date'])
    
    for item in items:
        writer.writerow([
            item.id,
            item.user.username,
            item.amount,
            item.bank_name,
            item.account_number,
            item.account_name,
            item.status,
            item.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
        
    filename = f"friday_payouts_{timestamp}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )

@admin_bp.route('/users')
@admin_required
def users():
    economy = get_system_economy()
    search = request.args.get('q', '').strip()
    
    query = User.query
    if search:
        query = query.filter(User.username.ilike(f'%{search}%') | User.referral_code.ilike(f'%{search}%'))
        
    all_users = query.order_by(User.created_at.desc()).limit(150).all()

    return render_template('admin/users.html', users=all_users, search=search, economy=economy)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own admin account.', 'danger')
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()
    status_str = "activated" if user.is_active else "deactivated"
    flash(f'User @{user.username} has been {status_str}.', 'info')
    return redirect(url_for('admin.users'))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        x_price = request.form.get('access_code_price', '5000').strip()
        currency_symbol = request.form.get('currency_symbol', '₦').strip()
        site_name = request.form.get('site_name', 'QuestPlatform').strip()
        allow_any_day = 'true' if request.form.get('allow_any_day_withdrawals') else 'false'
        
        google_ads_enabled = 'true' if request.form.get('google_ads_enabled') else 'false'
        google_ads_client_id = request.form.get('google_ads_client_id', '').strip()

        try:
            float(x_price)
        except ValueError:
            flash('Access Code Price ($X) must be a valid number.', 'danger')
            return redirect(url_for('admin.settings'))

        SystemSetting.set('access_code_price', x_price, 'Base access code price X')
        SystemSetting.set('currency_symbol', currency_symbol, 'Platform currency symbol')
        SystemSetting.set('site_name', site_name, 'Platform name')
        SystemSetting.set('allow_any_day_withdrawals', allow_any_day, 'Unlock withdrawals on any day')
        SystemSetting.set('google_ads_enabled', google_ads_enabled, 'Toggle Google Ads')
        SystemSetting.set('google_ads_client_id', google_ads_client_id, 'Google AdSense Publisher ID')

        flash('Platform economy and settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))

    economy = get_system_economy()
    return render_template('admin/settings.html', economy=economy)
