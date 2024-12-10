from sqlalchemy import Column, String, Integer, Boolean, Date, Text

from main import db


class Patient(db.Model):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=True)
    address = Column(String(), nullable=True) 
    gender = Column(String(10), nullable=False)  
    phone = Column(String(15), nullable=False)
    dob = Column(Date, nullable=True)

    # Relationships
    lab_results = db.relationship('LabResult', back_populates='patient', lazy='dynamic')

    def __repr__(self):
        return f"<Patient(id={self.id}, name={self.first_name} {self.last_name}, email={self.email})>"
