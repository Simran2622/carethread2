from datetime import datetime, timedelta, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Doctor, User, Appointment, AppointmentStatusEnum
from app.schemas.schemas import DoctorOut, SlotOut
from app.logger import app_logger

router = APIRouter(prefix="/doctors", tags=["doctors"])

SLOT_DURATION_MINUTES = 30
WORK_START = time(9, 0)
WORK_END = time(17, 0)
LUNCH_START = time(13, 0)
LUNCH_END = time(14, 0)


@router.get("", response_model=List[DoctorOut])
def list_doctors(
    specialty: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    query = db.query(Doctor).join(User).filter(Doctor.is_available == True)

    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))

    doctors = query.all()

    return [
        DoctorOut(
            id=d.id,
            name=d.user.name,
            specialty=d.specialty,
            years_experience=d.years_experience,
            is_available=d.is_available,
        )
        for d in doctors
    ]


@router.get("/{doctor_id}/slots", response_model=List[SlotOut])
def get_available_slots(
    doctor_id: int,
    date: str,
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    try:
        day = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    all_slots = []
    current = datetime.combine(day, WORK_START)
    end_of_day = datetime.combine(day, WORK_END)

    while current + timedelta(minutes=SLOT_DURATION_MINUTES) <= end_of_day:
        slot_end = current + timedelta(minutes=SLOT_DURATION_MINUTES)
        is_lunch = LUNCH_START <= current.time() < LUNCH_END
        if not is_lunch:
            all_slots.append((current, slot_end))
        current = slot_end

    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatusEnum.booked,
        Appointment.slot_start >= datetime.combine(day, time.min),
        Appointment.slot_start <= datetime.combine(day, time.max),
    ).all()

    booked_ranges = [(a.slot_start, a.slot_end) for a in booked]

    def overlaps(slot_start, slot_end):
        return any(
            slot_start < b_end and slot_end > b_start
            for b_start, b_end in booked_ranges
        )

    free_slots = [
        SlotOut(slot_start=s, slot_end=e)
        for s, e in all_slots
        if not overlaps(s, e)
    ]

    app_logger.info(
        f"Slots requested for doctor {doctor_id} on {date}: "
        f"{len(free_slots)} free slots"
    )

    return free_slots