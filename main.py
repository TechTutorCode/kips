from flask import Flask, request, jsonify, render_template, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///kips.db"
app.config["SECRET_KEY"] = "#deno0707@mwangi"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models after db initialization to avoid circular imports
from models.users import User
from models.patients import Patient
from models.doctors import Doctor
from models.patient_records import PatientRecord
from models.lab_results import LabResult
from models.lab_services import LabService
from models.pharmacy import PharmacyItem
from models.billing import Bill, BillItem, Payment
from models.lab_technicians import LabTechnician

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Role-based access control decorator
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

with app.app_context():
    db.create_all()  # Ensures all tables are created before handling requests

@app.route("/")
@login_required
def index():
    # Get today's date range
    today = datetime(2024, 12, 9).date()  # Using provided timestamp
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get today's appointments
    todays_appointments = PatientRecord.query.filter(
        PatientRecord.next_visit.between(today_start, today_end)
    ).order_by(PatientRecord.next_visit).all()
    appointment_count = len(todays_appointments)
    
    # Get pending payments (total balance from unpaid bills)
    pending_bills = Bill.query.filter(Bill.status.in_(['Unpaid', 'Partially Paid'])).all()
    pending_payments = sum(bill.total_amount - bill.paid_amount for bill in pending_bills)
    
    # Get low stock items
    low_stock_items = PharmacyItem.query.filter(
        PharmacyItem.quantity <= PharmacyItem.reorder_level
    ).all()
    low_stock_count = len(low_stock_items)
    
    # Calculate today's revenue from payments
    today_payments = Payment.query.filter(
        Payment.payment_date.between(today_start, today_end)
    ).all()
    today_revenue = sum(payment.amount for payment in today_payments)
    
    # Get recent bills
    recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(5).all()
    
    return render_template("index.html",
                         appointment_count=appointment_count,
                         pending_payments=pending_payments,
                         low_stock_count=low_stock_count,
                         today_revenue=today_revenue,
                         todays_appointments=todays_appointments,
                         low_stock_items=low_stock_items,
                         recent_bills=recent_bills)

@app.route('/doctors')
@login_required
@role_required(['admin', 'doctor'])
def add_doctor():
    if request.method=="GET":
        doctors=Doctor.query.all()
        print(doctors)
        return render_template("doctors.html", doctors=doctors)

@app.route('/department')
@login_required
def department():
     return render_template('departments.html')

@app.route('/patients')
@login_required
@role_required(['admin', 'doctor'])
def patient():
     patients = Patient.query.all()
     return render_template('patients.html', patients=patients)

