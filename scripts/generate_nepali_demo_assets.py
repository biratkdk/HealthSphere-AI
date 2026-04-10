from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = ROOT / "ml_pipeline" / "data" / "external"
IMAGING_DIR = ROOT / "ml_pipeline" / "data" / "raw" / "imaging"


REFERENCE_NOW = datetime(2025, 12, 9, 9, 17, 18, tzinfo=UTC)


PATIENTS = [
    {
        "patient_id": 2101,
        "mrn": "NP-2101",
        "name": "Srijana Karki",
        "age": 58,
        "sex": "Female",
        "city": "Kathmandu",
        "care_unit": "ICU",
        "diagnosis": "Community-acquired pneumonia observation",
        "vitals": {
            "heart_rate": 109,
            "respiratory_rate": 25,
            "systolic_bp": 98,
            "temperature_c": 38.1,
            "oxygen_saturation": 91,
            "pain_score": 3,
        },
        "medications": ["Ceftriaxone", "Azithromycin", "Paracetamol"],
        "risk_flags": ["Escalating oxygen requirement", "Fever trend"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=18),
        "labs": [
            {"name": "Lactate", "value": 2.6, "unit": "mmol/L", "collected_at": REFERENCE_NOW - timedelta(minutes=80)},
            {"name": "Glucose", "value": 141, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(minutes=45)},
            {"name": "Creatinine", "value": 1.3, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(minutes=45)},
        ],
        "imaging_history": [
            {
                "modality": "Chest X-Ray",
                "summary": "Patchy right lower zone haziness under follow-up",
                "confidence": 0.86,
                "captured_at": REFERENCE_NOW - timedelta(hours=6),
            }
        ],
    },
    {
        "patient_id": 2102,
        "mrn": "NP-2102",
        "name": "Nabin Shrestha",
        "age": 46,
        "sex": "Male",
        "city": "Pokhara",
        "care_unit": "Telemetry",
        "diagnosis": "Hypertensive urgency review",
        "vitals": {
            "heart_rate": 82,
            "respiratory_rate": 17,
            "systolic_bp": 164,
            "temperature_c": 36.9,
            "oxygen_saturation": 97,
            "pain_score": 1,
        },
        "medications": ["Amlodipine", "Losartan", "Aspirin"],
        "risk_flags": ["Blood pressure variability"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=34),
        "labs": [
            {"name": "Glucose", "value": 118, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=2)},
            {"name": "LDL", "value": 148, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=10)},
            {"name": "Troponin", "value": 0.02, "unit": "ng/mL", "collected_at": REFERENCE_NOW - timedelta(hours=2)},
        ],
        "imaging_history": [
            {
                "modality": "Cardiac CT",
                "summary": "Mild calcified plaque burden without acute concern",
                "confidence": 0.82,
                "captured_at": REFERENCE_NOW - timedelta(days=1),
            }
        ],
    },
    {
        "patient_id": 2103,
        "mrn": "NP-2103",
        "name": "Purnima Rai",
        "age": 32,
        "sex": "Female",
        "city": "Dharan",
        "care_unit": "Medical Ward",
        "diagnosis": "Postpartum infection watch",
        "vitals": {
            "heart_rate": 97,
            "respiratory_rate": 21,
            "systolic_bp": 112,
            "temperature_c": 37.8,
            "oxygen_saturation": 95,
            "pain_score": 4,
        },
        "medications": ["Amoxicillin-clavulanate", "Ibuprofen"],
        "risk_flags": ["Recent fever", "Postpartum monitoring"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=42),
        "labs": [
            {"name": "Lactate", "value": 1.8, "unit": "mmol/L", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
            {"name": "CRP", "value": 34, "unit": "mg/L", "collected_at": REFERENCE_NOW - timedelta(hours=5)},
            {"name": "Glucose", "value": 106, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
        ],
        "imaging_history": [
            {
                "modality": "Pelvic Ultrasound",
                "summary": "No retained products identified on limited review",
                "confidence": 0.8,
                "captured_at": REFERENCE_NOW - timedelta(days=2),
            }
        ],
    },
    {
        "patient_id": 2104,
        "mrn": "NP-2104",
        "name": "Bikash Gurung",
        "age": 61,
        "sex": "Male",
        "city": "Bharatpur",
        "care_unit": "Step-down",
        "diagnosis": "COPD exacerbation stabilization",
        "vitals": {
            "heart_rate": 101,
            "respiratory_rate": 23,
            "systolic_bp": 126,
            "temperature_c": 37.3,
            "oxygen_saturation": 90,
            "pain_score": 2,
        },
        "medications": ["Salbutamol", "Tiotropium", "Prednisolone"],
        "risk_flags": ["Baseline low oxygen saturation", "Inhaler adherence review"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=27),
        "labs": [
            {"name": "Glucose", "value": 129, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=4)},
            {"name": "Creatinine", "value": 1.1, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=4)},
            {"name": "CO2", "value": 29, "unit": "mmol/L", "collected_at": REFERENCE_NOW - timedelta(hours=4)},
        ],
        "imaging_history": [
            {
                "modality": "Chest X-Ray",
                "summary": "Hyperinflation pattern without focal consolidation",
                "confidence": 0.84,
                "captured_at": REFERENCE_NOW - timedelta(hours=9),
            }
        ],
    },
    {
        "patient_id": 2105,
        "mrn": "NP-2105",
        "name": "Manisha Thapa",
        "age": 39,
        "sex": "Female",
        "city": "Butwal",
        "care_unit": "Endocrine Ward",
        "diagnosis": "Diabetes stabilization",
        "vitals": {
            "heart_rate": 76,
            "respiratory_rate": 16,
            "systolic_bp": 122,
            "temperature_c": 36.7,
            "oxygen_saturation": 98,
            "pain_score": 1,
        },
        "medications": ["Metformin", "Insulin glargine", "Lisinopril"],
        "risk_flags": ["Recent glucose variability"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=51),
        "labs": [
            {"name": "HbA1c", "value": 8.1, "unit": "%", "collected_at": REFERENCE_NOW - timedelta(days=2)},
            {"name": "Glucose", "value": 182, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=1)},
            {"name": "Microalbumin", "value": 41, "unit": "mg/g", "collected_at": REFERENCE_NOW - timedelta(days=2)},
        ],
        "imaging_history": [
            {
                "modality": "Retinal Screening",
                "summary": "Early background retinopathy follow-up recommended",
                "confidence": 0.88,
                "captured_at": REFERENCE_NOW - timedelta(days=11),
            }
        ],
    },
    {
        "patient_id": 2106,
        "mrn": "NP-2106",
        "name": "Ritesh Lama",
        "age": 27,
        "sex": "Male",
        "city": "Lalitpur",
        "care_unit": "Observation",
        "diagnosis": "Mild head injury follow-up",
        "vitals": {
            "heart_rate": 72,
            "respiratory_rate": 15,
            "systolic_bp": 118,
            "temperature_c": 36.6,
            "oxygen_saturation": 99,
            "pain_score": 2,
        },
        "medications": ["Paracetamol"],
        "risk_flags": ["Neurologic re-check"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=23),
        "labs": [
            {"name": "Glucose", "value": 102, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
            {"name": "Sodium", "value": 139, "unit": "mmol/L", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
            {"name": "Creatinine", "value": 0.9, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
        ],
        "imaging_history": [
            {
                "modality": "CT Brain",
                "summary": "No acute intracranial bleed on initial review",
                "confidence": 0.92,
                "captured_at": REFERENCE_NOW - timedelta(hours=12),
            }
        ],
    },
    {
        "patient_id": 2107,
        "mrn": "NP-2107",
        "name": "Aashika Bhandari",
        "age": 34,
        "sex": "Female",
        "city": "Bhaktapur",
        "care_unit": "Women's Health",
        "diagnosis": "Postpartum infection surveillance",
        "vitals": {
            "heart_rate": 89,
            "respiratory_rate": 18,
            "systolic_bp": 114,
            "temperature_c": 37.5,
            "oxygen_saturation": 97,
            "pain_score": 3,
        },
        "medications": ["Ibuprofen", "Amoxicillin-clavulanate"],
        "risk_flags": ["Postpartum monitoring"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=31),
        "labs": [
            {"name": "CRP", "value": 18, "unit": "mg/L", "collected_at": REFERENCE_NOW - timedelta(hours=4)},
            {"name": "Glucose", "value": 96, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=4)},
            {"name": "Creatinine", "value": 0.8, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=4)},
        ],
        "imaging_history": [
            {
                "modality": "Pelvic Ultrasound",
                "summary": "No retained products identified on interval review",
                "confidence": 0.9,
                "captured_at": REFERENCE_NOW - timedelta(days=1),
            }
        ],
    },
    {
        "patient_id": 2108,
        "mrn": "NP-2108",
        "name": "Pradeep Koirala",
        "age": 64,
        "sex": "Male",
        "city": "Janakpur",
        "care_unit": "Telemetry",
        "diagnosis": "Preventive cardiology review",
        "vitals": {
            "heart_rate": 86,
            "respiratory_rate": 18,
            "systolic_bp": 142,
            "temperature_c": 36.9,
            "oxygen_saturation": 96,
            "pain_score": 1,
        },
        "medications": ["Aspirin", "Atorvastatin", "Losartan"],
        "risk_flags": ["Elevated LDL"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=39),
        "labs": [
            {"name": "LDL", "value": 158, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=8)},
            {"name": "Troponin", "value": 0.02, "unit": "ng/mL", "collected_at": REFERENCE_NOW - timedelta(hours=2)},
            {"name": "Glucose", "value": 109, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=2)},
        ],
        "imaging_history": [
            {
                "modality": "Cardiac CT",
                "summary": "Mild plaque burden without interval progression",
                "confidence": 0.81,
                "captured_at": REFERENCE_NOW - timedelta(days=3),
            }
        ],
    },
    {
        "patient_id": 2109,
        "mrn": "NP-2109",
        "name": "Sabina Magar",
        "age": 49,
        "sex": "Female",
        "city": "Nepalgunj",
        "care_unit": "Medical Ward",
        "diagnosis": "Diabetes pathway review",
        "vitals": {
            "heart_rate": 79,
            "respiratory_rate": 16,
            "systolic_bp": 128,
            "temperature_c": 36.8,
            "oxygen_saturation": 98,
            "pain_score": 1,
        },
        "medications": ["Metformin", "Semaglutide"],
        "risk_flags": ["Glucose variability"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=46),
        "labs": [
            {"name": "HbA1c", "value": 7.9, "unit": "%", "collected_at": REFERENCE_NOW - timedelta(days=4)},
            {"name": "Glucose", "value": 174, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=1)},
            {"name": "Microalbumin", "value": 36, "unit": "mg/g", "collected_at": REFERENCE_NOW - timedelta(days=4)},
        ],
        "imaging_history": [
            {
                "modality": "Retinal Screening",
                "summary": "Background changes with annual follow-up planned",
                "confidence": 0.85,
                "captured_at": REFERENCE_NOW - timedelta(days=10),
            }
        ],
    },
    {
        "patient_id": 2110,
        "mrn": "NP-2110",
        "name": "Roshan Tamang",
        "age": 29,
        "sex": "Male",
        "city": "Hetauda",
        "care_unit": "Observation",
        "diagnosis": "Viral pneumonia follow-up",
        "vitals": {
            "heart_rate": 104,
            "respiratory_rate": 22,
            "systolic_bp": 106,
            "temperature_c": 38.0,
            "oxygen_saturation": 92,
            "pain_score": 2,
        },
        "medications": ["Azithromycin", "Paracetamol"],
        "risk_flags": ["Escalating oxygen requirement"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=21),
        "labs": [
            {"name": "Lactate", "value": 2.4, "unit": "mmol/L", "collected_at": REFERENCE_NOW - timedelta(minutes=95)},
            {"name": "Glucose", "value": 125, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(minutes=95)},
            {"name": "Creatinine", "value": 1.0, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(minutes=95)},
        ],
        "imaging_history": [
            {
                "modality": "Chest X-Ray",
                "summary": "Mild bilateral hazy opacification for follow-up",
                "confidence": 0.83,
                "captured_at": REFERENCE_NOW - timedelta(hours=5),
            }
        ],
    },
    {
        "patient_id": 2111,
        "mrn": "NP-2111",
        "name": "Menuka Adhikari",
        "age": 57,
        "sex": "Female",
        "city": "Biratnagar",
        "care_unit": "Step-down",
        "diagnosis": "COPD stabilization",
        "vitals": {
            "heart_rate": 98,
            "respiratory_rate": 21,
            "systolic_bp": 124,
            "temperature_c": 37.2,
            "oxygen_saturation": 91,
            "pain_score": 2,
        },
        "medications": ["Tiotropium", "Prednisolone", "Salbutamol"],
        "risk_flags": ["Low oxygen saturation baseline"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=35),
        "labs": [
            {"name": "CO2", "value": 28, "unit": "mmol/L", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
            {"name": "Glucose", "value": 133, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
            {"name": "Creatinine", "value": 1.0, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=3)},
        ],
        "imaging_history": [
            {
                "modality": "Chest X-Ray",
                "summary": "Hyperinflation pattern without new focal change",
                "confidence": 0.87,
                "captured_at": REFERENCE_NOW - timedelta(hours=14),
            }
        ],
    },
    {
        "patient_id": 2112,
        "mrn": "NP-2112",
        "name": "Suraj Maharjan",
        "age": 44,
        "sex": "Male",
        "city": "Chitwan",
        "care_unit": "Observation",
        "diagnosis": "Renal function review",
        "vitals": {
            "heart_rate": 84,
            "respiratory_rate": 17,
            "systolic_bp": 134,
            "temperature_c": 36.7,
            "oxygen_saturation": 97,
            "pain_score": 1,
        },
        "medications": ["Losartan", "Amlodipine"],
        "risk_flags": ["Creatinine trend follow-up"],
        "last_updated": REFERENCE_NOW - timedelta(minutes=58),
        "labs": [
            {"name": "Creatinine", "value": 1.6, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=6)},
            {"name": "Glucose", "value": 108, "unit": "mg/dL", "collected_at": REFERENCE_NOW - timedelta(hours=6)},
            {"name": "Sodium", "value": 139, "unit": "mmol/L", "collected_at": REFERENCE_NOW - timedelta(hours=6)},
        ],
        "imaging_history": [
            {
                "modality": "Renal Ultrasound",
                "summary": "No acute obstructive pattern on review",
                "confidence": 0.84,
                "captured_at": REFERENCE_NOW - timedelta(days=2),
            }
        ],
    },
]


