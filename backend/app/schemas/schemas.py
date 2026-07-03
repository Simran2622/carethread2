from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.models.models import RoleEnum, UrgencyEnum, AppointmentStatusEnum


# ─── AUTH ────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum
    specialty: Optional[str] = None
    age: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum


# ─── TRIAGE ──────────────────────────────────────────

class TriageCreate(BaseModel):
    symptoms: List[str]


class TriageOut(BaseModel):
    id: int
    symptoms: List[str]
    urgency_level: UrgencyEnum
    suggested_specialty: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── DOCTORS ─────────────────────────────────────────

class DoctorOut(BaseModel):
    id: int
    name: str
    specialty: str
    years_experience: int
    is_available: bool

    class Config:
        from_attributes = True


class SlotOut(BaseModel):
    slot_start: datetime
    slot_end: datetime


# ─── APPOINTMENTS ────────────────────────────────────

class AppointmentCreate(BaseModel):
    doctor_id: int
    slot_start: datetime
    slot_end: datetime
    triage_request_id: Optional[int] = None


class AppointmentOut(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    slot_start: datetime
    slot_end: datetime
    status: AppointmentStatusEnum

    class Config:
        from_attributes = True


# ─── AUDIT LOG ───────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    appointment_id: int
    action: str
    triggered_by: int
    timestamp: datetime

    class Config:
        from_attributes = True