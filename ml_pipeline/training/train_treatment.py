from pathlib import Path

import joblib
import pandas as pd
from sklearn.tree import DecisionTreeClassifier


ROOT = Path(__file__).resolve().parents[1]
vitals = pd.read_csv(ROOT / "data" / "raw" / "vitals.csv")
labs = pd.read_csv(ROOT / "data" / "raw" / "labs.csv")
data = vitals.merge(labs, on="patient_id")

feature_columns = [
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "oxygen_saturation",
    "glucose",
    "lactate",
    "sepsis_watch",
]

X = data[feature_columns]
y = data["treatment_class"]

model = DecisionTreeClassifier(max_depth=4, random_state=21)
model.fit(X, y)

class_actions = {
    0: [
        "Activate rapid multidisciplinary review within 15 minutes.",
        "Repeat lactate and blood cultures, then review antimicrobial coverage.",
    ],
    1: [
        "Tighten glucose monitoring cadence and review endocrine consult need.",
        "Schedule follow-up reassessment within 60 minutes.",
    ],
    2: [
        "Verify telemetry trending and optimize cardiology prevention bundle.",
        "Continue standard care pathway with routine reassessment.",
    ],
}

artifact_path = ROOT / "models" / "rl_treatment.pt"
joblib.dump({"model": model, "feature_columns": feature_columns, "class_actions": class_actions}, artifact_path)
print(f"Saved treatment policy to {artifact_path}")