IMAGE_SPECS = [
    {
        "filename": "nepali_clear_demo.png",
        "description": "Synthetic low-anomaly chest-style image for a routine upload test.",
        "opacities": [],
        "nodules": [],
        "format": "PNG",
    },
    {
        "filename": "nepali_opacity_demo.png",
        "description": "Synthetic review-style chest image with right lower lung opacity markers.",
        "opacities": [(350, 300, 54, 185), (316, 350, 34, 178), (292, 245, 24, 170)],
        "nodules": [],
        "format": "PNG",
    },
    {
        "filename": "nepali_nodule_demo.jpg",
        "description": "Synthetic review-style chest image with a focal upper-lung density.",
        "opacities": [],
        "nodules": [(194, 182, 20, 196)],
        "format": "JPEG",
    },
    {
        "filename": "nepali_bilateral_demo.png",
        "description": "Synthetic bilateral haze pattern for respiratory review demos.",
        "opacities": [(186, 266, 42, 176), (326, 272, 46, 182), (258, 338, 32, 168)],
        "nodules": [],
        "format": "PNG",
    },
    {
        "filename": "nepali_edema_demo.png",
        "description": "Synthetic diffuse interstitial pattern for triage testing.",
        "opacities": [(202, 228, 28, 170), (314, 232, 28, 170), (258, 308, 56, 178)],
        "nodules": [],
        "format": "PNG",
    },
    {
        "filename": "nepali_followup_demo.jpg",
        "description": "Synthetic follow-up image with a small resolving focal density.",
        "opacities": [(338, 256, 26, 172)],
        "nodules": [(208, 168, 14, 188)],
        "format": "JPEG",
    },
    {
        "filename": "nepali_portable_demo.png",
        "description": "Synthetic portable scan style image with subtle lower-zone review markers.",
        "opacities": [(320, 356, 28, 168), (200, 362, 22, 164)],
        "nodules": [],
        "format": "PNG",
    },
    {
        "filename": "nepali_triage_demo.jpg",
        "description": "Synthetic triage image with multifocal review-worthy densities.",
        "opacities": [(188, 240, 34, 178), (330, 206, 30, 182), (286, 332, 40, 188)],
        "nodules": [(238, 184, 16, 194)],
        "format": "JPEG",
    },
]


