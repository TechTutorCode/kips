from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from main import db
from datetime import datetime

class MedicineRequest(db.Model):
    __tablename__ = "medicine_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey('doctors.id'), nullable=False)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    medicine_name = Column(String(200), nullable=False)
    dosage = Column(String(100), nullable=False)
    frequency = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default='Pending')  # Pending, Approved, Rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    doctor = relationship('Doctor', backref='medicine_requests')
    patient = relationship('Patient', backref='medicine_requests')

    def __repr__(self):
        return f"<MedicineRequest(id={self.id}, medicine={self.medicine_name}, patient_id={self.patient_id}, doctor_id={self.doctor_id})>"