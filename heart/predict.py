from pathlib import Path

import joblib
import pandas as pd

from heart.config import FEATURES, MODEL_PATH


# Load the persisted preprocessing + model pipeline.
def load_model(path: Path = MODEL_PATH):
    return joblib.load(path)


# Score patient records and return label, disease probability and confidence for each.
def predict_records(model, records: list[dict]) -> list[dict]:
    frame = pd.DataFrame(records, columns=FEATURES).astype(float)
    probs = model.predict_proba(frame)[:, 1]
    results = []
    for p in probs:
        label = int(p >= 0.5)
        results.append({
            "prediction": label,
            "label": "disease" if label else "no_disease",
            "probability_disease": round(float(p), 4),
            "confidence": round(float(p if label else 1 - p), 4),
        })
    return results