def latest_lab_value(patient: dict, name: str) -> str:
    matches = [lab for lab in patient["labs"] if lab["name"].lower() == name.lower()]
    return str(matches[-1]["value"]) if matches else ""


def write_json() -> Path:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": REFERENCE_NOW.isoformat(),
        "synthetic": True,
        "source_note": "Synthetic Nepali-style demo records for product testing only.",
        "patients": [
            {
                **patient,
                "last_updated": patient["last_updated"].isoformat(),
                "labs": [{**lab, "collected_at": lab["collected_at"].isoformat()} for lab in patient["labs"]],
                "imaging_history": [
                    {**item, "captured_at": item["captured_at"].isoformat()} for item in patient["imaging_history"]
                ],
            }
            for patient in PATIENTS
        ],
    }
    target = EXTERNAL_DIR / "nepali_synthetic_patients.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def write_csv() -> Path:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    target = EXTERNAL_DIR / "nepali_synthetic_patients.csv"
    fieldnames = [
        "patient_id",
        "mrn",
        "name",
        "age",
        "sex",
        "city",
        "care_unit",
        "diagnosis",
        "heart_rate",
        "respiratory_rate",
        "systolic_bp",
        "temperature_c",
        "oxygen_saturation",
        "pain_score",
        "glucose",
        "lactate",
        "creatinine",
        "hba1c",
        "medications",
        "risk_flags",
    ]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for patient in PATIENTS:
            writer.writerow(
                {
                    "patient_id": patient["patient_id"],
                    "mrn": patient["mrn"],
                    "name": patient["name"],
                    "age": patient["age"],
                    "sex": patient["sex"],
                    "city": patient["city"],
                    "care_unit": patient["care_unit"],
                    "diagnosis": patient["diagnosis"],
                    "heart_rate": patient["vitals"]["heart_rate"],
                    "respiratory_rate": patient["vitals"]["respiratory_rate"],
                    "systolic_bp": patient["vitals"]["systolic_bp"],
                    "temperature_c": patient["vitals"]["temperature_c"],
                    "oxygen_saturation": patient["vitals"]["oxygen_saturation"],
                    "pain_score": patient["vitals"]["pain_score"],
                    "glucose": latest_lab_value(patient, "Glucose"),
                    "lactate": latest_lab_value(patient, "Lactate"),
                    "creatinine": latest_lab_value(patient, "Creatinine"),
                    "hba1c": latest_lab_value(patient, "HbA1c"),
                    "medications": "; ".join(patient["medications"]),
                    "risk_flags": "; ".join(patient["risk_flags"]),
                }
            )
    return target


