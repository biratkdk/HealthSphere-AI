from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.ml_utils import get_model_registry


ROOT = Path(__file__).resolve().parents[3]
TRAINING_DIR = ROOT / "ml_pipeline" / "training"
MODELS_DIR = ROOT / "ml_pipeline" / "models"
MANIFEST_PATH = MODELS_DIR / "retraining_manifest.json"

TRAINING_JOBS = {
    "icu_deterioration_lstm": TRAINING_DIR / "train_icu.py",
    "disease_risk_xgboost": TRAINING_DIR / "train_disease.py",
    "imaging_triage_cnn": TRAINING_DIR / "train_imaging.py",
    "care_plan_recommendation_policy": TRAINING_DIR / "train_treatment.py",
}


def plan_retraining_window() -> list[dict[str, str]]:
    now = datetime.now(timezone.utc)
    jobs = []
    for model in get_model_registry():
        jobs.append(
            {
                "model": model.name,
                "scheduled_for": (now + timedelta(hours=4)).isoformat(),
                "owner": model.owner,
                "reason": "Routine monitoring and calibration review",
                "validation_status": model.validation_status,
            }
        )
    return jobs


def run_training_job(model_name: str) -> dict[str, str]:
    script_path = TRAINING_JOBS[model_name]
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "model": model_name,
        "script": str(script_path.relative_to(ROOT)).replace("\\", "/"),
        "stdout_tail": "\n".join(completed.stdout.strip().splitlines()[-5:]),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


def evaluate_release_gates() -> dict[str, object]:
    registry = get_model_registry()
    blocked = [
        model.name
        for model in registry
        if model.validation_status not in {"approved", "staging"} or not model.artifact_available
    ]
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "ready_for_release": not blocked,
        "blocked_models": blocked,
        "models_reviewed": len(registry),
    }


def publish_retraining_manifest(training_results: list[dict[str, str]] | None = None) -> str:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "planned_jobs": plan_retraining_window(),
        "training_results": training_results or [],
        "release_gates": evaluate_release_gates(),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return str(MANIFEST_PATH)
