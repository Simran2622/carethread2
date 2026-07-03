from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import TriageRequest, Patient, User, RoleEnum
from app.schemas.schemas import TriageCreate, TriageOut
from app.auth import get_current_user
from app.logger import app_logger

router = APIRouter(prefix="/triage", tags=["triage"])

TRIAGE_RULES = [
    {
        "symptoms": {"chest_pain", "shortness_of_breath"},
        "urgency": "EMERGENCY",
        "specialty": "Cardiology"
    },
    {
        "symptoms": {"severe_bleeding", "loss_of_consciousness"},
        "urgency": "EMERGENCY",
        "specialty": "Emergency Medicine"
    },
    {
        "symptoms": {"high_fever", "persistent_cough"},
        "urgency": "URGENT",
        "specialty": "General Physician"
    },
    {
        "symptoms": {"severe_abdominal_pain"},
        "urgency": "URGENT",
        "specialty": "Gastroenterology"
    },
    {
        "symptoms": {"skin_rash", "itching"},
        "urgency": "ROUTINE",
        "specialty": "Dermatology"
    },
    {
        "symptoms": {"joint_pain", "swelling"},
        "urgency": "ROUTINE",
        "specialty": "Orthopedics"
    },
    {
        "symptoms": {"mild_headache"},
        "urgency": "ROUTINE",
        "specialty": "General Physician"
    },
]

DEFAULT_RESULT = {"urgency": "ROUTINE", "specialty": "General Physician"}


def run_triage(selected_symptoms: list) -> dict:
    selected_set = set(selected_symptoms)
    best_rule = None
    best_overlap = 0

    for rule in TRIAGE_RULES:
        overlap = len(rule["symptoms"] & selected_set)
        if overlap > best_overlap:
            best_overlap = overlap
            best_rule = rule

    if best_rule is None:
        return DEFAULT_RESULT

    return {
        "urgency": best_rule["urgency"],
        "specialty": best_rule["specialty"]
    }


@router.get("/symptoms")
def list_symptoms():
    all_symptoms = sorted({s for rule in TRIAGE_RULES for s in rule["symptoms"]})
    return {"symptoms": all_symptoms}


@router.post("", response_model=TriageOut)
def submit_triage(
    payload: TriageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can submit triage requests"
        )

    patient = db.query(Patient).filter(
        Patient.user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )

    result = run_triage(payload.symptoms)

    triage_request = TriageRequest(
        patient_id=patient.id,
        symptoms=payload.symptoms,
        urgency_level=result["urgency"],
        suggested_specialty=result["specialty"],
    )
    db.add(triage_request)
    db.commit()
    db.refresh(triage_request)

    app_logger.info(
        f"Triage completed for patient {patient.id}: "
        f"urgency={result['urgency']}, specialty={result['specialty']}"
    )

    return triage_request