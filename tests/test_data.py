import numpy as np
import pandas as pd

from heart import data
from heart.config import FEATURES, RAW_COLUMNS, TARGET

RAW_LINES = [
    "63.0,1.0,1.0,145.0,233.0,1.0,2.0,150.0,0.0,2.3,3.0,0.0,6.0,0",
    "67.0,1.0,4.0,160.0,286.0,0.0,2.0,108.0,1.0,1.5,2.0,3.0,3.0,2",
    "67.0,1.0,4.0,120.0,229.0,0.0,2.0,129.0,1.0,2.6,2.0,2.0,7.0,1",
    "53.0,0.0,3.0,130.0,197.0,1.0,2.0,152.0,0.0,1.2,3.0,?,3.0,0",
    "67.0,1.0,4.0,120.0,229.0,0.0,2.0,129.0,1.0,2.6,2.0,2.0,7.0,1",
]


def _raw_file(tmp_path):
    path = tmp_path / "raw.data"
    path.write_text("\n".join(RAW_LINES) + "\n")
    return path


def test_load_raw_names_columns_and_marks_missing(tmp_path):
    df = data.load_raw(_raw_file(tmp_path))
    assert list(df.columns) == RAW_COLUMNS
    assert df["ca"].isna().sum() == 1


def test_clean_binarises_target_and_drops_duplicates(tmp_path):
    df = data.clean(data.load_raw(_raw_file(tmp_path)))
    assert len(df) == 4
    assert "num" not in df.columns
    assert set(df[TARGET]) == {0, 1}
    assert df[TARGET].tolist() == [0, 1, 1, 0]


def test_clean_coerces_question_marks_to_nan():
    raw = pd.DataFrame([[50, 1, 2, 120, 200, 0, 0, 160, 0, 1.0, 1, "?", "?", 0]],
                       columns=RAW_COLUMNS)
    df = data.clean(raw)
    assert np.isnan(df.loc[0, "ca"]) and np.isnan(df.loc[0, "thal"])
    assert all(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns)


def test_split_xy_returns_model_features(patients):
    X, y = data.split_xy(patients)
    assert list(X.columns) == FEATURES
    assert y.name == TARGET and len(X) == len(y)


def test_download_uses_cache(tmp_path, monkeypatch):
    cached = _raw_file(tmp_path)
    monkeypatch.setattr(data.urllib.request, "urlretrieve",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network")))
    assert data.download_raw(dest=cached) == cached
