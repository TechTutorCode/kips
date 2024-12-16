from flask import Flask, request, jsonify, render_template, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:#Deno0707@204.12.205.217:5432/kips"
# app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///kips.db"
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
from models.lab_service_requests import LabServiceRequest
from models.medicine_requests import MedicineRequest

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
    
    # Check and create default users if they don't exist
    def create_default_users():
        # Define default users
        default_users = [
            {
                'email': 'admin@kips.com',
                'password': 'admin123',
                'role': 'admin'
            },
            {
                'email': 'doctor@kips.com',
                'password': 'doctor123',
                'role': 'doctor'
            },
            {
                'email': 'billing@kips.com',
                'password': 'billing123',
                'role': 'billing'
            }
            ,
            {
                'email': 'pharmacist@kips.com',
                'password': 'pharmacist123',
                'role': 'pharmacist'
            }
        ]
        
        # Check and create users
        for user_data in default_users:
            existing_user = User.query.filter_by(email=user_data['email']).first()
            if not existing_user:
                # Create new user
                new_user = User(
                    email=user_data['email'],
                    role=user_data['role'],
                    password=user_data['password']
                )
                
                # Add and commit
                db.session.add(new_user)
                print(f"Created default user: {user_data['email']}")
        
        # Commit all changes
        db.session.commit()
    
    # Run user creation
    create_default_users()

@app.route("/")
@login_required
def index():
    # Get today's date range
    today = datetime.utcnow().date()  # Use current date
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get today's appointments
    todays_appointments = PatientRecord.query.filter(
        PatientRecord.next_visit.between(today_start, today_end)
    ).order_by(PatientRecord.next_visit).all()
    appointment_count = len(todays_appointments)
    print(f"Today's Appointments: {appointment_count}")
    
    # Get pending payments (total balance from unpaid bills)
    from sqlalchemy import func

    # Detailed query with logging
    print("Pending Bills Query Debug:")
    
    # Count of bills with different statuses
    status_counts = db.session.query(
        Bill.status, 
        func.count(Bill.id).label('count'), 
        func.sum(Bill.total_amount).label('total_amount'),
        func.sum(Bill.paid_amount).label('paid_amount')
    ).group_by(Bill.status).all()
    
    print("Bill Status Breakdown:")
    for status, count, total_amount, paid_amount in status_counts:
        print(f"Status: {status}")
        print(f"  Count: {count}")
        print(f"  Total Amount: {total_amount}")
        print(f"  Paid Amount: {paid_amount}")
        print("---")
    
    # Explicitly calculate pending payments
    pending_bills = Bill.query.filter(Bill.status.in_(['Unpaid', 'Partial'])).all()
  
    print("\nDetailed Pending Bills:")
    pending_payments = 0.0
    for bill in pending_bills:
        print("hello")
        balance = bill.total_amount - bill.paid_amount
        pending_payments += balance
        
        print(f"Bill ID: {bill.id}")
        print(f"  Patient: {bill.patient.first_name} {bill.patient.last_name}")
        print(f"  Total Amount: {bill.total_amount}")
        print(f"  Paid Amount: {bill.paid_amount}")
        print(f"  Status: {bill.status}")
        print(f"  Balance: {balance}")
    
    print(f"\nPending Payments Total: {pending_payments}")
    
    # Get low stock items
    low_stock_items = PharmacyItem.query.filter(
        PharmacyItem.quantity <= PharmacyItem.reorder_level
    ).all()
    low_stock_count = len(low_stock_items)
    print(f"Low Stock Items: {low_stock_count}")
    
    # Calculate today's revenue from payments and bills
    today_revenue_query = db.session.query(
        func.coalesce(func.sum(Bill.total_amount), 0.0).label('bill_total'),
        func.coalesce(func.sum(Payment.amount), 0.0).label('payment_total')
    ).outerjoin(Payment, Bill.id == Payment.bill_id).filter(
        Bill.bill_date.between(today_start, today_end)
    ).first()

    today_revenue = today_revenue_query.bill_total + today_revenue_query.payment_total
    print(f"Today's Revenue Breakdown:")
    print(f"  Bills Total: {today_revenue_query.bill_total}")
    print(f"  Payments Total: {today_revenue_query.payment_total}")
    print(f"  Total Revenue: {today_revenue}")
    
    # Optional: Separate revenue sources for more detailed tracking
    bill_revenue = today_revenue_query.bill_total
    payment_revenue = today_revenue_query.payment_total
    
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

