from pathlib import Path

import joblib
import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression


ROOT = Path(__file__).resolve().parents[1]
image_dir = ROOT / "data" / "raw" / "imaging"


def extract_features(path: Path) -> list[float]:
    with Image.open(path) as image:
        resized = image.convert("RGB").resize((32, 32))
        data = np.asarray(resized) / 255.0
    return [
        float(data[:, :, 0].mean()),
        float(data[:, :, 1].mean()),
        float(data[:, :, 2].mean()),
        float(data.std()),
    ]


X: list[list[float]] = []
y: list[int] = []
for path in sorted(image_dir.iterdir()):
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        continue
    label = 1 if path.stem.startswith("review") else 0
    X.append(extract_features(path))
    y.append(label)

if len(set(y)) < 2:
    raise RuntimeError("At least two labeled imaging classes are required.")

model = LogisticRegression(max_iter=400)
model.fit(X, y)

artifact_path = ROOT / "models" / "cnn_imaging.pt"
joblib.dump(model, artifact_path)
print(f"Saved imaging model to {artifact_path}")

