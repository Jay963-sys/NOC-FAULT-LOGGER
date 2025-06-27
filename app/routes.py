from flask import current_app, Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_user, login_required, logout_user, current_user
from app import db, mail
from app.models import User, Department, Fault, Customer
from flask_mail import Message
from datetime import datetime
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from werkzeug.security import check_password_hash
from collections import Counter
from sqlalchemy import func
from io import StringIO
import csv

bp = Blueprint('main', __name__)

def init_routes(app):
    app.register_blueprint(bp)

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

@bp.route('/log_fault', methods=['GET', 'POST'])
@login_required
def log_fault():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        customer_id = request.form['customer_id']
        description = request.form['description']
        assigned_to_id = request.form.get('assigned_to_id')

        lagos_tz = ZoneInfo('Africa/Lagos')
        today = datetime.now(lagos_tz).strftime('%Y%m%d')
        
        count_today = Fault.query.filter(
            func.strftime('%Y%m%d', func.datetime(Fault.created_at, 'localtime')) == today
        ).count() + 1

        ticket_number = f"{today}-{str(count_today).zfill(2)}"

        lagos_time = datetime.now(ZoneInfo('Africa/Lagos'))
        created_at = lagos_time.astimezone(timezone.utc)

        print(f"Lagos Time: {lagos_time}, UTC Time Stored: {created_at}")

        

        fault = Fault(
            customer_id=customer_id,
            description=description,
            status='Open',
            ticket_number=ticket_number,
            assigned_to_id=assigned_to_id if assigned_to_id else None,
            created_at=datetime.now(ZoneInfo('Africa/Lagos')).astimezone(timezone.utc),
            severity='Low'
        )
        db.session.add(fault)
        db.session.commit()

        flash(f'New fault logged successfully. Ticket Number: {ticket_number}', 'success')
        return redirect(url_for('main.dashboard'))

    customers = Customer.query.all()
    departments = Department.query.all()
    return render_template('log_fault.html', customers=customers, departments=departments)

@bp.route('/update_dashboard_table')
@login_required
def update_dashboard_table():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    filter_status = request.args.get('filter', 'all')
    search_query = request.args.get('search', '').strip()
    month = request.args.get('month')
    year = request.args.get('year')

    faults_query = Fault.query

    # Filter by status
    if filter_status != 'all':
        faults_query = faults_query.filter_by(status=filter_status)

    # Search by Customer Name or Customer ID
    if search_query:
        faults_query = faults_query.join(Customer).filter(
            (Customer.company.ilike(f"%{search_query}%")) |
            (Customer.id.cast(db.String).ilike(f"%{search_query}%"))
        )

    # Filter by Month
    if month and month.isdigit():
        faults_query = faults_query.filter(db.extract('month', Fault.created_at) == int(month))

    # Filter by Year
    if year and year.isdigit():
        faults_query = faults_query.filter(db.extract('year', Fault.created_at) == int(year))

    faults = faults_query.all()

    table_rows = ""
    for fault in faults:
        pending_hours = (
            f"{fault.age_hours:.1f}" if fault.status in ['Open', 'In Progress'] else "N/A"
        )

        row = f"""
        <tr class="fault-row" data-fault-id="{fault.id}">
            <td>{fault.ticket_number}</td>
            <td>{fault.customer.company if fault.customer else 'N/A'}</td>
            <td>{fault.customer.circuit_id if fault.customer else 'N/A'}</td>
            <td>{fault.description}</td>
            <td class="{fault.status.lower()}">
                <select class="status-select" data-fault-id="{fault.id}">
                    <option value="Open" {"selected" if fault.status == 'Open' else ""}>Open</option>
                    <option value="In Progress" {"selected" if fault.status == 'In Progress' else ""}>In Progress</option>
                    <option value="Resolved" {"selected" if fault.status == 'Resolved' else ""}>Resolved</option>
                    <option value="Closed" {"selected" if fault.status == 'Closed' else ""}>Closed</option>
                </select>
            </td>
            <td><span class="badge {fault.dynamic_severity.lower()}">{fault.dynamic_severity}</span></td>
            <td>{fault.local_created_at}</td>
            <td>{pending_hours}</td>
            <td>
                <button class="action-btn edit" data-fault-id="{fault.id}">Edit</button>
                <button class="action-btn delete" data-fault-id="{fault.id}">Delete</button>
            </td>
        </tr>
        """
        table_rows += row

    return jsonify({'table': table_rows})