def make_scan(opacities: list[tuple[int, int, int, int]], nodules: list[tuple[int, int, int, int]]) -> Image.Image:
    canvas = Image.new("L", (512, 512), 16)
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((88, 42, 424, 470), radius=132, fill=34)
    draw.rectangle((244, 56, 268, 448), fill=78)
    draw.ellipse((118, 88, 238, 428), fill=136)
    draw.ellipse((274, 88, 394, 428), fill=132)
    draw.ellipse((160, 76, 350, 162), fill=68)

    for x, y, radius, tone in opacities:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=tone)
    for x, y, radius, tone in nodules:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=tone)

    noise = Image.effect_noise((512, 512), 12).convert("L")
    canvas = ImageChops.add_modulo(canvas, noise)
    canvas = canvas.filter(ImageFilter.GaussianBlur(radius=1.6))

    rgb = Image.merge("RGB", (canvas, canvas, canvas))
    return rgb


def write_images() -> list[dict[str, str]]:
    IMAGING_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for spec in IMAGE_SPECS:
        image = make_scan(spec["opacities"], spec["nodules"])
        path = IMAGING_DIR / spec["filename"]
        if spec["format"] == "JPEG":
            image.save(path, quality=95)
        else:
            image.save(path)
        manifest.append(
            {
                "filename": spec["filename"],
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "description": spec["description"],
            }
        )
    return manifest


def write_manifest(images: list[dict[str, str]]) -> Path:
    target = EXTERNAL_DIR / "nepali_demo_manifest.json"
    payload = {
        "generated_at": REFERENCE_NOW.isoformat(),
        "synthetic": True,
        "dataset": "ml_pipeline/data/external/nepali_synthetic_patients.json",
        "flat_dataset": "ml_pipeline/data/external/nepali_synthetic_patients.csv",
        "upload_images": images,
        "usage_note": "These assets are synthetic and intended for UI, API, and imaging upload validation.",
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def main() -> None:
    json_path = write_json()
    csv_path = write_csv()
    images = write_images()
    manifest_path = write_manifest(images)

    print(json_path)
    print(csv_path)
    print(manifest_path)
    for image in images:
        print(ROOT / image["path"])


if __name__ == "__main__":
    main()
