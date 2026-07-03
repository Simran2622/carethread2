from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, Patient, Doctor, RoleEnum
from app.schemas.schemas import UserCreate, UserLogin, TokenOut
from app.auth import hash_password, verify_password, create_access_token
from app.logger import app_logger

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if payload.role == RoleEnum.doctor and not payload.specialty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctors must provide a specialty"
        )

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()

    if payload.role == RoleEnum.patient:
        profile = Patient(user_id=user.id, age=payload.age)
    else:
        profile = Doctor(user_id=user.id, specialty=payload.specialty)

    db.add(profile)
    db.commit()
    db.refresh(user)

    app_logger.info(f"New {payload.role} registered: {payload.email}")

    token = create_access_token({"user_id": user.id, "role": user.role.value})
    return TokenOut(access_token=token, role=user.role)


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        app_logger.warning(f"Failed login attempt for email: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    app_logger.info(f"Successful login: {payload.email}")

    token = create_access_token({"user_id": user.id, "role": user.role.value})
    return TokenOut(access_token=token, role=user.role)