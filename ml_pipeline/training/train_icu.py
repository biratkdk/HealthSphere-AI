from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
vitals = pd.read_csv(ROOT / "data" / "raw" / "vitals.csv")
labs = pd.read_csv(ROOT / "data" / "raw" / "labs.csv")
data = vitals.merge(labs, on="patient_id")

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

X = data[feature_columns]
y = data["icu_event"]

model = Pipeline(
    [
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=300)),
    ]
)
model.fit(X, y)

artifact_path = ROOT / "models" / "lstm_icu.pt"
joblib.dump(model, artifact_path)
print(f"Saved ICU model to {artifact_path}")
