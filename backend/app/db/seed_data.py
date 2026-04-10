from __future__ import annotations

from datetime import UTC, datetime, timedelta


REFERENCE_NOW = datetime(2025, 12, 9, 9, 17, 18, tzinfo=UTC)


def _patient(
    patient_id: int,
    *,
    mrn: str,
    name: str,
    age: int,
    sex: str,
    care_unit: str,
    diagnosis: str,
    vitals: dict,
    medications: list[str],
    risk_flags: list[str],
    updated_minutes: int,
    labs: list[dict],
    imaging_history: list[dict],
) -> dict:
    return {
        "patient_id": patient_id,
        "mrn": mrn,
        "name": name,
        "age": age,
        "sex": sex,
        "care_unit": care_unit,
        "diagnosis": diagnosis,
        "vitals": vitals,
        "medications": medications,
        "risk_flags": risk_flags,
        "last_updated": REFERENCE_NOW - timedelta(minutes=updated_minutes),
        "labs": [
            {**lab, "collected_at": REFERENCE_NOW - timedelta(minutes=lab["minutes_ago"])}
            for lab in labs
        ],
        "imaging_history": [
            {
                **item,
                "captured_at": REFERENCE_NOW - timedelta(hours=item["hours_ago"]),
            }
            for item in imaging_history
        ],
    }