@bp.route('/update_fault_status/<int:fault_id>', methods=['POST'])
@login_required
def update_fault_status(fault_id):
    fault = Fault.query.get_or_404(fault_id)
    new_status = request.json.get('status')
    fault.status = new_status
    db.session.commit()
    return jsonify({'message': f'Fault {fault.id} status updated to {new_status}.'})

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard' if current_user.role == 'admin' else 'main.dept_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('main.dashboard' if user.role == 'admin' else 'main.dept_dashboard'))

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
    if current_user.role != 'admin':
        return redirect(url_for('main.dept_dashboard'))

    faults = Fault.query.all()
    lagos_tz = ZoneInfo('Africa/Lagos')
    current_time = datetime.now(lagos_tz)

    pending_open = sum(1 for f in faults if f.status == 'Open')
    pending_progress = sum(1 for f in faults if f.status == 'In Progress')
    resolved_count = sum(1 for f in faults if f.status == 'Resolved')

    dept_fault_counts = Counter(f.assigned_to.name if f.assigned_to else "Unassigned" for f in faults)
    date_counts = Counter(f.local_created_at.split(' ')[0] for f in faults)
    severity_counter = Counter(f.dynamic_severity for f in faults)

    severity_chart_data = {
        "labels": ["Low", "Medium", "High"],
        "values": [
            severity_counter.get("Low", 0),
            severity_counter.get("Medium", 0),
            severity_counter.get("High", 0)
        ]
    }

    chart_data = {
        "dept_labels": list(dept_fault_counts.keys()),
        "dept_values": list(dept_fault_counts.values()),
        "date_labels": list(date_counts.keys()),
        "date_values": list(date_counts.values())
    }

    return render_template(
        'dashboard.html',
        faults=faults,
        pending_open=pending_open,
        pending_progress=pending_progress,
        resolved_count=resolved_count,
        pending_faults=[f for f in faults if f.status == 'Open'],
        progress_faults=[f for f in faults if f.status == 'In Progress'],
        resolved_faults=[f for f in faults if f.status == 'Resolved'],
        current_time=current_time.strftime('%Y-%m-%d %H:%M'),
        severity_chart_data=severity_chart_data,
        chart_data=chart_data
    )

@bp.route('/dept_dashboard')
@login_required
def dept_dashboard():
    if current_user.role != 'engineer':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    faults = Fault.query.filter_by(assigned_to_id=current_user.department_id).all()
    current_time = datetime.now(ZoneInfo('Africa/Lagos'))

    return render_template('dept_dashboard.html', faults=faults, current_time=current_time)

@bp.route('/customers')
@login_required
def customers():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    search_query = request.args.get('search', '').strip()

    if search_query:
        customers = Customer.query.filter(
            (Customer.company.ilike(f'%{search_query}%')) |
            (Customer.contact_person.ilike(f'%{search_query}%')) |
            (Customer.ip_address.ilike(f'%{search_query}%')) |
            (Customer.pop_site.ilike(f'%{search_query}%'))
        ).all()
    else:
        customers = Customer.query.all()

    return render_template('customers.html', customers=customers, search_query=search_query)


@bp.route('/add_customer', methods=['POST'])
@login_required
def add_customer():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    company = request.form['company']
    circuit_id = request.form.get('circuit_id')
    ip_address = request.form.get('ip_address')
    pop_site = request.form.get('pop_site')
    email = request.form.get('email')
    switch_info = request.form.get('switch_info')

    customer = Customer(
        company=company,
        circuit_id=circuit_id,
        ip_address=ip_address,
        pop_site=pop_site,
        email=email,
        switch_info=switch_info
    )
    db.session.add(customer)
    db.session.commit()

    flash('Customer added successfully.', 'success')
    return redirect(url_for('main.customers'))

