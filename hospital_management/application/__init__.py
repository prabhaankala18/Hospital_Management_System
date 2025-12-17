import os
from flask import Flask
from .models import db, Admin
from .controllers import auth_bp, admin_bp, doctor_bp, patient_bp
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    
    # Database Config
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hospital.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)

    # =========================================================
    #  DATE HELPER FUNCTIONS
    # =========================================================
    
    def add_days_filter(value, days):
        return value + timedelta(days=days)

    def format_date_filter(value, format_str="%Y-%m-%d"):
        if isinstance(value, datetime):
            return value.strftime(format_str)
        return value
        
    # CRITICAL FIX: Register as GLOBALS so they work like date_add(today, 1)
    app.jinja_env.globals.update(
        now=datetime.now,
        date_add=add_days_filter,
        date_format=format_date_filter
    )
    
    # =========================================================
    
    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(patient_bp, url_prefix='/patient')

    return app

def setup_database(app):
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            hashed_pw = generate_password_hash('admin', method='pbkdf2:sha256')
            new_admin = Admin(username='admin', password_hash=hashed_pw)
            db.session.add(new_admin)
            db.session.commit()
            print("Admin user created (User: admin, Pass: admin)")