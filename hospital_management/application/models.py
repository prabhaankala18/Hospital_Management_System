from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Create the database instance.
# This will be initialized with the Flask app in app.py
db = SQLAlchemy()

class Admin(db.Model):
    """
    Model for the Admin user.
    This user is predefined and has full access.
    """
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'
    
class Department(db.Model):
    """
    Model for a hospital department or specialization.
    e.g., "Cardiology", "Oncology"
    """
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    # --- Relationships ---
    # One-to-Many: One Department has many Doctors.
    doctors = db.relationship('Doctor', back_populates='department', lazy=True)

    def __repr__(self):
        return f'<Department {self.name}>'

class Doctor(db.Model):
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    experience_years = db.Column(db.Integer, default=0)
    
    # --- Foreign Keys ---
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    
    # --- Relationships ---
    # Many-to-One: Many Doctors belong to one Department.
    department = db.relationship('Department', back_populates='doctors')
    
    # One-to-Many: One Doctor can have many Appointments.
    appointments = db.relationship('Appointment', back_populates='doctor', lazy=True)
    
    # One-to-Many: One Doctor has many Availability slots.
    availability = db.relationship('DoctorAvailability', back_populates='doctor', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Doctor {self.full_name}>'


class Patient(db.Model):
    """
    Model for a Patient.
    Patients can register themselves.
    """
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    contact = db.Column(db.String(20))
    
    # --- Relationships ---
    # One-to-Many: One Patient can have many Appointments.
    appointments = db.relationship('Appointment', back_populates='patient', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Patient {self.full_name}>'


class Appointment(db.Model):
    """
    Model for an Appointment.
    This table links a Patient and a Doctor.
    """
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(30), nullable=False) # e.g., "08:00 - 12:00 am"
    status = db.Column(db.String(20), nullable=False, default='Booked') # "Booked", "Completed", "Cancelled"
    
    # --- Foreign Keys ---
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # --- Relationships ---
    # Many-to-One: Many Appointments belong to one Patient.
    patient = db.relationship('Patient', back_populates='appointments')
    
    # Many-to-One: Many Appointments are assigned to one Doctor.
    doctor = db.relationship('Doctor', back_populates='appointments')
    
    # One-to-One: One Appointment has one Treatment record.
    treatment = db.relationship('Treatment', back_populates='appointment', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Appointment {self.appointment_date} {self.time_slot}>'


class Treatment(db.Model):
    """
    Model for Treatment details.
    This is created by a Doctor for a specific Appointment.
    """
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    medicines = db.Column(db.Text)
    
    # --- Foreign Keys ---
    # One-to-One: This treatment belongs to exactly one appointment.
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True, nullable=False)
    
    # --- Relationships ---
    appointment = db.relationship('Appointment', back_populates='treatment')

    def __repr__(self):
        return f'<Treatment for Appointment {self.appointment_id}>'


class DoctorAvailability(db.Model):
    """
    Model for Doctor's 7-day availability schedule.
    """
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(30), nullable=False) # "08:00 - 12:00 am", "04:00 - 9:00 pm"
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    
    # --- Foreign Keys ---
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # --- Relationships ---
    # Many-to-One: Many availability slots belong to one Doctor.
    doctor = db.relationship('Doctor', back_populates='availability')

    def __repr__(self):
        return f'<Availability Dr. {self.doctor_id} on {self.date} at {self.time_slot} is {self.is_available}>'

