from backend.app.models import DiseaseRiskResponse, IcuRiskResponse, ImagingAnalysisResponse, ModelRegistryEntry, PatientRecord, TreatmentRecommendation
def predict_icu_risk(patient: PatientRecord) -> IcuRiskResponse:
    from backend.app.services.model_runtime import get_model_runtime

    return get_model_runtime().predict_icu_risk(patient)


def predict_disease(patient: PatientRecord) -> DiseaseRiskResponse:
    from backend.app.services.model_runtime import get_model_runtime

    return get_model_runtime().predict_disease(patient)


def analyze_imaging(file_bytes: bytes, filename: str = "uploaded-image") -> ImagingAnalysisResponse:
    from backend.app.services.model_runtime import get_model_runtime

    return get_model_runtime().analyze_imaging(file_bytes, filename)


def recommend_treatment(
    patient: PatientRecord,
    icu_risk: IcuRiskResponse,
    disease_risk: DiseaseRiskResponse,
) -> TreatmentRecommendation:
    from backend.app.services.model_runtime import get_model_runtime

    return get_model_runtime().recommend_treatment(patient, icu_risk, disease_risk)


def get_model_registry() -> list[ModelRegistryEntry]:
    from backend.app.services.model_runtime import get_model_runtime

    return get_model_runtime().registry_entries()