@app.route("/doctors")
@login_required
@role_required(['admin', 'doctor'])
def doctors():
    doctors = Doctor.query.all()
    print(doctors)
    return render_template('doctors.html', doctors=doctors)

@app.route('/add-doctor', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_doctor():
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            password = request.form.get('password')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            
            # Check if doctor already exists
            existing_doctor = Doctor.query.filter_by(email=email).first()
            if existing_doctor:
                flash('A doctor with this email already exists.', 'error')
                return redirect(url_for('add_doctor'))
            
            # Hash the password
            hashed_password = generate_password_hash(password)
            
            # Create new doctor
            new_doctor = Doctor(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=hashed_password,
                gender=gender,
                phone=phone,
                status=True
            )
            db.session.add(new_doctor)
            db.session.flush()  # This will populate the id
            
            # Create corresponding user account
            from models.users import User
            new_user = User(
                email=email,
                role='doctor',
                password=password,
                doctor_id=new_doctor.id
            )
            db.session.add(new_user)
            
            db.session.commit()
            
            flash('Doctor added successfully!', 'success')
            return redirect(url_for('doctors'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding doctor: {str(e)}', 'error')
            return redirect(url_for('add_doctor'))
    
    return render_template('add_doctor.html')

@app.route('/patients')
@login_required
@role_required(['admin', 'doctor'])
def patient():
     patients = Patient.query.all()
     return render_template('patients.html', patients=patients)

@app.route('/add-patient',  methods=['POST','GET'])
@login_required
@role_required(['admin', 'doctor'])
def add_p():
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            gender = request.form.get('gender')
            dob = request.form.get('dob')
            address = request.form.get('address')
            
            # Convert dob to datetime
            dob = datetime.strptime(dob, '%Y-%m-%d') if dob else None
            
            # Create new patient
            new_patient = Patient(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                gender=gender,
                dob=dob,
                address=address
            )
            
            db.session.add(new_patient)
            db.session.commit()
            
            flash('Patient added successfully!', 'success')
            return redirect(url_for('patient'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {str(e)}', 'danger')
            return redirect(url_for('add_p'))
    
    return render_template('add_patient.html')

@app.route('/edit-patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'doctor'])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        try:
            patient.first_name = request.form.get('first_name')
            patient.last_name = request.form.get('last_name')
            patient.email = request.form.get('email')
            patient.phone = request.form.get('phone')
            patient.gender = request.form.get('gender')
            patient.address = request.form.get('address')
            
            # Convert dob to datetime
            dob_str = request.form.get('dob')
            patient.dob = datetime.strptime(dob_str, '%Y-%m-%d') if dob_str else None
            
            db.session.commit()
            flash('Patient updated successfully!', 'success')
            return redirect(url_for('patient'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating patient: {str(e)}', 'danger')
            return redirect(url_for('edit_patient', patient_id=patient_id))
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/delete-patient', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_patient():
    patient_id = request.form.get('patient_id')
    patient = Patient.query.get_or_404(patient_id)
    
    try:
        db.session.delete(patient)
        db.session.commit()
        flash('Patient deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting patient: {str(e)}', 'danger')
    
    return redirect(url_for('patient'))

@app.route('/patient-records/<int:patient_id>')
@login_required
@role_required(['admin', 'doctor'])
def patient_records(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = PatientRecord.query.filter_by(patient_id=patient_id).order_by(PatientRecord.created_at.desc()).all()
    
    # Fetch lab results directly for the patient
    completed_lab_results = LabResult.query.filter(
        LabResult.patient_id == patient_id,
        LabResult.status == 'Completed'
    ).all()
    
    # Debugging and logging
    print(f"Total Completed Lab Results for Patient {patient_id}: {len(completed_lab_results)}")
    for lab_result in completed_lab_results:
        print(f"Lab Result ID: {lab_result.id}")
        print(f"Result Value: {lab_result.result_value}")
        print(f"Reference Range: {lab_result.reference_range}")
        print("---")
    # Fetch medicine requests
    medicine_requests = MedicineRequest.query.filter_by(patient_id=patient_id).order_by(MedicineRequest.created_at.desc()).all()
    return render_template('patient_records.html', 
                         patient=patient, 
                         records=records,
                         lab_results=completed_lab_results,
                         medicine_requests=medicine_requests)

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
        flash('Patient record added successfully!', 'success')
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
        flash('Patient record updated successfully!', 'success')
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
    
    # Ensure diagnosis is a string or empty string
    for record in appointments:
        if record.diagnosis is None:
            record.diagnosis = ''
    
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
@role_required(['admin', 'pharmacist'])
def add_pharmacy_item():
    if request.method == 'POST':
        try:
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
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding pharmacy item: {str(e)}', 'error')
            return redirect(url_for('add_pharmacy_item'))
    
    return render_template('add_pharmacy_item.html')

@app.route('/edit-pharmacy-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_pharmacy_item(item_id):
    item = PharmacyItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        try:
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
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating pharmacy item: {str(e)}', 'error')
            return redirect(url_for('edit_pharmacy_item', item_id=item_id))
    
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
    
    # Separate bills into completed and pending
    completed_bills = [bill for bill in bills if bill.status == 'Paid']
    pending_bills = [bill for bill in bills if bill.status in ['Pending', 'Partial']]
    
    return render_template('billing.html', completed_bills=completed_bills, pending_bills=pending_bills)

@app.route('/create-bill', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'billing', 'pharmacist'])
def create_bill():
    if request.method == 'POST':
        try:
            # Validate patient_id
            patient_id = request.form.get('patient_id')
            if not patient_id:
                raise ValueError("Patient ID is required")
            
            patient = Patient.query.get(patient_id)
            if not patient:
                raise ValueError("Invalid patient selected")
            
            # Validate bill date
            bill_date = request.form.get('bill_date')
            if not bill_date:
                raise ValueError("Bill date is required")
            
            try:
                bill_date = datetime.strptime(bill_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
            
            # Process bill items
            item_types = request.form.getlist('item_type[]')
            item_ids = request.form.getlist('item_id[]')
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            total_prices = request.form.getlist('total_price[]')
            
            # Debug print to see exact form data
            print("Form Data Debug:")
            print(f"Item Types: {item_types}")
            print(f"Item IDs: {item_ids}")
            print(f"Descriptions: {descriptions}")
            print(f"Quantities: {quantities}")
            print(f"Unit Prices: {unit_prices}")
            print(f"Total Prices: {total_prices}")
            
            # Validate bill items
            if not item_types or len(item_types) == 0:
                raise ValueError("At least one bill item is required")
            
            # Create new bill
            bill = Bill(
                patient_id=patient_id,
                bill_date=bill_date,
                status='Unpaid',
                total_amount=0.0,
                paid_amount=0.0
            )
            db.session.add(bill)
            db.session.flush()  # Get bill ID before adding bill items
            
            # Add new bill items with type conversion and validation
            total_bill_amount = 0.0
            for i in range(len(item_types)):
                try:
                    quantity = float(quantities[i])
                    unit_price = float(unit_prices[i])
                    total_price = float(total_prices[i])
                except ValueError:
                    raise ValueError(f"Invalid numeric value in bill item {i+1}")
                
                if quantity <= 0 or unit_price < 0:
                    raise ValueError(f"Invalid quantity or price in bill item {i+1}")
                
                # Validate item type and item_id
                if item_types[i] not in ['Lab Service', 'Pharmacy', 'Consultation']:
                    raise ValueError(f"Invalid item type in bill item {i+1}")
                
                if item_types[i] == 'Lab Service':
                    item = LabService.query.get(item_ids[i])
                elif item_types[i] == 'Pharmacy':
                    item = PharmacyItem.query.get(item_ids[i])
                    
                    # Check and reduce pharmacy item quantity
                    if item:
                        if item.quantity < quantity:
                            raise ValueError(f"Insufficient stock for {item.name}. Available: {item.quantity}")
                        
                        # Reduce pharmacy item quantity
                        item.quantity -= quantity
                        print(f"Reduced {item.name} stock by {quantity}. Remaining: {item.quantity}")
                    else:
                        raise ValueError(f"Invalid pharmacy item in bill item {i+1}")
                else:  # Consultation
                    item = True  # Consultation is a special case
                
                bill_item = BillItem(
                    bill_id=bill.id,
                    item_type=item_types[i],
                    item_id=item_ids[i] if item_types[i] != 'Consultation' else None,
                    quantity=quantity,
                    description=descriptions[i],
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.session.add(bill_item)
                total_bill_amount += total_price
            
            # Update bill total
            bill.total_amount = total_bill_amount
            
            db.session.commit()
            flash('Bill created successfully', 'success')
            return redirect(url_for('billing'))
        
        except Exception as e:
            db.session.rollback()
            print(f"Error in create_bill: {str(e)}")  # Add detailed logging
            flash(str(e), 'error')
            return redirect(url_for('create_bill'))
    
    # GET request - show create bill form
    patients = Patient.query.all()
    lab_services = LabService.query.all()
    pharmacy_items = PharmacyItem.query.all()
    
    return render_template('create_bill.html', 
                         patients=patients,
                         lab_services=lab_services,
                         pharmacy_items=pharmacy_items)

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
@role_required(['admin', 'billing', 'pharmacist'])
def edit_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        try:
            # Validate patient_id
            patient_id = request.form.get('patient_id')
            if not patient_id:
                raise ValueError("Patient ID is required")
            
            patient = Patient.query.get(patient_id)
            if not patient:
                raise ValueError("Invalid patient selected")
            
            # Validate bill date
            bill_date = request.form.get('bill_date')
            if not bill_date:
                raise ValueError("Bill date is required")
            
            try:
                bill.bill_date = datetime.strptime(bill_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
            
            bill.patient_id = patient_id
            
            # Process bill items
            item_types = request.form.getlist('item_type[]')
            item_ids = request.form.getlist('item_id[]')
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            total_prices = request.form.getlist('total_price[]')
            
            # Debug print to see exact form data
            print("Form Data Debug:")
            print(f"Item Types: {item_types}")
            print(f"Item IDs: {item_ids}")
            print(f"Descriptions: {descriptions}")
            print(f"Quantities: {quantities}")
            print(f"Unit Prices: {unit_prices}")
            print(f"Total Prices: {total_prices}")
            
            # Validate bill items
            if not item_types or len(item_types) == 0:
                raise ValueError("At least one bill item is required")
            
            # Remove existing bill items
            BillItem.query.filter_by(bill_id=bill_id).delete()
            
            # Add new bill items with type conversion and validation
            total_bill_amount = 0.0
            for i in range(len(item_types)):
                try:
                    quantity = float(quantities[i])
                    unit_price = float(unit_prices[i])
                    total_price = float(total_prices[i])
                except ValueError:
                    raise ValueError(f"Invalid numeric value in bill item {i+1}")
                
                if quantity <= 0 or unit_price < 0:
                    raise ValueError(f"Invalid quantity or price in bill item {i+1}")
                
                # Validate item type and item_id
                if item_types[i] not in ['Lab Service', 'Pharmacy', 'Consultation']:
                    raise ValueError(f"Invalid item type in bill item {i+1}")
                
                if item_types[i] == 'Lab Service':
                    item = LabService.query.get(item_ids[i])
                elif item_types[i] == 'Pharmacy':
                    item = PharmacyItem.query.get(item_ids[i])
                    
                    # Check and reduce pharmacy item quantity
                    if item:
                        if item.quantity < quantity:
                            raise ValueError(f"Insufficient stock for {item.name}. Available: {item.quantity}")
                        
                        # Reduce pharmacy item quantity
                        item.quantity -= quantity
                        print(f"Reduced {item.name} stock by {quantity}. Remaining: {item.quantity}")
                    else:
                        raise ValueError(f"Invalid pharmacy item in bill item {i+1}")
                else:  # Consultation
                    item = True  # Consultation is a special case
                
                bill_item = BillItem(
                    bill_id=bill_id,
                    item_type=item_types[i],
                    item_id=item_ids[i] if item_types[i] != 'Consultation' else None,
                    quantity=quantity,
                    description=descriptions[i],
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.session.add(bill_item)
                total_bill_amount += total_price
            
            # Update bill total
            bill.total_amount = total_bill_amount
            
            # Recalculate bill status
            bill.status = 'Unpaid' if bill.total_amount > bill.paid_amount else 'Paid'
            
            db.session.commit()
            flash('Bill updated successfully', 'success')
            return redirect(url_for('billing'))
        
        except Exception as e:
            db.session.rollback()
            print(f"Error in edit_bill: {str(e)}")  # Add detailed logging
            flash(str(e), 'error')
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
@role_required(['lab_technician'])
def add_lab_result(bill_item_id):
    bill_item = BillItem.query.get_or_404(bill_item_id)
    
    # Find the associated lab service request
    lab_service_request = LabServiceRequest.query.filter_by(bill_id=bill_item.bill_id).first()
    
    if not lab_service_request:
        flash('No associated lab service request found.', 'danger')
        return redirect(url_for('pending_lab_service_requests'))
    
    # Ensure the lab technician can only add results for their own service
    if request.method == 'POST':
        try:
            # Find the current logged-in lab technician by email
            current_lab_tech = LabTechnician.query.filter_by(email=current_user.email).first()
            
            if not current_lab_tech:
                flash('Lab technician profile not found.', 'danger')
                return redirect(url_for('pending_lab_service_requests'))
            
            # Create new lab result
            new_lab_result = LabResult(
                patient_id=bill_item.bill.patient_id,  # Add patient_id
                bill_item_id=bill_item_id,
                technician_id=current_lab_tech.id,
                result_value=request.form.get('result_value', ''),
                reference_range=request.form.get('reference_range', ''),
                remarks=request.form.get('remarks', ''),
                status='Completed',
                performed_at=datetime.utcnow()
            )
            
            db.session.add(new_lab_result)
            db.session.commit()
            
            flash('Lab result added successfully!', 'success')
            return redirect(url_for('lab_results'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding lab result: {str(e)}', 'danger')
            print(f"Full Error: {e}")
    
    # Get the lab service details for the bill item
    lab_service = lab_service_request.lab_service
    patient = bill_item.bill.patient
    
    return render_template('add_lab_result.html', 
                           bill_item=bill_item, 
                           lab_service=lab_service, 
                           patient=patient)

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
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Get email and password from form
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
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

@app.route('/request-lab-service', methods=['GET', 'POST'])
@login_required
@role_required(['doctor'])
def request_lab_service():
    if request.method == 'GET':
        # Get list of patients and lab services for the form
        patients = Patient.query.all()
        lab_services = LabService.query.all()
        return render_template('request_lab_service.html', 
                               patients=patients, 
                               lab_services=lab_services)
    
    if request.method == 'POST':
        try:
            # Get form data
            patient_id = request.form.get('patient_id')
            lab_service_id = request.form.get('lab_service_id')
            clinical_notes = request.form.get('clinical_notes')
            urgency = request.form.get('urgency', 'Normal')
            
            # Validate inputs
            if not patient_id or not lab_service_id:
                flash('Patient and Lab Service are required.', 'error')
                return redirect(url_for('request_lab_service'))
            
            # Create lab service request
            new_request = LabServiceRequest(
                doctor_id=current_user.doctor.id,  # Assuming current user is a doctor
                patient_id=patient_id,
                lab_service_id=lab_service_id,
                clinical_notes=clinical_notes,
                urgency=urgency,
                status='Pending'
            )
            
            db.session.add(new_request)
            db.session.commit()
            
            flash('Lab service request submitted successfully!', 'success')
            return redirect(url_for('request_lab_service'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting lab service request: {str(e)}', 'error')
            return redirect(url_for('request_lab_service'))

@app.route('/lab-service-requests', methods=['GET'])
@login_required
@role_required(['doctor', 'admin', 'lab_technician'])
def view_lab_service_requests():
    # Filter requests based on user role
    if current_user.role == 'doctor':
        requests = LabServiceRequest.query.filter_by(doctor_id=current_user.doctor.id).all()
    elif current_user.role == 'lab_technician':
        requests = LabServiceRequest.query.filter_by(status='Pending').all()
    else:  # admin
        requests = LabServiceRequest.query.all()
    
    return render_template('lab_service_requests.html', requests=requests)

@app.route('/process-lab-service-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@role_required(['lab_technician'])
def process_lab_service_request(request_id):
    # Find the lab service request
    lab_service_request = LabServiceRequest.query.get_or_404(request_id)
    
    if request.method == 'GET':
        # Show processing form
        return render_template('process_lab_service_request.html', request=lab_service_request)
    
    if request.method == 'POST':
        try:
            # Get form data
            action = request.form.get('action')
            notes = request.form.get('notes')
            
            # Update request status
            if action == 'approve':
                # Create bill for the lab service
                # Find the lab service
                lab_service = LabService.query.get(lab_service_request.lab_service_id)
                
                # Find the current user's lab technician ID (if exists)
                current_lab_technician = None
                if current_user.role == 'lab_technician':
                    current_lab_technician = LabTechnician.query.filter_by(email=current_user.email).first()
                
                # Create bill first
                bill = Bill(
                    patient_id=lab_service_request.patient_id,
                    total_amount=lab_service.cost,
                    status='Unpaid'
                )
                db.session.add(bill)
                db.session.flush()  # This will populate the bill.id
                
                # Create bill item
                bill_item = BillItem(
                    bill_id=bill.id,  # Use the bill's ID
                    item_type='Lab Service',
                    item_id=lab_service.id,
                    description=lab_service.name,
                    unit_price=lab_service.cost,
                    total_price=lab_service.cost,
                    quantity=1
                )
                db.session.add(bill_item)
                db.session.flush()  # Ensure bill_item has an ID
                
                # Add bill items to the bill
                bill.bill_items = [bill_item]
                
                # Create lab result entry
                lab_result = LabResult(
                    patient_id=lab_service_request.patient_id,  # Add patient_id
                    bill_item_id=bill_item.id,
                    technician_id=current_lab_technician.id if current_lab_technician else None,
                    result_value='Pending',
                    reference_range=None,  # Add reference range
                    status='Pending',
                    remarks=notes or 'Lab service request approved',
                    performed_at=datetime.utcnow()
                )
                db.session.add(lab_result)
                
                # Update lab service request status and link bill
                lab_service_request.status = 'Approved'
                lab_service_request.bill_id = bill.id
                
                # Commit all changes
                db.session.commit()
                
                flash('Lab service request approved. Bill created and lab result prepared.', 'success')
            elif action == 'reject':
                lab_service_request.status = 'Rejected'
                
                # Add notes for rejection
                if notes:
                    lab_service_request.clinical_notes = (lab_service_request.clinical_notes or '') + f"\n\nRejection Notes: {notes}"
                
                db.session.commit()
                flash('Lab service request rejected.', 'warning')
            
            return redirect(url_for('view_lab_service_requests'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing lab service request: {str(e)}', 'error')
            return redirect(url_for('process_lab_service_request', request_id=request_id))

@app.route('/view_lab_result/<int:result_id>', methods=['GET'])
@login_required
def view_lab_result(result_id):
    # Check user permissions
    if current_user.role not in ['admin', 'doctor', 'lab_technician']:
        flash('You do not have permission to view lab results.', 'danger')
        return redirect(url_for('index'))
    
    # Find the lab result
    lab_result = LabResult.query.get_or_404(result_id)
    
    # If user is a doctor, ensure they are associated with the patient
    if current_user.role == 'doctor':
        # Find the doctor by email
        doctor = Doctor.query.filter_by(email=current_user.email).first()
        
        # Validate doctor exists
        if not doctor:
            flash('Doctor profile not found.', 'danger')
            return redirect(url_for('index'))
    
    return render_template('view_lab_result.html', result=lab_result)

@app.route('/pending-lab-service-requests', methods=['GET'])
@login_required
@role_required(['lab_technician'])
def pending_lab_service_requests():
    # Find approved lab service requests that need lab results
    pending_requests = LabServiceRequest.query.filter(
        LabServiceRequest.status == 'Approved',
        LabServiceRequest.bill_id.isnot(None)
    ).all()
    
    # Filter out requests that already have completed lab results
    filtered_requests = []
    for request in pending_requests:
        # Check if the bill associated with this request has any bill items
        bill = Bill.query.get(request.bill_id)
        if bill and bill.items:
            # Check if any bill item has a completed lab result
            has_completed_result = False
            for item in bill.items:
                # Check if the bill item has a lab result
                lab_result = LabResult.query.filter_by(bill_item_id=item.id).first()
                if lab_result and lab_result.status == 'Completed':
                    has_completed_result = True
                    break
            
            if not has_completed_result:
                filtered_requests.append(request)
    
    return render_template('pending_lab_service_requests.html', requests=filtered_requests)

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
        return redirect(url_for('doctors'))
        
    return render_template('edit_doctor.html', doctor=doctor)

@app.route('/patient-bills/<int:patient_id>')
@login_required
@role_required(['admin', 'doctor', 'billing'])
def patient_bills(patient_id):
    # Get the patient
    patient = Patient.query.get_or_404(patient_id)
    
    # Get all bills for this patient
    all_bills = Bill.query.filter_by(patient_id=patient_id).order_by(Bill.bill_date.desc()).all()
    
    # Separate completed and ongoing bills
    completed_bills = [bill for bill in all_bills if bill.status == 'Paid']
    ongoing_bills = [bill for bill in all_bills if bill.status in ['Unpaid', 'Partial']]
    
    return render_template('patient_bills.html', 
                         patient=patient, 
                         completed_bills=completed_bills,
                         ongoing_bills=ongoing_bills)

@app.route('/request-medicine/<int:patient_id>', methods=['POST'])
@login_required
def request_medicine(patient_id):
    # Ensure only doctors can request medicine
    if not current_user.doctor:
        return jsonify({"error": "Unauthorized: Only doctors can request medicine"}), 403
    
    # Validate patient exists
    patient = Patient.query.get_or_404(patient_id)
    
    # Get form data
    medicine_name = request.form.get('medicine_name')
    dosage = request.form.get('dosage')
    frequency = request.form.get('frequency')
    duration = request.form.get('duration')
    notes = request.form.get('notes')
    
    # Validate required fields
    if not all([medicine_name, dosage, frequency]):
        return jsonify({"error": "Missing required medicine request fields"}), 400
    
    try:
        # Create medicine request
        medicine_request = MedicineRequest(
            doctor_id=current_user.id,
            patient_id=patient_id,
            medicine_name=medicine_name,
            dosage=dosage,
            frequency=frequency,
            duration=duration,
            notes=notes,
            status='Pending'
        )
        
        db.session.add(medicine_request)
        db.session.commit()
        
        return jsonify({
            "message": "Medicine request submitted successfully",
            "request_id": medicine_request.id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/update-medicine-request', methods=['POST'])
@login_required
def update_medicine_request():
    # Ensure only doctors can update medicine requests
    if not current_user.doctor:
        return jsonify({"error": "Unauthorized: Only doctors can update medicine requests"}), 403
    
    # Get form data
    request_id = request.form.get('request_id')
    medicine_name = request.form.get('medicine_name')
    dosage = request.form.get('dosage')
    frequency = request.form.get('frequency')
    duration = request.form.get('duration')
    notes = request.form.get('notes')
    
    # Validate required fields
    if not all([request_id, medicine_name, dosage, frequency]):
        return jsonify({"error": "Missing required medicine request fields"}), 400
    
    try:
        # Find existing medicine request
        medicine_request = MedicineRequest.query.get_or_404(request_id)
        
        # Update medicine request
        medicine_request.medicine_name = medicine_name
        medicine_request.dosage = dosage
        medicine_request.frequency = frequency
        medicine_request.duration = duration or None
        medicine_request.notes = notes or None
        
        db.session.commit()
        
        return jsonify({
            "message": "Medicine request updated successfully",
            "request_id": medicine_request.id
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/delete-medicine-request/<int:request_id>', methods=['POST'])
@login_required
def delete_medicine_request(request_id):
    try:
        medicine_request = MedicineRequest.query.get_or_404(request_id)
        
        db.session.delete(medicine_request)
        db.session.commit()
        
        return jsonify({'message': 'Medicine request deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route("/medicine-requests")
@login_required
@role_required(['pharmacist', 'admin'])
def view_medicine_requests():
    """
    View all medicine requests for pharmacists
    """
    # Get all medicine requests, ordered by most recent first
    medicine_requests = MedicineRequest.query.order_by(MedicineRequest.created_at.desc()).all()
    
    return render_template('medicine_requests.html', 
                           medicine_requests=medicine_requests, 
                           title='Medicine Requests')

@app.route("/patient-medicine-history/<int:patient_id>")
@login_required
@role_required(['pharmacist', 'admin', 'doctor'])
def view_patient_medicine_history(patient_id):
    """
    View medicine request history for a specific patient
    """
    # Get patient details
    patient = Patient.query.get_or_404(patient_id)
    
    # Get all medicine requests for this patient, ordered by most recent first
    medicine_requests = MedicineRequest.query.filter_by(patient_id=patient_id)\
        .order_by(MedicineRequest.created_at.desc()).all()
    
    return render_template('patient_medicine_history.html', 
                           patient=patient, 
                           medicine_requests=medicine_requests, 
                           title=f'Medicine History for {patient.first_name} {patient.last_name}')

@app.route('/update-medicine-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@role_required(['pharmacist', 'admin', 'doctor'])
def update_medicine_request_status(request_id):
    """
    Update the status of a medicine request
    """
    # Fetch the specific medicine request
    medicine_request = MedicineRequest.query.get_or_404(request_id)
    
    if request.method == 'POST':
        try:
            # Get the new status from the form
            new_status = request.form.get('status')
            
            # Validate status
            valid_statuses = ['Pending', 'Provided', 'Sent to Buy']
            if new_status not in valid_statuses:
                flash('Invalid status selected.', 'error')
                return redirect(url_for('view_medicine_requests'))
            
            # Update the status
            medicine_request.status = new_status
            
            # Commit changes
            db.session.commit()
            
            # Success message
            flash(f'Medicine request status updated to {new_status}.', 'success')
            
            return redirect(url_for('view_medicine_requests'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating medicine request: {str(e)}', 'error')
            return redirect(url_for('view_medicine_requests'))
    
    # GET request: show update form
    return render_template('update_medicine_request.html', 
                           medicine_request=medicine_request, 
                           title='Update Medicine Request Status')

if __name__ == '__main__':
    app.run(debug=True)
