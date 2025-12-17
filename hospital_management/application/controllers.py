from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import db, Patient, Doctor, Admin, Department, Appointment, Treatment, DoctorAvailability
from functools import wraps
from datetime import datetime

# --- Blueprint Definitions ---
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)
doctor_bp = Blueprint('doctor', __name__)
patient_bp = Blueprint('patient', __name__)

# --- Helper: Role-Based Login Required ---
def login_required(role="any"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in.", "danger")
                return redirect(url_for('auth.login'))
            if role != "any" and session.get('role') != role:
                flash("Access denied.", "danger")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =====================================================
# AUTH ROUTES
# =====================================================

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 1. Check Admin
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['user_id'] = admin.id
            session['role'] = 'admin'
            return redirect(url_for('admin.dashboard'))
            
        # 2. Check Doctor
        doctor = Doctor.query.filter_by(username=username).first()
        if doctor and doctor.check_password(password):
            session['user_id'] = doctor.id
            session['role'] = 'doctor'
            return redirect(url_for('doctor.dashboard'))

        # 3. Check Patient
        patient = Patient.query.filter_by(username=username).first()
        if patient and patient.check_password(password):
            session['user_id'] = patient.id
            session['role'] = 'patient'
            return redirect(url_for('patient.dashboard'))
            
        flash('Invalid credentials.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear() 
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if Patient.query.filter_by(username=username).first() or \
           Doctor.query.filter_by(username=username).first() or \
           Admin.query.filter_by(username=username).first():
            flash('Username taken.', 'danger')
            return redirect(url_for('auth.register'))

        try:
            new_patient = Patient(username=username)
            new_patient.set_password(password)
            db.session.add(new_patient)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            db.session.rollback() 
            flash('Error creating account.', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')


# =====================================================
# ADMIN ROUTES
# =====================================================

@admin_bp.route('/dashboard', methods=['GET'])
@login_required(role="admin")
def dashboard():
    search_query = request.args.get('search_query')
    
    doctors_query = Doctor.query
    patients_query = Patient.query
    appointments_query = Appointment.query.order_by(Appointment.appointment_date.asc())
    
    if search_query:
        doctors_query = doctors_query.join(Department).filter(
            (Doctor.full_name.ilike(f'%{search_query}%')) | 
            (Department.name.ilike(f'%{search_query}%'))
        )
        patients_query = patients_query.filter(
            (Patient.username.ilike(f'%{search_query}%')) |
            (Patient.full_name.ilike(f'%{search_query}%'))
        )

    return render_template('admin_dashboard.html', 
                           doctor_count=len(doctors_query.all()), 
                           patient_count=len(patients_query.all()), 
                           appointments=appointments_query.all(),
                           doctors=doctors_query.all(),
                           patients=patients_query.all())

@admin_bp.route('/create_doctor', methods=['GET', 'POST'])
@login_required(role="admin")
def create_doctor():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        specialization = request.form.get('specialization')
        experience = request.form.get('experience')
        username = fullname.lower().replace(" ", ".")
        
        if Doctor.query.filter_by(username=username).first():
            flash(f'Error: Doctor with username "{username}" already exists.', 'danger')
            return redirect(url_for('admin.create_doctor'))

        try:
            dept = Department.query.filter_by(name=specialization).first()
            if not dept:
                dept = Department(name=specialization)
                db.session.add(dept)
                db.session.commit()

            new_doctor = Doctor(
                username=username, full_name=fullname,
                department_id=dept.id, experience_years=experience
            )
            new_doctor.set_password('doctor123') 
            db.session.add(new_doctor)
            db.session.commit()
            
            flash(f'Doctor {fullname} added! (Login: {username} / doctor123)', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception:
            db.session.rollback()
            flash('Database error.', 'danger')
            return redirect(url_for('admin.create_doctor'))

    return render_template('a_create.html')

@admin_bp.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
@login_required(role="admin")
def edit_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    if request.method == 'POST':
        doctor.full_name = request.form.get('fullname')
        doctor.experience_years = request.form.get('experience')
        spec_name = request.form.get('specialization')
        
        department = Department.query.filter_by(name=spec_name).first()
        if not department:
            department = Department(name=spec_name)
            db.session.add(department)
            db.session.commit()
        doctor.department_id = department.id
        
        db.session.commit()
        flash('Doctor details updated!', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('a_edit.html', doctor=doctor)

# --- SEPARATE DELETE AND BLACKLIST FUNCTIONS ---
@admin_bp.route('/delete_doctor/<int:id>', methods=['POST'])
@login_required(role="admin")
def delete_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor deleted successfully.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/blacklist_doctor/<int:id>', methods=['POST'])
@login_required(role="admin")
def blacklist_doctor_view(id):
    doctor = Doctor.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor blacklisted successfully.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_patient/<int:id>', methods=['POST'])
@login_required(role="admin")
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient deleted successfully.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/view_patient_history/<int:patient_id>', methods=['GET'])
@login_required(role="admin")
def view_patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient_id).all()
    return render_template('a_view.html', patient=patient, treatments=treatments)


# =====================================================
# DOCTOR ROUTES
# =====================================================

@doctor_bp.route('/dashboard')
@login_required('doctor')
def dashboard():
    doctor = Doctor.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
    
    # Assigned patients logic
    patient_ids = {appt.patient_id for appt in appointments}
    assigned_patients = Patient.query.filter(Patient.id.in_(patient_ids)).all()
    
    return render_template('doctor_dashboard.html', 
                           doctor=doctor, 
                           appointments=appointments,
                           assigned_patients=assigned_patients)

@doctor_bp.route('/appointment_action/<int:id>/<string:action>', methods=['POST'])
@login_required('doctor')
def appointment_action(id, action):
    appointment = Appointment.query.get_or_404(id)
    if action == 'complete':
        appointment.status = 'Completed'
    elif action == 'cancel':
        appointment.status = 'Cancelled'
    db.session.commit()
    return redirect(url_for('doctor.dashboard'))

@doctor_bp.route('/update_history/<int:appointment_id>', methods=['GET', 'POST'])
@login_required('doctor')
def update_history(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    treatment = Treatment.query.filter_by(appointment_id=appointment.id).first()
    
    if request.method == 'POST':
        if not treatment:
            treatment = Treatment(appointment_id=appointment.id)
            db.session.add(treatment)
        
        treatment.diagnosis = request.form.get('diagnosis')
        treatment.prescription = request.form.get('prescription')
        treatment.medicines = request.form.get('medicines')
        appointment.status = 'Completed'
        
        db.session.commit()
        flash('Patient history updated!', 'success')
        return redirect(url_for('doctor.dashboard'))
        
    return render_template('doc_update.html', appointment=appointment, treatment=treatment)

@doctor_bp.route('/view_patient_history/<int:patient_id>', methods=['GET'])
@login_required('doctor')
def view_patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient_id).all()
    return render_template('doc_view.html', patient=patient, treatments=treatments)

@doctor_bp.route('/availability', methods=['GET', 'POST'])
@login_required('doctor')
def availability():
    if request.method == 'POST':
        flash('Availability saved (Demo).', 'success')
        return redirect(url_for('doctor.dashboard'))
    return render_template('doc_provide_availability.html')


# =====================================================
# PATIENT ROUTES
# =====================================================

@patient_bp.route('/dashboard')
@login_required(role="patient")
def dashboard():
    current_patient = Patient.query.get(session['user_id'])
    departments = Department.query.all()
    appointments = Appointment.query.filter_by(patient_id=session.get('user_id')).all()
    
    return render_template('patient_dashboard.html', 
                           departments=departments, 
                           appointments=appointments, 
                           user=current_patient)

@patient_bp.route('/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required(role="patient")
def book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    if request.method == 'POST':
        date_str = request.form.get('date')
        time_slot = request.form.get('time_slot')
        try:
            appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            existing = Appointment.query.filter_by(doctor_id=doctor.id, appointment_date=appt_date, time_slot=time_slot).first()
            if existing:
                flash('Slot already booked.', 'danger')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor.id))
            
            new_appointment = Appointment(
                patient_id=session['user_id'],
                doctor_id=doctor.id,
                appointment_date=appt_date,
                time_slot=time_slot,
                status="Booked"
            )
            db.session.add(new_appointment)
            db.session.commit()
            flash('Booked successfully!', 'success')
            return redirect(url_for('patient.dashboard'))
        except ValueError:
            flash('Invalid date.', 'danger')

    return render_template('p_availability.html', doctor=doctor)

@patient_bp.route('/appointment_action/<int:appt_id>/<string:action>', methods=['POST'])
@login_required('patient')
def appointment_action(appt_id, action):
    appointment = Appointment.query.get_or_404(appt_id)
    if appointment.patient_id != session['user_id']:
        return redirect(url_for('patient.dashboard'))
        
    if action == 'cancel' and appointment.status == 'Booked':
        appointment.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled.', 'warning')
    else:
        flash('Cannot cancel.', 'danger')
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/history')
@login_required(role="patient")
def history():
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == session['user_id']).all()
    return render_template('p_history.html', treatments=treatments)

@patient_bp.route('/department/<int:dept_id>')
@login_required('patient')
def department(dept_id):
    department = Department.query.get_or_404(dept_id)
    return render_template('view_department.html', department=department)

@patient_bp.route('/doctor_profile/<int:doctor_id>')
@login_required('patient')
def doctor_profile(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return render_template('view_doctor.html', doctor=doctor)

@patient_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required(role="patient")
def edit_profile():
    current_patient = Patient.query.get(session['user_id'])
    if request.method == 'POST':
        current_patient.full_name = request.form.get('full_name')
        current_patient.contact = request.form.get('contact')
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('patient.dashboard'))
    return render_template('p_edit_profile.html', user=current_patient)