from app import create_app, db
from app.models import User, Department
from werkzeug.security import generate_password_hash

print("Starting init_db.py")
app = create_app()

with app.app_context():
    print("Creating departments")
    dept1 = Department(name='Field Operations')
    dept2 = Department(name='Power Team')
    db.session.add_all([dept1, dept2])
    db.session.commit()

    print("Creating users")
    admin = User(
        username='admin',
        password=generate_password_hash('admin123'),
        role='admin',
        email='admin@isp.com'
    )
    engineer1 = User(
        username='engineer1',
        password=generate_password_hash('eng123'),
        role='engineer',
        department_id=dept1.id,
        email='engineer1@isp.com'
    )
    engineer2 = User(
        username='engineer2',
        password=generate_password_hash('eng123'),
        role='engineer',
        department_id=dept2.id,
        email='engineer2@isp.com'
    )

    print("[DEBUG] Admin username:", admin.username)
    print("[DEBUG] Engineer1 username:", engineer1.username)
    print("[DEBUG] Engineer2 username:", engineer2.username)

    db.session.add_all([admin, engineer1, engineer2])
    db.session.commit()
    print("Sample data added!")