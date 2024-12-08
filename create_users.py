
from models.users import User
from models.doctors import Doctor
from main import app, db
def create_initial_users():
    with app.app_context():
        # Check if users already exist
        existing_users = User.query.all()
        if existing_users:
            print("Users already exist. Skipping creation.")
            return

        # Create admin user
        admin = User(username='admin', email='admin@hospital.com', role='admin')
        admin.set_password('admin123')

        # Create users for existing doctors
        doctors = Doctor.query.all()
        for doctor in doctors:
            # Create a user for each doctor using their existing email and password
            doctor_user = User(
                username=f"{doctor.first_name.lower()}.{doctor.last_name.lower()}",
                email=doctor.email,
                role='doctor'
            )
            # Set the password directly since it's already hashed
            doctor_user.password_hash = doctor.password

            db.session.add(doctor_user)

        # Create lab technician user
        lab_tech = User(username='labtech', email='labtech@hospital.com', role='lab_technician')
        lab_tech.set_password('labtech123')

        # Add users to session and commit
        db.session.add(admin)
        db.session.add(lab_tech)
        
        db.session.commit()
        print("Initial users created successfully!")

if __name__ == '__main__':
    create_initial_users()
