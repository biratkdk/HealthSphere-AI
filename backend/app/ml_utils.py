from backend.app.models import DiseaseRiskResponse, IcuRiskResponse, ImagingAnalysisResponse, ModelRegistryEntry, PatientRecord, TreatmentRecommendation
from backend.app.services.model_runtime import get_model_runtime


def predict_icu_risk(patient: PatientRecord) -> IcuRiskResponse:
    return get_model_runtime().predict_icu_risk(patient)


def predict_disease(patient: PatientRecord) -> DiseaseRiskResponse:
    return get_model_runtime().predict_disease(patient)


def analyze_imaging(file_bytes: bytes, filename: str = "uploaded-image") -> ImagingAnalysisResponse:
    return get_model_runtime().analyze_imaging(file_bytes, filename)


def recommend_treatment(
    patient: PatientRecord,
    icu_risk: IcuRiskResponse,
    disease_risk: DiseaseRiskResponse,
) -> TreatmentRecommendation:
    return get_model_runtime().recommend_treatment(patient, icu_risk, disease_risk)


def get_model_registry() -> list[ModelRegistryEntry]:
    return get_model_runtime().registry_entries()
