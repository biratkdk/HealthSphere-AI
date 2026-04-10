from datetime import datetime, timezone

from backend.app.models import DiseaseRiskResponse, IcuRiskResponse, PatientRecord, ReportArtifact, TreatmentRecommendation


def build_patient_report(
    patient: PatientRecord,
    icu_risk: IcuRiskResponse,
    disease_risk: DiseaseRiskResponse,
    treatment: TreatmentRecommendation,
) -> ReportArtifact:
    summary = (
        f"{patient.name} is currently assigned to {patient.care_unit} for {patient.diagnosis}. "
        f"The current ICU deterioration score is {icu_risk.icu_risk:.2f} with a {icu_risk.risk_band} priority band. "
        f"Disease progression indicators remain most elevated for diabetes ({disease_risk.diabetes_risk:.2f}) "
        f"and heart disease ({disease_risk.heart_disease_risk:.2f})."
    )

    actions = [
        *treatment.actions,
        "Document physician review in the care coordination note.",
        "Confirm follow-up lab cadence before the next nursing handoff.",
    ]

    risk_snapshot = {
        "icu_risk": icu_risk.icu_risk,
        "diabetes_risk": disease_risk.diabetes_risk,
        "heart_disease_risk": disease_risk.heart_disease_risk,
        "sepsis_watch_risk": disease_risk.sepsis_watch_risk,
    }

    return ReportArtifact(
        patient_id=patient.patient_id,
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        clinical_actions=actions,
        risk_snapshot=risk_snapshot,
    )
