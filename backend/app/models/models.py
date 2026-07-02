import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class RoleEnum(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"


class UrgencyEnum(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"


class AppointmentStatusEnum(str, enum.Enum):
    booked = "booked"
    cancelled = "cancelled"
    completed = "completed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient_profile = relationship("Patient", back_populates="user", uselist=False)
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    medical_history = Column(String, nullable=True)

    user = relationship("User", back_populates="patient_profile")
    triage_requests = relationship("TriageRequest", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    specialty = Column(String, nullable=False, index=True)
    years_experience = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)

    user = relationship("User", back_populates="doctor_profile")
    appointments = relationship("Appointment", back_populates="doctor")


class TriageRequest(Base):
    __tablename__ = "triage_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    symptoms = Column(JSON, nullable=False)
    urgency_level = Column(Enum(UrgencyEnum), nullable=False)
    suggested_specialty = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="triage_requests")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    triage_request_id = Column(Integer, ForeignKey("triage_requests.id"), nullable=True)
    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatusEnum), default=AppointmentStatusEnum.booked)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    action = Column(String, nullable=False)
    triggered_by = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)