import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from heart.config import BINARY, CATEGORICAL, NUMERIC

ENGINEERED = ["hr_reserve", "chol_per_age"]


class ClinicalFeatures(BaseEstimator, TransformerMixin):
    # Nothing to learn; only remember the input column names.
    def fit(self, X, y=None):
        self.feature_names_in_ = np.array(pd.DataFrame(X).columns)
        return self

    # Add % of age-predicted max heart rate reached and cholesterol per year of age.
    def transform(self, X):
        X = pd.DataFrame(X).copy()
        X["hr_reserve"] = X["thalach"] / (220 - X["age"])
        X["chol_per_age"] = X["chol"] / X["age"]
        return X

    # Report output column names so the pipeline can expose feature names.
    def get_feature_names_out(self, input_features=None):
        base = self.feature_names_in_ if input_features is None else input_features
        return np.array(list(base) + ENGINEERED)


# Build the full preprocessing chain: derived features, imputation, scaling, one-hot.
def build_preprocessor() -> Pipeline:
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    columns = ColumnTransformer([
        ("num", numeric, NUMERIC + ENGINEERED),
        ("bin", SimpleImputer(strategy="most_frequent"), BINARY),
        ("cat", categorical, CATEGORICAL),
    ])
    return Pipeline([("clinical", ClinicalFeatures()), ("columns", columns)])
