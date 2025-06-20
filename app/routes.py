from flask import current_app, Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, logout_user, current_user
from app import db, mail
from app.models import User, Department, Fault
from flask_mail import Message
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash

bp = Blueprint('main', __name__)

def init_routes(app):
    app.register_blueprint(bp)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"[DEBUG] Username entered: {username}")
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"[DEBUG] User found: {user.username}")
            if check_password_hash(user.password, password):
                print("[DEBUG] Password match")
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                print("[DEBUG] Password mismatch")
        else:
            print("[DEBUG] No user found")
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    current_time = datetime.utcnow() + timedelta(hours=1)  # UTC+1

    if current_user.role == 'admin':
        faults_query = Fault.query

        # Filters from form
        status = request.args.get('status')
        severity = request.args.get('severity')
        query = request.args.get('query')

        if status:
            faults_query = faults_query.filter_by(status=status)
        if severity:
            faults_query = faults_query.filter_by(severity=severity)
        if query:
            search = f"%{query}%"
            faults_query = faults_query.filter(
                Fault.type.ilike(search) | Fault.location.ilike(search)
            )

        faults = faults_query.all()

        # Counts from unfiltered list for stats
        all_faults = Fault.query.all()
        pending_open = sum(1 for f in all_faults if f.status == 'Open')
        pending_progress = sum(1 for f in all_faults if f.status == 'In Progress')
        resolved_count = sum(1 for f in all_faults if f.status == 'Resolved')
        total_pending_time = sum(
            ((current_time - f.created_at).total_seconds() / 3600)
            for f in all_faults if f.status != 'Resolved'
        )

        departments = Department.query.all()
        dept_stats = []
        for dept in departments:
            dept_faults = [f for f in all_faults if f.assigned_to_id == dept.id and f.status != 'Resolved']
            fault_count = len(dept_faults)
            total_hours = sum(
                ((current_time - f.created_at).total_seconds() / 3600)
                for f in dept_faults
            )
            if fault_count > 0:
                dept_stats.append({
                    'name': dept.name,
                    'count': fault_count,
                    'hours': int(total_hours)
                })

        return render_template(
            'dashboard.html',
            faults=faults,
            current_time=current_time,
            pending_open=pending_open,
            pending_progress=pending_progress,
            resolved_count=resolved_count,
            total_pending_time=int(total_pending_time),
            dept_stats=dept_stats
        )

    else:
        faults = Fault.query.filter_by(assigned_to_id=current_user.department_id).all()
        return render_template('dept_dashboard.html', faults=faults, current_time=current_time)

@bp.route('/log_fault', methods=['GET', 'POST'])
@login_required
def log_fault():
    if current_user.role != 'admin':
        flash('Only admins can log faults.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        fault_type = request.form['type']
        description = request.form['description']
        location = request.form['location']
        severity = request.form['severity']
        dept_id = request.form['department_id']
        fault = Fault(
            type=fault_type,
            description=description,
            location=location,
            severity=severity,
            assigned_to_id=int(dept_id) if dept_id else None,
            status='Open'
        )
        db.session.add(fault)
        db.session.commit()

        if dept_id:
            dept = Department.query.get(dept_id)
            users = User.query.filter_by(department_id=dept_id, role='engineer').all()
            for user in users:
                msg = Message(
                    subject=f'New Fault Assigned: #{fault.id} - {fault.type}',
                    sender=current_app.config['MAIL_USERNAME'],
                    recipients=[user.email]
                )
                msg.body = f'A new fault has been assigned to {dept.name}:\n\nType: {fault.type}\nLocation: {location}\nSeverity: {fault.severity}\nDescription: {description}'
                mail.send(msg)
        flash('Fault logged successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    departments = Department.query.all()
    return render_template('log_fault.html', departments=departments)

@bp.route('/update_fault/<int:fault_id>', methods=['POST'])
@login_required
def update_fault(fault_id):
    fault = Fault.query.get_or_404(fault_id)
    if current_user.role == 'engineer' and fault.assigned_to_id != current_user.department_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.dashboard'))

    status = request.form['status']
    notes = request.form.get('notes')
    fault.status = status
    fault.notes = notes

    if status == 'Resolved':
        fault.resolved_at = datetime.utcnow()
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            msg = Message(
                subject=f'Fault #{fault.id} Resolved',
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[admin.email]
            )
            msg.body = f'Fault #{fault.id} ({fault.type}) has been resolved by {current_user.department.name}.\n\nNotes: {notes}'
            mail.send(msg)

    db.session.commit()
    flash('Fault updated successfully!', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

@bp.route('/history')
@login_required
def history():
    faults = Fault.query.order_by(Fault.created_at.desc()).all()
    return render_template('history.html', faults=faults)

@bp.route('/fault/<int:fault_id>')
@login_required
def view_fault(fault_id):
    fault = Fault.query.get_or_404(fault_id)
    return render_template('fault_detail.html', fault=fault)
