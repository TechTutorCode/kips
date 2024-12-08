from main import db
from datetime import datetime

class LabResult(db.Model):
    __tablename__ = 'lab_results'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_item_id = db.Column(db.Integer, db.ForeignKey('bill_items.id'), nullable=False)
    result_value = db.Column(db.Text, nullable=False)
    reference_range = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed
    remarks = db.Column(db.Text)
    performed_by = db.Column(db.String(100))
    performed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    bill_item = db.relationship('BillItem', backref='lab_result')
