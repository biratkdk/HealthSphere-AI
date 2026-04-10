# Model Artifacts

This directory stores the active model artifacts referenced by the backend model registry.

- `lstm_icu.pt`: ICU deterioration model artifact
- `xgboost_disease.pkl`: disease risk model artifact
- `cnn_imaging.pt`: imaging triage model artifact
- `rl_treatment.pt`: treatment recommendation policy artifact

The committed files are compact demo artifacts that keep the backend registry and prediction paths functional out of the box. Run the training scripts to regenerate them with updated artifacts when you want to refresh the packaged model set.