@app.route('/add-doctor',  methods=['POST','GET'])
@login_required
@role_required(['admin'])
def add_d():
    if request.method=="GET":
        return render_template("add_doctor.html")
    
    if request.method=="POST":
        try:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            password = request.form.get('password')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            
            # Create new doctor
            new_doctor = Doctor(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                gender=gender,
                phone=phone,
                status=True
            )
            
            # Create corresponding user account
            from models.users import User
            new_user = User(
                username=f"{first_name.lower()}.{last_name.lower()}",
                email=email,
                role='doctor'
            )
            new_user.password_hash = password  # Use the same password
            
            # Add both to session
            db.session.add(new_doctor)
            db.session.add(new_user)
            
            db.session.commit()
            
            flash('Doctor added successfully!', 'success')
            return redirect(url_for('add_doctor'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding doctor: {str(e)}', 'error')
            return render_template("add_doctor.html")

@app.route('/profile/<int:id>')
@login_required
def profile(id):
     doctor = Doctor.query.filter_by(id=id).first()
     return render_template("profile.html", doctor=doctor)      

@app.route('/add-patient',  methods=['POST','GET'])
@login_required
@role_required(['admin', 'doctor'])
def add_p():
    if request.method=="GET":
        return render_template("add_patient.html")
    elif request.method == "POST":
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        address = request.form.get('address')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        dob = request.form.get('dob')
        
        # Create new patient
        patient = Patient(
            first_name=first_name,
            last_name=last_name,
            email=email,
            address=address,
            gender=gender,
            phone=phone,
            dob=datetime.strptime(dob, '%Y-%m-%d') if dob else None
        )
        
        db.session.add(patient)
        db.session.commit()
        
        flash('Patient added successfully!')
        return redirect(url_for('patient'))

@app.route('/delete-patient', methods=['POST'])
@login_required
@role_required(['admin', 'doctor'])
def delete_patient():
    patient_id = request.form.get('patient_id')
    if patient_id:
        patient = Patient.query.get(patient_id)
        if patient:
            db.session.delete(patient)
            db.session.commit()
            flash('Patient deleted successfully!')
    return redirect(url_for('patient'))

@app.route('/edit-doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    if request.method == 'POST':
        doctor.first_name = request.form['first_name']
        doctor.last_name = request.form['last_name']
        doctor.email = request.form['email']
        doctor.gender = request.form['gender']
        doctor.phone = request.form['phone']
        doctor.status = request.form['status'] == 'true'
        
        # Only update password if a new one is provided
        new_password = request.form.get('password')
        if new_password:
            doctor.password = generate_password_hash(new_password)
            
        db.session.commit()
        flash('Doctor updated successfully!')
        return redirect(url_for('add_doctor'))
        
    return render_template('edit_doctor.html', doctor=doctor)

@app.route('/edit-patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'doctor'])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        patient.first_name = request.form['first_name']
        patient.last_name = request.form['last_name']
        patient.email = request.form.get('email')
        patient.gender = request.form['gender']
        patient.phone = request.form['phone']
        patient.address = request.form.get('address')
        
        # Handle date of birth
        dob = request.form.get('dob')
        if dob:
            patient.dob = datetime.strptime(dob, '%Y-%m-%d')
        else:
            patient.dob = None
            
        db.session.commit()
        flash('Patient updated successfully!')
        return redirect(url_for('patient'))
        
    return render_template('edit_patient.html', patient=patient)

@app.route('/patient-records/<int:patient_id>')
@login_required
@role_required(['admin', 'doctor'])
def patient_records(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = PatientRecord.query.filter_by(patient_id=patient_id).order_by(PatientRecord.created_at.desc()).all()
    
    # Get lab results for this patient
    lab_results = BillItem.query.join(Bill).join(Bill.patient).filter(
        BillItem.item_type == 'Lab Service',
        Bill.patient_id == patient_id,
        Bill.status.in_(['Paid', 'Partial'])
    ).order_by(BillItem.created_at.desc()).all()
    
    return render_template('patient_records.html', 
                         patient=patient, 
                         records=records,
                         lab_results=lab_results)

@app.route('/add-record/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'doctor'])
def add_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctors = Doctor.query.all()
    
    if request.method == 'POST':
        record = PatientRecord(
            patient_id=patient_id,
            doctor_id=request.form['doctor_id'],
            diagnosis=request.form['diagnosis'],
            prescription=request.form.get('prescription'),
            notes=request.form.get('notes')
        )
        
        next_visit = request.form.get('next_visit')
        if next_visit:
            record.next_visit = datetime.strptime(next_visit, '%Y-%m-%d')
            
        db.session.add(record)
        db.session.commit()
        flash('Patient record added successfully!')
        return redirect(url_for('patient_records', patient_id=patient_id))
        
    return render_template('add_record.html', patient=patient, doctors=doctors)

@app.route('/edit-record/<int:record_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'doctor'])
def edit_record(record_id):
    record = PatientRecord.query.get_or_404(record_id)
    doctors = Doctor.query.all()
    
    if request.method == 'POST':
        record.doctor_id = request.form['doctor_id']
        record.diagnosis = request.form['diagnosis']
        record.prescription = request.form.get('prescription')
        record.notes = request.form.get('notes')
        
        next_visit = request.form.get('next_visit')
        if next_visit:
            record.next_visit = datetime.strptime(next_visit, '%Y-%m-%d')
        else:
            record.next_visit = None
            
        db.session.commit()
        flash('Patient record updated successfully!')
        return redirect(url_for('patient_records', patient_id=record.patient_id))
        
    return render_template('edit_record.html', record=record, doctors=doctors)

@app.route('/appointments')
@login_required
def appointments():
    today = datetime.now().date()
    # Get all records with next_visit date that's today or in the future
    appointments = PatientRecord.query.filter(
        PatientRecord.next_visit != None
    ).order_by(PatientRecord.next_visit).all()
    
    return render_template('appointments.html', appointments=appointments, today=today)

@app.route('/add-appointment', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'doctor'])
def add_appointment():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        appointment_date = datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date()
        notes = request.form.get('notes')

        # Create a new patient record with the appointment date
        record = PatientRecord(
            patient_id=patient_id,
            doctor_id=doctor_id,
            next_visit=appointment_date,
            notes=notes if notes else "Scheduled appointment"
        )
        
        db.session.add(record)
        db.session.commit()
        
        flash('Appointment scheduled successfully!', 'success')
        return redirect(url_for('appointments'))
    
    # GET request - show the form
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    return render_template('add_appointment.html', patients=patients, doctors=doctors)

@app.route('/lab-services')
@login_required
def lab_services():
    services = LabService.query.order_by(LabService.name).all()
    return render_template('lab_services.html', services=services)

@app.route('/add-lab-service', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_lab_service():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        cost = float(request.form.get('cost'))

        service = LabService(
            name=name,
            description=description,
            cost=cost
        )
        
        db.session.add(service)
        db.session.commit()
        
        flash('Lab service added successfully!', 'success')
        return redirect(url_for('lab_services'))
    
    return render_template('add_lab_service.html')

@app.route('/edit-lab-service/<int:service_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_lab_service(service_id):
    service = LabService.query.get_or_404(service_id)
    
    if request.method == 'POST':
        service.name = request.form.get('name')
        service.description = request.form.get('description')
        service.cost = float(request.form.get('cost'))
        
        db.session.commit()
        flash('Lab service updated successfully!', 'success')
        return redirect(url_for('lab_services'))
    
    return render_template('edit_lab_service.html', service=service)

@app.route('/delete-lab-service/<int:service_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_lab_service(service_id):
    service = LabService.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    
    flash('Lab service deleted successfully!', 'success')
    return redirect(url_for('lab_services'))

@app.route('/pharmacy')
@login_required
def pharmacy():
    items = PharmacyItem.query.order_by(PharmacyItem.name).all()
    return render_template('pharmacy.html', items=items)

@app.route('/add-pharmacy-item', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_pharmacy_item():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        unit = request.form.get('unit')
        quantity = int(request.form.get('quantity'))
        cost_per_unit = float(request.form.get('cost_per_unit'))
        reorder_level = int(request.form.get('reorder_level'))

        item = PharmacyItem(
            name=name,
            category=category,
            description=description,
            unit=unit,
            quantity=quantity,
            cost_per_unit=cost_per_unit,
            reorder_level=reorder_level
        )
        
        db.session.add(item)
        db.session.commit()
        
        flash('Pharmacy item added successfully!', 'success')
        return redirect(url_for('pharmacy'))
    
    return render_template('add_pharmacy_item.html')

@app.route('/edit-pharmacy-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_pharmacy_item(item_id):
    item = PharmacyItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.category = request.form.get('category')
        item.description = request.form.get('description')
        item.unit = request.form.get('unit')
        item.quantity = int(request.form.get('quantity'))
        item.cost_per_unit = float(request.form.get('cost_per_unit'))
        item.reorder_level = int(request.form.get('reorder_level'))
        
        db.session.commit()
        flash('Pharmacy item updated successfully!', 'success')
        return redirect(url_for('pharmacy'))
    
    return render_template('edit_pharmacy_item.html', item=item)

@app.route('/delete-pharmacy-item/<int:item_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_pharmacy_item(item_id):
    item = PharmacyItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    
    flash('Pharmacy item deleted successfully!', 'success')
    return redirect(url_for('pharmacy'))

@app.route('/billing')
@login_required
def billing():
    bills = Bill.query.order_by(Bill.created_at.desc()).all()
    # Update statuses based on balance
    for bill in bills:
        if bill.balance > 0:
            bill.status = 'Partial'
        elif bill.paid_amount >= bill.total_amount and bill.balance == 0:
            bill.status = 'Paid'
        else:
            bill.status = 'Pending'
    db.session.commit()
    return render_template('billing.html', bills=bills)

@app.route('/create-bill', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'billing'])
def create_bill():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            bill_date = datetime.strptime(request.form.get('bill_date'), '%Y-%m-%d')
            total_amount = float(request.form.get('total_amount'))

            # Validate patient exists
            patient = Patient.query.get(patient_id)
            if not patient:
                flash('Invalid patient selected', 'error')
                return redirect(url_for('create_bill'))

            # Create bill
            bill = Bill(
                patient_id=patient_id,
                bill_date=bill_date,
                total_amount=total_amount,
                status='Pending',
                paid_amount=0.0
            )
            db.session.add(bill)
            db.session.flush()  # Get bill ID before committing

            # Create bill items
            item_types = request.form.getlist('item_type[]')
            item_ids = request.form.getlist('item_id[]')
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            total_prices = request.form.getlist('total_price[]')
            bill_item_ids = request.form.getlist('bill_item_id[]')
            
            for i in range(len(item_types)):
                if bill_item_ids[i]:  # Update existing item
                    bill_item = BillItem.query.get(int(bill_item_ids[i]))
                    bill_item.item_type = item_types[i]
                    bill_item.item_id = item_ids[i]
                    bill_item.quantity = quantities[i]
                    bill_item.description = descriptions[i]
                    bill_item.unit_price = unit_prices[i]
                    bill_item.total_price = total_prices[i]
                else:  # Add new item
                    bill_item = BillItem(
                        bill_id=bill_id,
                        item_type=item_types[i],
                        item_id=item_ids[i],
                        quantity=quantities[i],
                        description=descriptions[i],
                        unit_price=unit_prices[i],
                        total_price=total_prices[i]
                    )
                    db.session.add(bill_item)
        
            # Update bill total
            bill.total_amount = sum(float(price) for price in total_prices)
        
            try:
                db.session.commit()
                flash('Bill updated successfully', 'success')
                return redirect(url_for('billing'))
            except Exception as e:
                db.session.rollback()
                flash('Error updating bill: ' + str(e), 'error')
        except Exception as e:
                db.session.rollback()
                flash('Error updating bill: ' + str(e), 'error')
    # GET request - show edit form
    patients = Patient.query.all()
    lab_services = LabService.query.all()
    pharmacy_items = PharmacyItem.query.all()
    bill_items = BillItem.query.filter_by(bill_id=bill_id).all()
    
    return render_template('edit_bill.html', 
                         patients=patients,
                         lab_services=lab_services,
                         pharmacy_items=pharmacy_items,
                         bill=bill,
                         bill_items=bill_items)

@app.route('/view-bill/<int:bill_id>')
@login_required
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('view_bill.html', bill=bill)

@app.route('/add-payment/<int:bill_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'billing'])
def add_payment(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        payment_method = request.form.get('payment_method')
        payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d')
        reference_number = request.form.get('reference_number')

        # Create payment
        payment = Payment(
            bill_id=bill.id,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            reference_number=reference_number
        )
        db.session.add(payment)

        # Update bill
        bill.paid_amount += amount
        if bill.paid_amount >= bill.total_amount and bill.balance == 0:
            bill.status = 'Paid'
        else:
            bill.status = 'Partial'

        db.session.commit()
        flash('Payment added successfully!', 'success')
        return redirect(url_for('view_bill', bill_id=bill.id))

    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_payment.html', bill=bill, today=today)

@app.route('/edit_bill/<int:bill_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'billing'])
def edit_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        try:
            # Extract form data
            patient_id = request.form.get('patient_id')
            bill_date = request.form.get('bill_date')
            
            # Update bill details
            bill.patient_id = patient_id
            bill.bill_date = datetime.strptime(bill_date, '%Y-%m-%d')
            
            # Process bill items
            item_types = request.form.getlist('item_type[]')
            item_ids = request.form.getlist('item_id[]')
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            total_prices = request.form.getlist('total_price[]')
            bill_item_ids = request.form.getlist('bill_item_id[]')
            
            # Remove existing bill items
            BillItem.query.filter_by(bill_id=bill_id).delete()
            
            # Add new bill items
            for i in range(len(item_types)):
                bill_item = BillItem(
                    bill_id=bill_id,
                    item_type=item_types[i],
                    item_id=item_ids[i],
                    quantity=quantities[i],
                    description=descriptions[i],
                    unit_price=unit_prices[i],
                    total_price=total_prices[i]
                )
                db.session.add(bill_item)
            
            # Update bill total
            bill.total_amount = sum(float(price) for price in total_prices)
            
            db.session.commit()
            flash('Bill updated successfully', 'success')
            return redirect(url_for('billing'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating bill: {str(e)}', 'error')
            return redirect(url_for('edit_bill', bill_id=bill_id))
    
    # GET request - show edit form
    patients = Patient.query.all()
    lab_services = LabService.query.all()
    pharmacy_items = PharmacyItem.query.all()
    bill_items = BillItem.query.filter_by(bill_id=bill_id).all()
    
    return render_template('edit_bill.html', 
                         patients=patients,
                         lab_services=lab_services,
                         pharmacy_items=pharmacy_items,
                         bill=bill,
                         bill_items=bill_items)

@app.route('/fix-bill-statuses')
@login_required
@role_required(['admin', 'billing'])
def fix_bill_statuses():
    bills = Bill.query.all()
    for bill in bills:
        if bill.balance > 0:
            bill.status = 'Partial'
        elif bill.paid_amount >= bill.total_amount and bill.balance == 0:
            bill.status = 'Paid'
        else:
            bill.status = 'Pending'
    db.session.commit()
    flash('Bill statuses have been updated', 'success')
    return redirect(url_for('billing'))

@app.route('/lab-results')
@login_required
@role_required(['admin', 'lab_technician'])
def lab_results():
    # If lab technician, show only their results
    if current_user.role == 'lab_technician':
        technician = LabTechnician.query.filter_by(email=current_user.email).first()
        results = LabResult.query.filter_by(technician_id=technician.id).all()
    else:
        # Admin sees all results
        results = LabResult.query.all()
    
    return render_template('lab_results.html', results=results)

@app.route('/add-lab-result/<int:bill_item_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'lab_technician'])
def add_lab_result(bill_item_id):
    bill_item = BillItem.query.get_or_404(bill_item_id)
    
    if request.method == 'POST':
        result_value = request.form.get('result_value')
        reference_range = request.form.get('reference_range')
        status = request.form.get('status')
        performed_by = request.form.get('performed_by')
        performed_at = request.form.get('performed_at')
        remarks = request.form.get('remarks')
        
        # Create lab result
        lab_result = LabResult(
            bill_item_id=bill_item.id,
            result_value=result_value,
            reference_range=reference_range,
            status=status,
            performed_by=performed_by,
            performed_at=datetime.strptime(performed_at, '%Y-%m-%dT%H:%M') if performed_at else None,
            remarks=remarks
        )
        
        db.session.add(lab_result)
        db.session.commit()
        
        flash('Lab result added successfully!', 'success')
        return redirect(url_for('lab_results'))
    
    return render_template('add_lab_result.html', bill_item=bill_item, lab_result=None)

@app.route('/edit-lab-result/<int:result_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'lab_technician'])
def edit_lab_result(result_id):
    lab_result = LabResult.query.get_or_404(result_id)
    bill_item = lab_result.bill_item
    
    if request.method == 'POST':
        lab_result.result_value = request.form.get('result_value')
        lab_result.reference_range = request.form.get('reference_range')
        lab_result.status = request.form.get('status')
        lab_result.performed_by = request.form.get('performed_by')
        performed_at = request.form.get('performed_at')
        lab_result.performed_at = datetime.strptime(performed_at, '%Y-%m-%dT%H:%M') if performed_at else None
        lab_result.remarks = request.form.get('remarks')
        
        db.session.commit()
        flash('Lab result updated successfully!', 'success')
        return redirect(url_for('lab_results'))
    
    return render_template('add_lab_result.html', bill_item=bill_item, lab_result=lab_result)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect to appropriate dashboard based on role
        if current_user.role == 'admin':
            return redirect(url_for('index'))
        elif current_user.role == 'doctor':
            return redirect(url_for('patient'))
        elif current_user.role == 'lab_technician':
            return redirect(url_for('lab_results'))  # Create this route
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            
            # Redirect to appropriate dashboard based on role
            if user.role == 'admin':
                return redirect(url_for('index'))
            elif user.role == 'doctor':
                return redirect(url_for('patient'))
            elif user.role == 'lab_technician':
                return redirect(url_for('lab_results'))  # Create this route
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/lab-technicians')
@login_required
@role_required(['admin'])
def lab_technicians():
    technicians = LabTechnician.query.all()
    return render_template('lab_technicians.html', technicians=technicians)

@app.route('/add-lab-technician', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_lab_technician():
    if request.method == 'POST':
        try:
            # Extract form data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            password = request.form.get('password')
            specialization = request.form.get('specialization')

            # Create new lab technician
            new_technician = LabTechnician(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                password=generate_password_hash(password),
                specialization=specialization,
                status=True
            )

            # Create corresponding user account
            new_user = User(
                username=f"{first_name.lower()}.{last_name.lower()}",
                email=email,
                role='lab_technician'
            )
            new_user.password_hash = generate_password_hash(password)

            # Add both to session
            db.session.add(new_technician)
            db.session.add(new_user)
            
            db.session.commit()
            
            flash('Lab Technician added successfully!', 'success')
            return redirect(url_for('lab_technicians'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding lab technician: {str(e)}', 'error')
    
    return render_template('add_lab_technician.html')

@app.route('/edit-lab-technician/<int:technician_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_lab_technician(technician_id):
    technician = LabTechnician.query.get_or_404(technician_id)
    
    if request.method == 'POST':
        try:
            # Update technician details
            technician.first_name = request.form.get('first_name')
            technician.last_name = request.form.get('last_name')
            technician.email = request.form.get('email')
            technician.phone = request.form.get('phone')
            technician.specialization = request.form.get('specialization')
            
            # Update password if provided
            new_password = request.form.get('password')
            if new_password:
                technician.password = generate_password_hash(new_password)
                
                # Update corresponding user account
                user = User.query.filter_by(email=technician.email).first()
                if user:
                    user.password_hash = generate_password_hash(new_password)
            
            db.session.commit()
            
            flash('Lab Technician updated successfully!', 'success')
            return redirect(url_for('lab_technicians'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating lab technician: {str(e)}', 'error')
    
    return render_template('edit_lab_technician.html', technician=technician)

@app.route('/delete-lab-technician/<int:technician_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_lab_technician(technician_id):
    technician = LabTechnician.query.get_or_404(technician_id)
    
    try:
        # Delete corresponding user account
        user = User.query.filter_by(email=technician.email).first()
        if user:
            db.session.delete(user)
        
        # Delete lab technician
        db.session.delete(technician)
        db.session.commit()
        
        flash('Lab Technician deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting lab technician: {str(e)}', 'error')
    
    return redirect(url_for('lab_technicians'))

if __name__ == '__main__':
    app.run(debug=True)
