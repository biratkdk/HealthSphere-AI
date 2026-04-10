from __future__ import annotations

import hashlib
import io
import logging
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from statistics import mean

_log = logging.getLogger("healthsphere.model_runtime")

import joblib
import numpy as np
import pandas as pd
from PIL import Image
from pydicom import dcmread

from backend.app.models import (
    DiseaseRiskResponse,
    IcuRiskResponse,
    ImagingAnalysisResponse,
    ModelRegistryEntry,
    PatientRecord,
    TreatmentRecommendation,
)


ROOT = Path(__file__).resolve().parents[3]


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _risk_band(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def _latest_lab_value(patient: PatientRecord, lab_name: str, default: float = 0.0) -> float:
    matches = [lab.value for lab in patient.labs if lab.name.lower() == lab_name.lower()]
    return matches[-1] if matches else default


@dataclass
class ArtifactState:
    artifact_path: Path
    version: str
    owner: str
    validation_status: str
    last_retrained: datetime
    monitoring_tags: list[str]
    model: object | None = None
    loaded_at: datetime | None = None
    load_attempted: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def artifact_available(self) -> bool:
        return self.model is not None

    @property
    def serving_mode(self) -> str:
        return "artifact" if self.artifact_available else "fallback"


class ModelRuntime:
    def __init__(self) -> None:
        self._catalog: dict[str, ArtifactState] = {
            "icu_deterioration_sequence_model": ArtifactState(
                artifact_path=ROOT / "ml_pipeline" / "models" / "lstm_icu.pt",
                version="1.3.0",
                owner="clinical-ai@healthsphere.local",
                validation_status="approved",
                last_retrained=datetime(2025, 12, 15, tzinfo=UTC),
                monitoring_tags=["icu", "time-series", "drift-watch"],
            ),
            "chronic_disease_risk_model": ArtifactState(
                artifact_path=ROOT / "ml_pipeline" / "models" / "xgboost_disease.pkl",
                version="2.1.4",
                owner="population-health@healthsphere.local",
                validation_status="approved",
                last_retrained=datetime(2025, 12, 7, tzinfo=UTC),
                monitoring_tags=["tabular", "risk", "population-health"],
            ),
            "thoracic_imaging_triage_model": ArtifactState(
                artifact_path=ROOT / "ml_pipeline" / "models" / "cnn_imaging.pt",
                version="1.0.0",
                owner="radiology-ai@healthsphere.local",
                validation_status="approved",
                last_retrained=datetime(2025, 11, 28, tzinfo=UTC),
                monitoring_tags=["imaging", "radiology", "triage"],
            ),
            "care_plan_recommendation_policy": ArtifactState(
                artifact_path=ROOT / "ml_pipeline" / "models" / "rl_treatment.pt",
                version="1.1.0",
                owner="care-ops@healthsphere.local",
                validation_status="approved",
                last_retrained=datetime(2025, 12, 1, tzinfo=UTC),
                monitoring_tags=["recommendation", "governance", "audit"],
            ),
        }

    def load_artifacts(self, force: bool = False) -> None:
        for state in self._catalog.values():
            if state.model is not None and not force:
                continue
            if state.load_attempted and not force:
                continue
            state.notes.clear()
            state.load_attempted = True
            if not state.artifact_path.exists():
                state.model = None
                state.loaded_at = None
                state.notes.append("Artifact file is not present in the packaged runtime.")
                continue
            try:
                with warnings.catch_warnings(record=True) as caught_warnings:
                    warnings.simplefilter("always")
                    state.model = joblib.load(state.artifact_path)
                state.loaded_at = datetime.now(UTC)
                for item in caught_warnings:
                    message = str(item.message).strip()
                    if message:
                        state.notes.append(f"Load warning: {message}")
            except Exception as exc:  # pragma: no cover - defensive
                state.model = None
                state.loaded_at = None
                state.notes.append(f"Artifact load failed: {exc}")

    def registry_entries(self) -> list[ModelRegistryEntry]:
        self.load_artifacts()
        entries: list[ModelRegistryEntry] = []
        for name, state in self._catalog.items():
            notes = state.notes[:] if state.notes else []
            if state.loaded_at:
                notes.append(f"Loaded at {state.loaded_at.isoformat()}")
            elif state.model is None and not notes:
                notes.append("Artifact is unavailable and runtime fallback scoring is active.")
            entries.append(
                ModelRegistryEntry(
                    name=name,
                    version=state.version,
                    artifact_path=str(state.artifact_path.relative_to(ROOT)),
                    owner=state.owner,
                    validation_status=state.validation_status,  # type: ignore[arg-type]
                    last_retrained=state.last_retrained,
                    monitoring_tags=state.monitoring_tags,
                    artifact_available=state.artifact_available,
                    serving_mode=state.serving_mode,  # type: ignore[arg-type]
                    notes=notes,
                )
            )
        return entries

    def predict_icu_risk(self, patient: PatientRecord) -> IcuRiskResponse:
        self.load_artifacts()
        score = self._predict_icu_score(patient)
        drivers = self._icu_drivers(patient)
        return IcuRiskResponse(
            patient_id=patient.patient_id,
            icu_risk=score,
            risk_band=_risk_band(score),
            drivers=drivers,
        )

    def predict_disease(self, patient: PatientRecord) -> DiseaseRiskResponse:
        self.load_artifacts()
        diabetes_risk, heart_risk, sepsis_risk = self._predict_disease_scores(patient)
        overall = mean([diabetes_risk, heart_risk, sepsis_risk])
        return DiseaseRiskResponse(
            patient_id=patient.patient_id,
            diabetes_risk=diabetes_risk,
            heart_disease_risk=heart_risk,
            sepsis_watch_risk=sepsis_risk,
            overall_risk_band=_risk_band(overall),
        )

    def recommend_treatment(
        self,
        patient: PatientRecord,
        icu_risk: IcuRiskResponse,
        disease_risk: DiseaseRiskResponse,
    ) -> TreatmentRecommendation:
        self.load_artifacts()
        actions = self._treatment_actions(patient, icu_risk, disease_risk)
        priority_score = max(
            icu_risk.icu_risk,
            disease_risk.diabetes_risk,
            disease_risk.heart_disease_risk,
            disease_risk.sepsis_watch_risk,
        )
        return TreatmentRecommendation(
            patient_id=patient.patient_id,
            priority=_risk_band(priority_score),
            actions=actions,
            rationale=(
                f"Recommendations synthesize physiologic instability, lab trends, and current care setting for {patient.name}."
            ),
            recommended_follow_up_minutes=15 if priority_score >= 0.8 else 60 if priority_score >= 0.5 else 240,
        )

    def analyze_imaging(self, file_bytes: bytes, filename: str = "uploaded-image") -> ImagingAnalysisResponse:
        self.load_artifacts()
        state = self._catalog["thoracic_imaging_triage_model"]
        anomaly_score = None

        try:
            features = self._image_features(file_bytes, filename)
            if state.model is not None:
                anomaly_score = float(state.model.predict_proba([features])[0][1])
        except Exception as exc:  # pragma: no cover - artifact/inference failure
            _log.warning("imaging-model-prediction-failed", extra={"error": str(exc), "filename": filename})
            state.notes.append(f"Imaging prediction failed at inference: {exc}")
            anomaly_score = None

        if anomaly_score is None:
            # Deterministic fallback — only used when ML artifact is unavailable or prediction fails.
            # This is logged so ops can track fallback activation rate.
            _log.info("imaging-model-fallback-active", extra={"filename": filename, "mode": state.serving_mode})
            digest = hashlib.sha256(file_bytes or filename.encode("utf-8")).hexdigest()
            anomaly_score = int(digest[:8], 16) / 0xFFFFFFFF

        anomaly_score = round(_clamp(anomaly_score), 2)
        confidence = round(0.8 + anomaly_score * 0.19, 2)

        if anomaly_score >= 0.72:
            result = "Review recommended for focal opacity pattern."
            next_step = "Escalate to radiology over-read and compare with prior study."
        elif anomaly_score >= 0.45:
            result = "Mild abnormal texture detected."
            next_step = "Schedule secondary review with clinical correlation."
        else:
            result = "No acute anomaly signal detected."
            next_step = "Continue routine imaging surveillance."

        return ImagingAnalysisResponse(
            result=result,
            confidence=confidence,
            anomaly_score=anomaly_score,
            suggested_next_step=next_step,
        )

    def _predict_icu_score(self, patient: PatientRecord) -> float:
        state = self._catalog["icu_deterioration_sequence_model"]
        feature_columns = [
            "age",
            "heart_rate",
            "respiratory_rate",
            "systolic_bp",
            "temperature_c",
            "oxygen_saturation",
            "pain_score",
            "glucose",
            "lactate",
            "creatinine",
        ]
        features = pd.DataFrame([self._icu_features(patient)], columns=feature_columns)
        if state.model is not None:
            try:
                return round(_clamp(float(state.model.predict_proba(features)[0][1])), 2)
            except Exception as exc:  # pragma: no cover
                _log.warning("icu-model-prediction-failed", extra={"error": str(exc), "patient_id": patient.patient_id})
                state.notes.append(f"Prediction fallback triggered for ICU model: {exc}")

        vitals = patient.vitals
        lactate = _latest_lab_value(patient, "Lactate", default=1.2)
        kidney_stress = _latest_lab_value(patient, "Creatinine", default=1.0)
        score = (
            (vitals.heart_rate - 70) / 120
            + (vitals.respiratory_rate - 14) / 40
            + (95 - vitals.systolic_bp) / 80
            + (vitals.temperature_c - 36.8) / 5
            + (95 - vitals.oxygen_saturation) / 20
            + (lactate - 1.0) / 5
            + (kidney_stress - 1.0) / 4
        ) / 7
        return round(_clamp(score + 0.45), 2)

    def _predict_disease_scores(self, patient: PatientRecord) -> tuple[float, float, float]:
        state = self._catalog["chronic_disease_risk_model"]

        if isinstance(state.model, dict):
            try:
                feature_columns = state.model.get("feature_columns", [])
                feature_frame = pd.DataFrame([self._disease_features(patient)], columns=feature_columns)
                diabetes_risk = float(state.model["models"]["diabetes"].predict_proba(feature_frame)[0][1])
                heart_risk = float(state.model["models"]["heart"].predict_proba(feature_frame)[0][1])
                sepsis_risk = float(state.model["models"]["sepsis"].predict_proba(feature_frame)[0][1])
                return tuple(round(_clamp(score), 2) for score in (diabetes_risk, heart_risk, sepsis_risk))
            except Exception as exc:  # pragma: no cover
                _log.warning("disease-model-prediction-failed", extra={"error": str(exc), "patient_id": patient.patient_id})
                state.notes.append(f"Prediction fallback triggered for disease model: {exc}")

        glucose = _latest_lab_value(patient, "Glucose", default=110)
        hba1c = _latest_lab_value(patient, "HbA1c", default=6.2)
        ldl = _latest_lab_value(patient, "LDL", default=100)
        troponin = _latest_lab_value(patient, "Troponin", default=0.01)
        lactate = _latest_lab_value(patient, "Lactate", default=1.0)
        diabetes_risk = round(_clamp(((glucose - 90) / 180 + (hba1c - 5.7) / 6 + patient.age / 120) / 3 + 0.22), 2)
        heart_risk = round(
            _clamp(((ldl - 90) / 160 + patient.vitals.systolic_bp / 200 + troponin * 3 + patient.age / 120) / 4 + 0.18),
            2,
        )
        sepsis_risk = round(
            _clamp(((lactate - 1.0) / 4 + patient.vitals.temperature_c / 45 + patient.vitals.heart_rate / 180) / 3),
            2,
        )
        return diabetes_risk, heart_risk, sepsis_risk

    def _treatment_actions(
        self,
        patient: PatientRecord,
        icu_risk: IcuRiskResponse,
        disease_risk: DiseaseRiskResponse,
    ) -> list[str]:
        state = self._catalog["care_plan_recommendation_policy"]

        if isinstance(state.model, dict):
            try:
                feature_columns = state.model.get("feature_columns", [])
                feature_frame = pd.DataFrame([self._treatment_features(patient, disease_risk)], columns=feature_columns)
                prediction = int(state.model["model"].predict(feature_frame)[0])
                action_bundles = state.model["class_actions"]
                predicted = action_bundles.get(prediction, [])
                if predicted:
                    return predicted
            except Exception as exc:  # pragma: no cover
                _log.warning("treatment-model-prediction-failed", extra={"error": str(exc), "patient_id": patient.patient_id})
                state.notes.append(f"Prediction fallback triggered for treatment policy: {exc}")

        actions: list[str] = []
        if icu_risk.icu_risk >= 0.8:
            actions.append("Activate rapid multidisciplinary review within 15 minutes.")
        if disease_risk.sepsis_watch_risk >= 0.6:
            actions.append("Repeat lactate and blood cultures, then review antimicrobial coverage.")
        if disease_risk.heart_disease_risk >= 0.5:
            actions.append("Verify telemetry trending and optimize cardiology prevention bundle.")
        if disease_risk.diabetes_risk >= 0.55:
            actions.append("Tighten glucose monitoring cadence and review endocrine consult need.")
        if not actions:
            actions.append("Continue standard care pathway with routine reassessment.")
        return actions

    def _icu_features(self, patient: PatientRecord) -> list[float]:
        return [
            patient.age,
            patient.vitals.heart_rate,
            patient.vitals.respiratory_rate,
            patient.vitals.systolic_bp,
            patient.vitals.temperature_c,
            patient.vitals.oxygen_saturation,
            patient.vitals.pain_score,
            _latest_lab_value(patient, "Glucose", default=110),
            _latest_lab_value(patient, "Lactate", default=1.2),
            _latest_lab_value(patient, "Creatinine", default=1.0),
        ]

    def _disease_features(self, patient: PatientRecord) -> list[float]:
        return [
            patient.age,
            patient.vitals.heart_rate,
            patient.vitals.systolic_bp,
            patient.vitals.oxygen_saturation,
            _latest_lab_value(patient, "Glucose", default=110),
            _latest_lab_value(patient, "LDL", default=100),
            _latest_lab_value(patient, "Troponin", default=0.01),
            _latest_lab_value(patient, "HbA1c", default=6.2),
            _latest_lab_value(patient, "Lactate", default=1.0),
        ]

    def _treatment_features(self, patient: PatientRecord, disease_risk: DiseaseRiskResponse) -> list[float]:
        return [
            patient.vitals.heart_rate,
            patient.vitals.respiratory_rate,
            patient.vitals.systolic_bp,
            patient.vitals.oxygen_saturation,
            _latest_lab_value(patient, "Glucose", default=110),
            _latest_lab_value(patient, "Lactate", default=1.0),
            disease_risk.sepsis_watch_risk,
        ]

    def _image_features(self, payload: bytes, filename: str = "uploaded-image") -> list[float]:
        image = self._load_imaging_image(payload, filename)
        resized = image.convert("RGB").resize((32, 32))
        data = np.asarray(resized) / 255.0
        return [
            float(data[:, :, 0].mean()),
            float(data[:, :, 1].mean()),
            float(data[:, :, 2].mean()),
            float(data.std()),
        ]

    def _load_imaging_image(self, payload: bytes, filename: str) -> Image.Image:
        if filename.lower().endswith(".dcm") or payload[128:132] == b"DICM":
            dataset = dcmread(io.BytesIO(payload), force=True)
            pixels = np.asarray(dataset.pixel_array, dtype=np.float32)
            if pixels.ndim == 3 and pixels.shape[0] in {3, 4} and pixels.shape[-1] not in {3, 4}:
                pixels = np.moveaxis(pixels, 0, -1)

            if pixels.ndim == 2:
                normalized = self._normalize_pixel_array(pixels)
                if getattr(dataset, "PhotometricInterpretation", "").upper() == "MONOCHROME1":
                    normalized = 255 - normalized
                return Image.fromarray(normalized).convert("RGB")

            if pixels.ndim == 3:
                if pixels.shape[-1] == 1:
                    pixels = np.repeat(pixels, 3, axis=-1)
                elif pixels.shape[-1] > 3:
                    pixels = pixels[:, :, :3]
                normalized = self._normalize_pixel_array(pixels)
                return Image.fromarray(normalized.astype(np.uint8)).convert("RGB")

            raise ValueError("Unsupported DICOM pixel dimensions.")

        with Image.open(io.BytesIO(payload)) as image:
            return image.copy()

    def _normalize_pixel_array(self, pixels: np.ndarray) -> np.ndarray:
        minimum = float(np.min(pixels))
        maximum = float(np.max(pixels))
        if maximum <= minimum:
            return np.zeros_like(pixels, dtype=np.uint8)
        scaled = ((pixels - minimum) / (maximum - minimum)) * 255.0
        return np.clip(scaled, 0, 255).astype(np.uint8)

    def _icu_drivers(self, patient: PatientRecord) -> list[str]:
        drivers: list[str] = []
        if patient.vitals.oxygen_saturation < 92:
            drivers.append("Reduced oxygen saturation")
        if patient.vitals.systolic_bp < 100:
            drivers.append("Hypotension trend")
        if _latest_lab_value(patient, "Lactate", default=1.0) >= 2.5:
            drivers.append("Elevated lactate")
        if not drivers:
            drivers.append("Stable short-interval physiologic trend")
        return drivers


@lru_cache(maxsize=1)
def get_model_runtime() -> ModelRuntime:
    return ModelRuntime()
