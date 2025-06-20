from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from datetime import datetime

from . import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    department = db.relationship('Department', backref='users')


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'Field Ops', 'Power Team'

class Fault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # e.g., 'Fiber Cut', 'Power Issue'
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'Low', 'Medium', 'High'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    assigned_to = db.relationship('Department', backref='faults')
    status = db.Column(db.String(20), default='Open')  # 'Open', 'Pending', 'Resolved'
    resolved_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)