# ML Pipeline

## Scope

The ML workspace supports four product tracks:

- ICU deterioration scoring
- chronic disease and sepsis-watch scoring
- imaging triage
- care-plan recommendation

## Data layout

- `ml_pipeline/data/raw`
  Baseline vitals, lab extracts, and imaging examples used for training and validation.

- `ml_pipeline/data/processed`
  Workspace for derived features, split data, and generated intermediate artifacts.

- `ml_pipeline/data/external`
  Synthetic Nepali demo datasets and manifests used for product validation and walkthroughs.

## Demo dataset pack

External demo assets include:

- `nepali_synthetic_patients.json`
- `nepali_synthetic_patients.csv`
- `nepali_demo_manifest.json`
- upload-ready synthetic imaging files under `ml_pipeline/data/raw/imaging/`

Regenerate the external pack with:

```bash
python scripts/generate_nepali_demo_assets.py
```

## Training scripts

- `train_icu.py`
  Trains the ICU deterioration baseline and writes `lstm_icu.pt`

- `train_disease.py`
  Trains the disease-risk model and writes `xgboost_disease.pkl`

- `train_imaging.py`
  Trains the imaging triage model and writes `cnn_imaging.pt`

- `train_treatment.py`
  Trains the care-plan policy artifact and writes `rl_treatment.pt`

The artifact names match the serving contract in the backend runtime, so training refreshes do not require API changes.

## Retraining orchestration

The repository includes:

- Airflow DAGs under `airflow/dags/`
- retraining helpers under `backend/app/workers/retraining.py`
- manifest publication to `ml_pipeline/models/retraining_manifest.json`

The retraining helper layer supports:

- retraining-window planning
- per-model training invocation
- release-gate evaluation
- manifest publication for operational review

## Governance expectations

- store artifact version, owner, and validation state in the model registry
- retain evaluation output alongside each artifact refresh
- review calibration and threshold behavior before release
- use rollback notes and manifest history to document model promotion decisions
- keep synthetic demo data separate from any real clinical data source
