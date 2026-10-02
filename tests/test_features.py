import numpy as np
import pandas as pd

from heart.config import FEATURES
from heart.features import ENGINEERED, ClinicalFeatures, build_preprocessor


def test_clinical_features_adds_ratios(patients):
    out = ClinicalFeatures().fit_transform(patients[FEATURES])
    assert set(ENGINEERED) <= set(out.columns)
    row = patients.iloc[0]
    assert np.isclose(out["hr_reserve"].iloc[0], row["thalach"] / (220 - row["age"]))
    assert np.isclose(out["chol_per_age"].iloc[0], row["chol"] / row["age"])


def test_clinical_features_does_not_mutate_input(patients):
    X = patients[FEATURES].copy()
    ClinicalFeatures().fit_transform(X)
    assert list(X.columns) == FEATURES


def test_preprocessor_output_has_no_missing_values(patients):
    out = build_preprocessor().fit_transform(patients[FEATURES])
    assert out.shape[0] == len(patients)
    assert not np.isnan(np.asarray(out, dtype=float)).any()


def test_preprocessor_scales_numeric_columns(patients):
    prep = build_preprocessor().fit(patients[FEATURES])
    names = list(prep.get_feature_names_out())
    out = pd.DataFrame(np.asarray(prep.transform(patients[FEATURES])), columns=names)
    assert abs(out["num__age"].mean()) < 1e-6
    assert abs(out["num__age"].std(ddof=0) - 1) < 1e-6


def test_preprocessor_ignores_unseen_category(patients):
    prep = build_preprocessor().fit(patients[FEATURES])
    odd = patients[FEATURES].head(1).copy()
    odd["thal"] = 5.0
    assert prep.transform(odd).shape[1] == prep.transform(patients[FEATURES].head(1)).shape[1]
