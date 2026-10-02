import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from heart.config import FEATURES, TARGET
from heart.models import build_pipeline


# Synthetic but realistic patient frame so tests never depend on the network.
@pytest.fixture(scope="session")
def patients() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 160
    df = pd.DataFrame({
        "age": rng.integers(30, 78, n),
        "sex": rng.integers(0, 2, n),
        "cp": rng.integers(1, 5, n),
        "trestbps": rng.normal(132, 17, n).round(),
        "chol": rng.normal(246, 50, n).round(),
        "fbs": rng.integers(0, 2, n),
        "restecg": rng.integers(0, 3, n),
        "thalach": rng.normal(150, 22, n).round(),
        "exang": rng.integers(0, 2, n),
        "oldpeak": rng.gamma(1.2, 0.9, n).round(1),
        "slope": rng.integers(1, 4, n),
        "ca": rng.integers(0, 4, n).astype(float),
        "thal": rng.choice([3.0, 6.0, 7.0], n),
    })
    risk = (df["cp"] == 4) * 1.2 + df["exang"] + df["oldpeak"] * 0.6 + df["ca"] * 0.5
    df[TARGET] = (risk + rng.normal(0, 0.6, n) > 1.8).astype(int)
    df.loc[:3, "ca"] = np.nan
    df.loc[4:5, "thal"] = np.nan
    return df


# A small fitted pipeline shared by model and API tests.
@pytest.fixture(scope="session")
def fitted_model(patients):
    model = build_pipeline(LogisticRegression(max_iter=1000))
    return model.fit(patients[FEATURES], patients[TARGET])


# Persist the fitted model plus metadata to a temp dir, as training would.
@pytest.fixture(scope="session")
def model_dir(tmp_path_factory, fitted_model):
    path = tmp_path_factory.mktemp("models")
    joblib.dump(fitted_model, path / "model.joblib")
    (path / "metadata.json").write_text(json.dumps({"model_name": "test_lr",
                                                    "trained_at": "test"}))
    return path


@pytest.fixture
def sample_patient() -> dict:
    return {"age": 57, "sex": 1, "cp": 4, "trestbps": 140, "chol": 241, "fbs": 0,
            "restecg": 0, "thalach": 123, "exang": 1, "oldpeak": 0.2, "slope": 2,
            "ca": 0, "thal": 7}
