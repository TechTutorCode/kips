from sqlalchemy import Column, String, Integer, Boolean, Date, Text

from main import db


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    password = Column(String(255), nullable=False)  # Store hashed passwords  
    gender = Column(String(10), nullable=False)  # e.g., Male/Female/Other
    phone = Column(String(15), nullable=False)
    status = Column(Boolean, default=True)  # Active (True) or Inactive (False)

    def __repr__(self):
        return f"<Doctor(id={self.id}, name={self.first_name} {self.last_name}, email={self.email})>"
