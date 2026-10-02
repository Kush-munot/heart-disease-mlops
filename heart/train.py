import argparse
import json
import os
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import sklearn
from mlflow.models import infer_signature
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split

from heart.config import (
    EXPERIMENT_NAME, FEATURES, FIGURES_DIR, METADATA_PATH, MODEL_PATH,
    RANDOM_STATE, REGISTERED_MODEL, TEST_SIZE, ROOT,
)
from heart.data import load_clean, split_xy
from heart.evaluate import (
    compute_metrics, plot_confusion, plot_importance, plot_model_comparison, plot_roc,
)
from heart.models import build_pipeline, candidate_models

SCORING = ["accuracy", "precision", "recall", "f1", "roc_auc"]


# Point MLflow at MLFLOW_TRACKING_URI or a local ./mlruns folder.
def setup_mlflow(experiment: str) -> None:
    uri = os.getenv("MLFLOW_TRACKING_URI", (ROOT / "mlruns").as_uri())
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment)


# Grid-search one model with stratified CV and log everything to a nested MLflow run.
def train_one(name, estimator, grid, X_train, y_train, X_test, y_test, folds):
    with mlflow.start_run(run_name=name, nested=True) as run:
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=RANDOM_STATE)
        search = GridSearchCV(
            build_pipeline(estimator), grid, scoring=SCORING, refit="roc_auc",
            cv=cv, n_jobs=-1, return_train_score=True,
        )
        search.fit(X_train, y_train)
        best = search.best_estimator_
        i = search.best_index_
        cv_scores = {m: search.cv_results_[f"mean_test_{m}"][i] for m in SCORING}
        cv_std = {m: search.cv_results_[f"std_test_{m}"][i] for m in SCORING}

        y_prob = best.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)
        test_scores = compute_metrics(y_test, y_pred, y_prob)

        mlflow.set_tags({"model_family": name, "stage": "candidate"})
        mlflow.log_params({k.replace("clf__", ""): v for k, v in search.best_params_.items()})
        mlflow.log_params({"cv_folds": folds, "grid_size": len(search.cv_results_["params"])})
        mlflow.log_metrics({f"cv_{k}": v for k, v in cv_scores.items()})
        mlflow.log_metrics({f"cv_{k}_std": v for k, v in cv_std.items()})
        mlflow.log_metrics({f"test_{k}": v for k, v in test_scores.items()})

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pd.DataFrame(search.cv_results_).to_csv(tmp / "cv_results.csv", index=False)
            plot_confusion(y_test, y_pred, f"{name} - confusion", tmp / "confusion_matrix.png")
            plot_roc(y_test, y_prob, f"{name} - ROC", tmp / "roc_curve.png")
            plot_importance(best, tmp / "feature_importance.png")
            mlflow.log_artifacts(str(tmp), artifact_path="evaluation")

        signature = infer_signature(X_train, best.predict_proba(X_train))
        mlflow.sklearn.log_model(
            best, artifact_path="model", signature=signature, input_example=X_train.head(3),
        )
        print(f"{name:22s} cv_roc_auc={cv_scores['roc_auc']:.4f} "
              f"test_roc_auc={test_scores['roc_auc']:.4f} params={search.best_params_}")
        return {
            "name": name, "run_id": run.info.run_id, "model": best,
            "params": search.best_params_, "cv": cv_scores, "cv_std": cv_std,
            "test": test_scores, "y_pred": y_pred, "y_prob": y_prob,
        }


# Persist the winning pipeline plus a metadata file the API reports back.
def save_best(best: dict, n_train: int, n_test: int) -> None:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best["model"], MODEL_PATH)
    metadata = {
        "model_name": best["name"],
        "mlflow_run_id": best["run_id"],
        "best_params": {k.replace("clf__", ""): v for k, v in best["params"].items()},
        "cv_metrics": {k: round(v, 4) for k, v in best["cv"].items()},
        "test_metrics": {k: round(v, 4) for k, v in best["test"].items()},
        "features": FEATURES,
        "train_rows": n_train,
        "test_rows": n_test,
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))


# Train all candidates, pick the best by CV ROC-AUC, save it and register it in MLflow.
def main(folds: int = 5, experiment: str = EXPERIMENT_NAME, register: bool = True) -> dict:
    setup_mlflow(experiment)
    X, y = split_xy(load_clean())
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE,
    )
    with mlflow.start_run(run_name="model-selection") as parent:
        mlflow.log_params({"train_rows": len(X_train), "test_rows": len(X_test),
                           "test_size": TEST_SIZE, "random_state": RANDOM_STATE})
        results = [
            train_one(name, est, grid, X_train, y_train, X_test, y_test, folds)
            for name, (est, grid) in candidate_models().items()
        ]
        summary = pd.DataFrame({r["name"]: r["cv"] for r in results}).T
        best = max(results, key=lambda r: r["cv"]["roc_auc"])

        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        summary.round(4).to_csv(FIGURES_DIR / "model_comparison.csv")
        plot_model_comparison(summary, FIGURES_DIR / "model_comparison.png")
        plot_confusion(y_test, best["y_pred"], f"Best: {best['name']}",
                       FIGURES_DIR / "best_confusion_matrix.png")
        plot_roc(y_test, best["y_prob"], f"Best: {best['name']}",
                 FIGURES_DIR / "best_roc_curve.png")
        plot_importance(best["model"], FIGURES_DIR / "best_feature_importance.png")

        mlflow.log_artifact(str(FIGURES_DIR / "model_comparison.csv"), "comparison")
        mlflow.log_artifact(str(FIGURES_DIR / "model_comparison.png"), "comparison")
        mlflow.set_tags({"best_model": best["name"], "best_run_id": best["run_id"]})
        mlflow.log_metrics({f"best_test_{k}": v for k, v in best["test"].items()})

        save_best(best, len(X_train), len(X_test))
        mlflow.log_artifact(str(METADATA_PATH), "best_model")
        if register:
            mlflow.register_model(f"runs:/{best['run_id']}/model", REGISTERED_MODEL)
        print(f"\nBest model: {best['name']} (parent run {parent.info.run_id})")
        print(summary.round(4).to_string())
    return best


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and track heart disease classifiers")
    parser.add_argument("--folds", type=int, default=5, help="number of CV folds")
    parser.add_argument("--experiment", default=EXPERIMENT_NAME, help="MLflow experiment name")
    parser.add_argument("--no-register", action="store_true", help="skip model registry step")
    args = parser.parse_args()
    main(folds=args.folds, experiment=args.experiment, register=not args.no_register)
