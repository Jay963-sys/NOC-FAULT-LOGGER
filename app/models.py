from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

    users = db.relationship('User', back_populates='department', lazy=True)
    faults = db.relationship('Fault', backref='assigned_to', lazy=True)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)

    department = db.relationship('Department', back_populates='users')


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(120), nullable=False)
    circuit_id = db.Column(db.String(100))
    ip_address = db.Column(db.String(100))
    pop_site = db.Column(db.String(100))
    email = db.Column(db.String(120))
    switch_info = db.Column(db.String(200))

    faults = db.relationship('Fault', back_populates='customer', lazy=True)


class Fault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    type = db.Column(db.String(100))
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    status = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)  # ✅ You were missing this!
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    severity = db.Column(db.String(20), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    owner_of_ticket = db.Column(db.String(100))
    assigned_to_person = db.Column(db.String(100))

    customer = db.relationship("Customer", back_populates="faults")

    @property
    def age_hours(self):
        """Accurate pending hours, freezes when resolved or closed."""
        tz = ZoneInfo('Africa/Lagos')

        if self.closed_at:
            end_time = self.closed_at
        elif self.resolved_at:
            end_time = self.resolved_at
        else:
            end_time = datetime.now(timezone.utc)

        created_at = self.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return (end_time.astimezone(tz) - created_at.astimezone(tz)).total_seconds() / 3600

    @property
    def total_pending_hours(self):
        tz = ZoneInfo('Africa/Lagos')
        if self.closed_at:
            end_time = self.closed_at
        elif self.resolved_at:
            end_time = self.resolved_at
        else:
            end_time = datetime.now(timezone.utc)

        created_at = self.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return (end_time.astimezone(tz) - created_at.astimezone(tz)).total_seconds() / 3600

    @property
    def dynamic_severity(self):
        if self.age_hours < 4:
            return 'Low'
        elif self.age_hours < 12:
            return 'Medium'
        else:
            return 'High'

    @property
    def local_created_at(self):
        tz = ZoneInfo('Africa/Lagos')
        created_at = self.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at.astimezone(tz).strftime('%Y-%m-%d %H:%M')
    
    @property
    def local_resolved_at(self):
        if self.resolved_at:
            tz = ZoneInfo('Africa/Lagos')
            resolved_at = self.resolved_at
            if resolved_at.tzinfo is None:
                resolved_at = resolved_at.replace(tzinfo=timezone.utc)
            return resolved_at.astimezone(tz).strftime('%Y-%m-%d %H:%M')
        return 'N/A'

    @property
    def local_closed_at(self):
        if self.closed_at:
            tz = ZoneInfo('Africa/Lagos')
            closed_at = self.closed_at
            if closed_at.tzinfo is None:
                closed_at = closed_at.replace(tzinfo=timezone.utc)
            return closed_at.astimezone(tz).strftime('%Y-%m-%d %H:%M')
        return 'N/A'