SEED_PATIENTS = [
    _patient(
        1001,
        mrn="HS-1001",
        name="Srijana Karki",
        age=67,
        sex="Female",
        care_unit="ICU",
        diagnosis="Acute respiratory compromise",
        vitals={
            "heart_rate": 118,
            "respiratory_rate": 28,
            "systolic_bp": 92,
            "temperature_c": 38.4,
            "oxygen_saturation": 89,
            "pain_score": 4,
        },
        medications=["Piperacillin-tazobactam", "Norepinephrine", "Insulin sliding scale"],
        risk_flags=["Escalating oxygen requirement", "Possible septic shock"],
        updated_minutes=15,
        labs=[
            {"name": "Lactate", "value": 3.4, "unit": "mmol/L", "minutes_ago": 80},
            {"name": "Glucose", "value": 168, "unit": "mg/dL", "minutes_ago": 50},
            {"name": "Creatinine", "value": 1.7, "unit": "mg/dL", "minutes_ago": 50},
        ],
        imaging_history=[
            {
                "modality": "Chest X-Ray",
                "summary": "Diffuse bilateral patchy opacity under escalation watch",
                "confidence": 0.91,
                "hours_ago": 6,
            }
        ],
    ),
    _patient(
        1002,
        mrn="HS-1002",
        name="Nabin Shrestha",
        age=54,
        sex="Male",
        care_unit="Telemetry",
        diagnosis="Chest pain evaluation",
        vitals={
            "heart_rate": 88,
            "respiratory_rate": 18,
            "systolic_bp": 138,
            "temperature_c": 37.0,
            "oxygen_saturation": 96,
            "pain_score": 2,
        },
        medications=["Aspirin", "Atorvastatin"],
        risk_flags=["Elevated LDL", "Secondary prevention review"],
        updated_minutes=30,
        labs=[
            {"name": "Troponin", "value": 0.03, "unit": "ng/mL", "minutes_ago": 120},
            {"name": "LDL", "value": 154, "unit": "mg/dL", "minutes_ago": 720},
            {"name": "Glucose", "value": 112, "unit": "mg/dL", "minutes_ago": 120},
        ],
        imaging_history=[
            {
                "modality": "CT Coronary",
                "summary": "Moderate calcified plaque burden without acute obstruction",
                "confidence": 0.87,
                "hours_ago": 24,
            }
        ],
    ),
    _patient(
        1003,
        mrn="HS-1003",
        name="Purnima Rai",
        age=41,
        sex="Female",
        care_unit="Medical Ward",
        diagnosis="Diabetes optimization",
        vitals={
            "heart_rate": 74,
            "respiratory_rate": 16,
            "systolic_bp": 126,
            "temperature_c": 36.8,
            "oxygen_saturation": 98,
            "pain_score": 1,
        },
        medications=["Metformin", "Semaglutide", "Lisinopril"],
        risk_flags=["Suboptimal glycemic control"],
        updated_minutes=45,
        labs=[
            {"name": "HbA1c", "value": 8.6, "unit": "%", "minutes_ago": 4320},
            {"name": "Glucose", "value": 196, "unit": "mg/dL", "minutes_ago": 60},
            {"name": "Microalbumin", "value": 49, "unit": "mg/g", "minutes_ago": 4320},
        ],
        imaging_history=[
            {
                "modality": "Retinal Screening",
                "summary": "Mild non-proliferative retinal change with scheduled follow-up",
                "confidence": 0.89,
                "hours_ago": 336,
            }
        ],
    ),
    _patient(
        1004,
        mrn="HS-1004",
        name="Bikash Gurung",
        age=72,
        sex="Male",
        care_unit="Step-down",
        diagnosis="COPD exacerbation stabilization",
        vitals={
            "heart_rate": 126,
            "respiratory_rate": 30,
            "systolic_bp": 86,
            "temperature_c": 38.7,
            "oxygen_saturation": 88,
            "pain_score": 5,
        },
        medications=["Salbutamol", "Tiotropium", "Prednisolone"],
        risk_flags=["Baseline low oxygen saturation", "Escalation review"],
        updated_minutes=11,
        labs=[
            {"name": "Lactate", "value": 3.8, "unit": "mmol/L", "minutes_ago": 65},
            {"name": "Glucose", "value": 152, "unit": "mg/dL", "minutes_ago": 95},
            {"name": "Creatinine", "value": 2.0, "unit": "mg/dL", "minutes_ago": 95},
        ],
        imaging_history=[
            {
                "modality": "Chest X-Ray",
                "summary": "Hyperinflation with lower-zone streaky opacity",
                "confidence": 0.9,
                "hours_ago": 5,
            }
        ],
    ),
    _patient(
        1005,
        mrn="HS-1005",
        name="Manisha Thapa",
        age=63,
        sex="Female",
        care_unit="Endocrine Ward",
        diagnosis="Diabetes stabilization",
        vitals={
            "heart_rate": 94,
            "respiratory_rate": 20,
            "systolic_bp": 132,
            "temperature_c": 37.4,
            "oxygen_saturation": 95,
            "pain_score": 3,
        },
        medications=["Metformin", "Insulin glargine", "Lisinopril"],
        risk_flags=["Recent glucose variability", "Medication titration review"],
        updated_minutes=52,
        labs=[
            {"name": "Glucose", "value": 104, "unit": "mg/dL", "minutes_ago": 120},
            {"name": "HbA1c", "value": 6.0, "unit": "%", "minutes_ago": 2880},
            {"name": "LDL", "value": 166, "unit": "mg/dL", "minutes_ago": 2880},
        ],
        imaging_history=[
            {
                "modality": "Retinal Screening",
                "summary": "Stable background changes with annual review plan",
                "confidence": 0.85,
                "hours_ago": 240,
            }
        ],
    ),
    _patient(
        1006,
        mrn="HS-1006",
        name="Ritesh Lama",
        age=58,
        sex="Male",
        care_unit="Observation",
        diagnosis="Pulmonary infection watch",
        vitals={
            "heart_rate": 108,
            "respiratory_rate": 24,
            "systolic_bp": 98,
            "temperature_c": 38.1,
            "oxygen_saturation": 91,
            "pain_score": 4,
        },
        medications=["Ceftriaxone", "Paracetamol", "Oxygen support"],
        risk_flags=["Persistent fever trend", "Borderline hypotension"],
        updated_minutes=19,
        labs=[
            {"name": "Lactate", "value": 2.9, "unit": "mmol/L", "minutes_ago": 55},
            {"name": "Glucose", "value": 146, "unit": "mg/dL", "minutes_ago": 55},
            {"name": "Creatinine", "value": 1.5, "unit": "mg/dL", "minutes_ago": 55},
        ],
        imaging_history=[
            {
                "modality": "Chest X-Ray",
                "summary": "Right middle-zone review opacity with interval follow-up requested",
                "confidence": 0.88,
                "hours_ago": 8,
            }
        ],
    ),
    _patient(
        1007,
        mrn="HS-1007",
        name="Aashika Bhandari",
        age=47,
        sex="Female",
        care_unit="Women's Health",
        diagnosis="Postpartum infection surveillance",
        vitals={
            "heart_rate": 82,
            "respiratory_rate": 17,
            "systolic_bp": 124,
            "temperature_c": 36.7,
            "oxygen_saturation": 97,
            "pain_score": 1,
        },
        medications=["Amoxicillin-clavulanate", "Ibuprofen"],
        risk_flags=["Postpartum monitoring"],
        updated_minutes=41,
        labs=[
            {"name": "CRP", "value": 14, "unit": "mg/L", "minutes_ago": 240},
            {"name": "Glucose", "value": 98, "unit": "mg/dL", "minutes_ago": 240},
            {"name": "Creatinine", "value": 0.8, "unit": "mg/dL", "minutes_ago": 240},
        ],
        imaging_history=[
            {
                "modality": "Pelvic Ultrasound",
                "summary": "No retained products identified on follow-up review",
                "confidence": 0.92,
                "hours_ago": 36,
            }
        ],
    ),
    _patient(
        1008,
        mrn="HS-1008",
        name="Pradeep Koirala",
        age=69,
        sex="Male",
        care_unit="Telemetry",
        diagnosis="Hypertensive urgency review",
        vitals={
            "heart_rate": 112,
            "respiratory_rate": 26,
            "systolic_bp": 102,
            "temperature_c": 37.9,
            "oxygen_saturation": 90,
            "pain_score": 3,
        },
        medications=["Amlodipine", "Losartan", "Aspirin"],
        risk_flags=["Blood pressure variability", "Preventive cardiology follow-up"],
        updated_minutes=32,
        labs=[
            {"name": "Glucose", "value": 138, "unit": "mg/dL", "minutes_ago": 90},
            {"name": "Lactate", "value": 2.7, "unit": "mmol/L", "minutes_ago": 90},
            {"name": "Creatinine", "value": 1.4, "unit": "mg/dL", "minutes_ago": 90},
        ],
        imaging_history=[
            {
                "modality": "Cardiac CT",
                "summary": "Moderate plaque burden with no acute interval change",
                "confidence": 0.84,
                "hours_ago": 48,
            }
        ],
    ),
]