@bp.route('/edit_customer/<int:customer_id>', methods=['POST'])
@login_required
def edit_customer(customer_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    customer = Customer.query.get_or_404(customer_id)
    data = request.get_json()

    customer.company = data.get('company')
    customer.ip_address = data.get('ip_address')
    customer.pop_site = data.get('pop_site')
    customer.circuit_id = data.get('circuit_id')
    customer.email = data.get('email')
    customer.switch_info = data.get('switch_info')

    db.session.commit()
    return jsonify({'message': 'Customer updated successfully.'})

@bp.route('/delete_customer/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    customer = Customer.query.get_or_404(customer_id)

    # Optional: Prevent deleting customers with active faults
    active_faults = Fault.query.filter_by(customer_id=customer.id).count()
    if active_faults > 0:
        return jsonify({'error': 'Cannot delete customer with active faults.'}), 400

    db.session.delete(customer)
    db.session.commit()

    return jsonify({'message': 'Customer deleted successfully.'})

@bp.route('/get_fault_details/<int:fault_id>')
@login_required
def get_fault_details(fault_id):
    fault = Fault.query.get_or_404(fault_id)
    customer = fault.customer

    fault_data = {
        'ticket_number': fault.ticket_number,
        'description': fault.description,
        'type': fault.type,
        'location': fault.location,
        'status': fault.status,
        'severity': fault.dynamic_severity,
        'created_at': fault.local_created_at,
        'customer': {
            'company': customer.company if customer else 'N/A',
            'circuit_id': customer.circuit_id if customer else 'N/A',
            'ip_address': customer.ip_address if customer else 'N/A',
            'pop_site': customer.pop_site if customer else 'N/A',
            'email': customer.email if customer else 'N/A',
            'switch_info': customer.switch_info if customer else 'N/A'
        },
        'history': []
    }

    # Add fault history for this customer, excluding current fault
    if customer:
        for f in customer.faults:
            if f.id != fault.id:
                fault_data['history'].append({
                    'id': f.id,
                    'issue': f.description,
                    'status': f.status,
                    'logged_time': f.local_created_at
                })

    return jsonify(fault_data)


@bp.route('/departments')
@login_required
def departments():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    departments = Department.query.all()
    return render_template('departments.html', departments=departments)


@bp.route('/add_department', methods=['POST'])
@login_required
def add_department():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    name = request.form['name']

    if Department.query.filter_by(name=name).first():
        return jsonify({'error': 'Department already exists'}), 400

    dept = Department(name=name)
    db.session.add(dept)
    db.session.commit()
    return jsonify({'message': 'Department added successfully'})


@bp.route('/delete_department/<int:dept_id>', methods=['POST'])
@login_required
def delete_department(dept_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    dept = Department.query.get_or_404(dept_id)

    if dept.faults:
        return jsonify({'error': 'Cannot delete department with assigned faults'}), 400

    db.session.delete(dept)
    db.session.commit()
    return jsonify({'message': 'Department deleted successfully'})

@bp.route('/delete_fault/<int:fault_id>', methods=['POST'])
@login_required
def delete_fault(fault_id):
    if current_user.role != 'admin':
        return jsonify({"message": "Unauthorized"}), 403

    fault = Fault.query.get_or_404(fault_id)
    db.session.delete(fault)
    db.session.commit()

    return jsonify({"message": "Fault deleted successfully"})


@bp.route('/edit_fault/<int:fault_id>', methods=['POST'])
@login_required
def edit_fault(fault_id):
    fault = Fault.query.get_or_404(fault_id)
    data = request.get_json()

    fault.type = data.get('type', fault.type)
    fault.description = data.get('description', fault.description)
    fault.location = data.get('location', fault.location)

    db.session.commit()
    return jsonify({"message": "Fault updated successfully"})
