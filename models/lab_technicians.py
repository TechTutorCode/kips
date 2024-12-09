from main import db
from datetime import datetime

class LabTechnician(db.Model):
    __tablename__ = "lab_technicians"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store hashed passwords
    specialization = db.Column(db.String(100))
    
    # Relationship with lab results (one-to-many)
    lab_results = db.relationship('LabResult', back_populates='technician', lazy='dynamic')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Boolean, default=True)  # Active or Inactive

    def __repr__(self):
        return f"<LabTechnician(id={self.id}, name={self.first_name} {self.last_name}, email={self.email})>"
