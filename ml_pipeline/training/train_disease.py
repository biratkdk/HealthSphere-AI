from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


ROOT = Path(__file__).resolve().parents[1]
vitals = pd.read_csv(ROOT / "data" / "raw" / "vitals.csv")
labs = pd.read_csv(ROOT / "data" / "raw" / "labs.csv")
data = vitals.merge(labs, on="patient_id")

feature_columns = [
    "age",
    "heart_rate",
    "systolic_bp",
    "oxygen_saturation",
    "glucose",
    "ldl",
    "troponin",
    "hba1c",
    "lactate",
]

X = data[feature_columns]
labels = {
    "diabetes": ((data["glucose"] >= 140) | (data["hba1c"] >= 6.5)).astype(int),
    "heart": ((data["ldl"] >= 145) | (data["troponin"] >= 0.03) | (data["systolic_bp"] >= 135)).astype(int),
    "sepsis": data["sepsis_watch"].astype(int),
}

models = {}
for label_name, label_values in labels.items():
    classifier = RandomForestClassifier(n_estimators=200, random_state=7)
    classifier.fit(X, label_values)
    models[label_name] = classifier

artifact_path = ROOT / "models" / "xgboost_disease.pkl"
joblib.dump({"feature_columns": feature_columns, "models": models}, artifact_path)
print(f"Saved disease model to {artifact_path}")