SEED_ALERTS = [
    {
        "alert_id": "ALT-9001",
        "patient_id": 1001,
        "severity": "critical",
        "title": "Sepsis escalation watch",
        "description": "Lactate and oxygen demand remain elevated over the last 2 hours.",
        "created_at": REFERENCE_NOW - timedelta(minutes=10),
        "acknowledged": False,
    },
    {
        "alert_id": "ALT-9002",
        "patient_id": 1004,
        "severity": "critical",
        "title": "Respiratory decompensation review",
        "description": "Low oxygen saturation and rising respiratory effort require immediate reassessment.",
        "created_at": REFERENCE_NOW - timedelta(minutes=18),
        "acknowledged": False,
    },
    {
        "alert_id": "ALT-9003",
        "patient_id": 1002,
        "severity": "medium",
        "title": "Cardiac risk review",
        "description": "Lipid profile suggests aggressive secondary prevention planning.",
        "created_at": REFERENCE_NOW - timedelta(hours=2),
        "acknowledged": False,
    },
    {
        "alert_id": "ALT-9004",
        "patient_id": 1003,
        "severity": "medium",
        "title": "Diabetes optimization follow-up",
        "description": "Current HbA1c remains above goal and needs treatment reconciliation.",
        "created_at": REFERENCE_NOW - timedelta(hours=5),
        "acknowledged": False,
    },
    {
        "alert_id": "ALT-9005",
        "patient_id": 1007,
        "severity": "low",
        "title": "Postpartum review scheduled",
        "description": "Follow-up clinical review has been added to the care pathway.",
        "created_at": REFERENCE_NOW - timedelta(hours=8),
        "acknowledged": True,
    },
]

SEED_NOTIFICATIONS = [
    {
        "notification_id": "NTF-1001",
        "recipient_username": "clinician",
        "patient_id": 1001,
        "severity": "critical",
        "category": "alerts",
        "title": "Critical deterioration requires review",
        "body": "Srijana Karki remains above the escalation threshold and needs immediate reassessment.",
        "detail": {"source": "alert-engine", "action": "review-patient"},
        "is_read": False,
        "created_at": REFERENCE_NOW - timedelta(minutes=9),
        "read_at": None,
    },
    {
        "notification_id": "NTF-1002",
        "recipient_username": "analyst",
        "patient_id": 1002,
        "severity": "medium",
        "category": "operations",
        "title": "Cardiometabolic trend moved outside baseline",
        "body": "Nabin Shrestha's telemetry pathway has a rising preventive action score for cardiac follow-up.",
        "detail": {"source": "analytics", "action": "review-queue"},
        "is_read": False,
        "created_at": REFERENCE_NOW - timedelta(minutes=26),
        "read_at": None,
    },
    {
        "notification_id": "NTF-1003",
        "recipient_username": "admin",
        "patient_id": None,
        "severity": "low",
        "category": "platform",
        "title": "Demo workspace synchronized",
        "body": "Synthetic clinical records, Nepali patient roster, and baseline alerts are ready for validation.",
        "detail": {"source": "bootstrap"},
        "is_read": False,
        "created_at": REFERENCE_NOW - timedelta(minutes=35),
        "read_at": None,
    },
]
