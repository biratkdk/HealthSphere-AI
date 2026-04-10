from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.enterprise_repository import alerts_for_patient, get_patient, list_handoff_notes, list_patient_tasks, list_patients
from backend.app.ml_utils import predict_disease, predict_icu_risk, recommend_treatment
from backend.app.models import DiseaseRiskResponse, IcuRiskResponse, PatientRecord, PatientSummary, TreatmentRecommendation, UserProfile


def _resolve_organization_id(current_user: UserProfile | None = None, organization_id: int | None = None) -> int:
    resolved = organization_id or getattr(current_user, "organization_id", None)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is not attached to an organization.")
    return resolved


def get_patient_or_404(
    db: Session,
    patient_id: int,
    current_user: UserProfile | None = None,
    organization_id: int | None = None,
) -> PatientRecord:
    resolved_organization_id = _resolve_organization_id(current_user, organization_id)
    patient = get_patient(db, resolved_organization_id, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} was not found.",
        )
    return patient


def list_patient_records(
    db: Session,
    current_user: UserProfile,
    query: str | None = None,
    limit: int = 200,
) -> list[PatientRecord]:
    return list_patients(db, _resolve_organization_id(current_user), query=query, limit=limit)


def get_icu_prediction(db: Session, patient_id: int, current_user: UserProfile) -> IcuRiskResponse:
    patient = get_patient_or_404(db, patient_id, current_user)
    return predict_icu_risk(patient)


def get_disease_prediction(db: Session, patient_id: int, current_user: UserProfile) -> DiseaseRiskResponse:
    patient = get_patient_or_404(db, patient_id, current_user)
    return predict_disease(patient)


def get_treatment_plan(db: Session, patient_id: int, current_user: UserProfile) -> TreatmentRecommendation:
    patient = get_patient_or_404(db, patient_id, current_user)
    icu_risk = predict_icu_risk(patient)
    disease_risk = predict_disease(patient)
    return recommend_treatment(patient, icu_risk, disease_risk)


def get_patient_summary(db: Session, patient_id: int, current_user: UserProfile) -> PatientSummary:
    organization_id = _resolve_organization_id(current_user)
    patient = get_patient_or_404(db, patient_id, current_user)
    icu_risk = predict_icu_risk(patient)
    disease_risk = predict_disease(patient)
    treatment = recommend_treatment(patient, icu_risk, disease_risk)
    return PatientSummary(
        patient=patient,
        icu_risk=icu_risk,
        disease_risk=disease_risk,
        treatment=treatment,
        open_alerts=alerts_for_patient(db, organization_id, patient_id),
        tasks=list_patient_tasks(db, organization_id, patient_id),
        recent_handoffs=list_handoff_notes(db, organization_id, patient_id, limit=6),
    )


def get_patient_summary_for_organization(db: Session, organization_id: int, patient_id: int) -> PatientSummary:
    patient = get_patient_or_404(db, patient_id, organization_id=organization_id)
    icu_risk = predict_icu_risk(patient)
    disease_risk = predict_disease(patient)
    treatment = recommend_treatment(patient, icu_risk, disease_risk)
    return PatientSummary(
        patient=patient,
        icu_risk=icu_risk,
        disease_risk=disease_risk,
        treatment=treatment,
        open_alerts=alerts_for_patient(db, organization_id, patient_id),
        tasks=list_patient_tasks(db, organization_id, patient_id),
        recent_handoffs=list_handoff_notes(db, organization_id, patient_id, limit=6),
    )
