from flask import Flask, request, jsonify,render_template, redirect
from database import engine, Base
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from models.doctors import Doctor 

# Initialize Flask app
app = Flask(__name__)

# Database setup (replace with your actual database URL)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
@app.route("/")
def index():
    return render_template("index.html")

@app.route('/doctors')
def add_doctor():
    if request.method=="GET":
        return render_template("doctors.html")

@app.route('/appointments')
def appointment():
     return render_template("appointments.html")
@app.route('/schedule')
def schedule():
     return render_template("schedule.html")
@app.route('/department')
def department():
     return render_template('departments.html')
@app.route('/patients')
def patient():
     return render_template('patients.html')
@app.route('/add-doctor',  methods=['POST','GET'])
def add_d():
    if request.method=="GET":
        return render_template("add_doctor.html")
    try:
            # Extract data from the form submission
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            password = request.form.get('password')
            dob = request.form.get('dob')  # Should be in YYYY-MM-DD format
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            avatar = request.form.get('avatar')  # Optional
            status = request.form.get('status', 'true').lower() == 'true'  # Default to True
            education_info = request.form.get('education_info')
            specialisation = request.form.get('specialisation')

            # Validate required fields
            required_fields = [first_name, last_name, email, password, dob, gender, phone, education_info, specialisation]
            if not all(required_fields):
                return jsonify({"error": "All required fields must be filled"}), 400

            # Create a new doctor object
            new_doctor = Doctor(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=generate_password_hash(password),  # Hash the password
                dob=dob,
                gender=gender,
                phone=phone,
                avatar=avatar,  # Optional
                status=status,
                education_info=education_info,
                specialisation=specialisation
            )

            # Add the doctor to the database
            session.add(new_doctor)
            session.commit()

            # return jsonify({"message": "Doctor added successfully", "doctor_id": new_doctor.id}), 201
            return redirect("/doctors")
    except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 500
    finally:
            session.close()
    
        

if __name__ == '__main__':
    app.run(debug=True)
