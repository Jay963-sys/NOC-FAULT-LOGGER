from app import app, db
from app.models import User, Department, Customer, Fault
from flask.cli import with_appcontext

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Department': Department,
        'Customer': Customer,
        'Fault': Fault
    }
