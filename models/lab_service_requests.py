from main import db
from datetime import datetime

class LabServiceRequest(db.Model):
    __tablename__ = 'lab_service_requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    lab_service_id = db.Column(db.Integer, db.ForeignKey('lab_services.id'), nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=True)  # New field to track generated bill
    
    # Status tracking
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Completed, Rejected
    
    # Additional details
    clinical_notes = db.Column(db.Text)
    urgency = db.Column(db.String(20), default='Normal')  # Normal, Urgent, Emergency
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('Doctor', backref='lab_service_requests')
    patient = db.relationship('Patient', backref='lab_service_requests')
    lab_service = db.relationship('LabService', backref='lab_service_requests')
    bill = db.relationship('Bill', backref='lab_service_request')
    
    def __repr__(self):
        return f"<LabServiceRequest(id={self.id}, doctor_id={self.doctor_id}, patient_id={self.patient_id}, status={self.status})>"
