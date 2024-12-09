from main import db, app
from models.users import User
from models.doctors import Doctor
from models.lab_technicians import LabTechnician
from models.lab_results import LabResult
from werkzeug.security import generate_password_hash

def create_initial_users():
    # Create admin user
    admin_user = User(
        email='admin@hospital.com', 
        role='admin', 
        password='admin123'
    )
    db.session.add(admin_user)

    # Create lab technician user
    lab_tech_user = User(
        email='labtech@hospital.com', 
        role='lab_technician', 
        password='labtech123'
    )
    db.session.add(lab_tech_user)

    # Create users for existing doctors
    doctors = Doctor.query.all()
    for doctor in doctors:
        # Create user with linked doctor
        doctor_user = User(
            email=doctor.email, 
            role='doctor', 
            password=doctor.password,  # Assuming direct password comparison
            doctor_id=doctor.id  # Link the doctor
        )
        db.session.add(doctor_user)

    # Commit all users
    db.session.commit()

def create_initial_lab_technicians():
    # Check if lab technician already exists
    existing_tech = LabTechnician.query.filter_by(email='labtech@hospital.com').first()
    if not existing_tech:
        # Create a default lab technician
        lab_tech = LabTechnician(
            first_name='Lab',
            last_name='Technician',
            email='labtech@hospital.com',
            phone='1234567890',
            password=generate_password_hash('labtech123'),
            specialization='General Lab Services',
            status=True
        )
        db.session.add(lab_tech)
        db.session.commit()

if __name__ == '__main__':
    # Ensure database is created
    with app.app_context():
        # Drop all tables and recreate (use with caution!)
        db.drop_all()
        db.create_all()
        
        # Create initial users
        create_initial_users()
        create_initial_lab_technicians()
        
        print("Initial users and lab technicians created successfully!")
