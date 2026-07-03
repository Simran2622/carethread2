from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.models import (
    Appointment, Doctor, Patient, User,
    RoleEnum, AppointmentStatusEnum, AuditLog
)
from app.schemas.schemas import AppointmentCreate, AppointmentOut
from app.auth import get_current_user
from app.logger import app_logger

router = APIRouter(prefix="/appointments", tags=["appointments"])


def is_slot_available(db: Session, doctor_id: int, slot_start, slot_end) -> bool:
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatusEnum.booked,
        Appointment.slot_start < slot_end,
        Appointment.slot_end > slot_start,
    ).first()
    return conflict is None


def create_audit_log(db: Session, appointment_id: int, action: str, triggered_by: int):
    log = AuditLog(
        appointment_id=appointment_id,
        action=action,
        triggered_by=triggered_by,
    )
    db.add(log)


@router.post("", response_model=AppointmentOut)
def book_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments"
        )

    patient = db.query(Patient).filter(
        Patient.user_id == current_user.id
    ).first()

    doctor = db.query(Doctor).filter(
        Doctor.id == payload.doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    if payload.slot_end <= payload.slot_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="slot_end must be after slot_start"
        )

    # SELECT FOR UPDATE — database level lock
    # This prevents two patients from booking the same slot simultaneously
    with db.begin_nested():
        db.execute(
            select(Appointment).where(
                Appointment.doctor_id == payload.doctor_id,
                Appointment.status == AppointmentStatusEnum.booked,
                Appointment.slot_start < payload.slot_end,
                Appointment.slot_end > payload.slot_start,
            ).with_for_update()
        )

        if not is_slot_available(db, payload.doctor_id, payload.slot_start, payload.slot_end):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This slot is no longer available"
            )

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            triage_request_id=payload.triage_request_id,
            slot_start=payload.slot_start,
            slot_end=payload.slot_end,
            status=AppointmentStatusEnum.booked,
        )
        db.add(appointment)
        db.flush()

        create_audit_log(db, appointment.id, "created", current_user.id)

    db.commit()
    db.refresh(appointment)

    app_logger.info(
        f"Appointment booked: patient={patient.id}, "
        f"doctor={doctor.id}, slot={payload.slot_start}"
    )

    return appointment


@router.get("/me", response_model=List[AppointmentOut])
def my_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == RoleEnum.patient:
        patient = db.query(Patient).filter(
            Patient.user_id == current_user.id
        ).first()
        return db.query(Appointment).filter(
            Appointment.patient_id == patient.id
        ).all()
    else:
        doctor = db.query(Doctor).filter(
            Doctor.user_id == current_user.id
        ).first()
        return db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id
        ).all()


@router.patch("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    patient = db.query(Patient).filter(
        Patient.user_id == current_user.id
    ).first()
    doctor = db.query(Doctor).filter(
        Doctor.user_id == current_user.id
    ).first()

    owns_it = (
        (patient and appointment.patient_id == patient.id) or
        (doctor and appointment.doctor_id == doctor.id)
    )

    if not owns_it:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this appointment"
        )

    if appointment.status == AppointmentStatusEnum.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled"
        )

    appointment.status = AppointmentStatusEnum.cancelled
    create_audit_log(db, appointment.id, "cancelled", current_user.id)
    db.commit()
    db.refresh(appointment)

    app_logger.info(
        f"Appointment {appointment_id} cancelled by user {current_user.id}"
    )

    return appointment