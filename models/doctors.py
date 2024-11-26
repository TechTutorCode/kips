from sqlalchemy import Column, String, Integer, Boolean, Date, Text
from database import Base



class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # Store hashed passwords
    dob = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)  # e.g., Male/Female/Other
    phone = Column(String(15), nullable=False, unique=True)
    avatar = Column(String(255), nullable=True)  # URL or file path
    status = Column(Boolean, default=True)  # Active (True) or Inactive (False)
    education_info = Column(Text, nullable=False)  # e.g., MBBS, MD, etc.
    specialisation = Column(String(255), nullable=False)  # e.g., Cardiologist, Surgeon

    def __repr__(self):
        return f"<Doctor(id={self.id}, name={self.first_name} {self.last_name}, email={self.email})>"
