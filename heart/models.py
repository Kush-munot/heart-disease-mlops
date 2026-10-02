from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from heart.config import RANDOM_STATE
from heart.features import build_preprocessor


# Candidate models with the hyper-parameter grid searched for each.
def candidate_models() -> dict:
    return {
        "logistic_regression": (
            LogisticRegression(max_iter=5000, random_state=RANDOM_STATE),
            {
                "clf__C": [0.01, 0.1, 0.3, 1.0, 3.0],
                "clf__class_weight": [None, "balanced"],
            },
        ),
        "random_forest": (
            RandomForestClassifier(random_state=RANDOM_STATE),
            {
                "clf__n_estimators": [200, 400],
                "clf__max_depth": [None, 4, 8],
                "clf__min_samples_leaf": [1, 3, 5],
            },
        ),
        "gradient_boosting": (
            GradientBoostingClassifier(random_state=RANDOM_STATE),
            {
                "clf__n_estimators": [100, 200],
                "clf__learning_rate": [0.03, 0.1],
                "clf__max_depth": [2, 3],
            },
        ),
    }


# Wrap a classifier behind the shared preprocessing so one object goes raw input -> label.
def build_pipeline(classifier) -> Pipeline:
    return Pipeline([("prep", build_preprocessor()), ("clf", classifier)])
