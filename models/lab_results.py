from main import db
from datetime import datetime

class LabResult(db.Model):
    __tablename__ = 'lab_results'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    bill_item_id = db.Column(db.Integer, db.ForeignKey('bill_items.id'), nullable=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('lab_technicians.id'), nullable=True)
    lab_request_id = db.Column(db.Integer, db.ForeignKey('lab_service_requests.id'), nullable=True)
    
    result_value = db.Column(db.Text, nullable=False)
    reference_range = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed
    remarks = db.Column(db.Text)
    
    performed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', back_populates='lab_results')
    bill_item = db.relationship('BillItem', backref='lab_result')
    technician = db.relationship('LabTechnician', back_populates='lab_results')
    lab_result = db.relationship('LabServiceRequest', back_populates='lab_service')
    
    # Add patient relationship through bill
    @property
    def patient_through_bill(self):
        return self.bill_item.bill.patient if self.bill_item and self.bill_item.bill else None
    
    def __repr__(self):
        return f"<LabResult(id={self.id}, status={self.status}, bill_item_id={self.bill_item_id})>"
