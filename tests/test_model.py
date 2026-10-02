import joblib
import numpy as np
import pytest

from heart.config import FEATURES, TARGET
from heart.evaluate import compute_metrics
from heart.models import build_pipeline, candidate_models
from heart.predict import load_model, predict_records


def test_candidate_models_have_grids():
    models = candidate_models()
    assert len(models) >= 2
    for est, grid in models.values():
        assert grid and all(k.startswith("clf__") for k in grid)


@pytest.mark.parametrize("name", list(candidate_models()))
def test_every_candidate_trains_and_predicts(name, patients):
    est, _ = candidate_models()[name]
    model = build_pipeline(est).fit(patients[FEATURES], patients[TARGET])
    probs = model.predict_proba(patients[FEATURES])[:, 1]
    assert probs.shape == (len(patients),)
    assert ((probs >= 0) & (probs <= 1)).all()


def test_model_beats_chance_on_training_signal(fitted_model, patients):
    probs = fitted_model.predict_proba(patients[FEATURES])[:, 1]
    assert compute_metrics(patients[TARGET], probs >= 0.5, probs)["roc_auc"] > 0.7


def test_compute_metrics_keys_and_perfect_score():
    y = np.array([0, 1, 1, 0])
    m = compute_metrics(y, y, np.array([0.1, 0.9, 0.8, 0.2]))
    assert set(m) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
    assert all(v == 1.0 for v in m.values())


def test_model_round_trips_through_joblib(fitted_model, patients, tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(fitted_model, path)
    loaded = load_model(path)
    X = patients[FEATURES]
    assert np.allclose(loaded.predict_proba(X), fitted_model.predict_proba(X))


def test_predict_records_shape_and_confidence(fitted_model, sample_patient):
    missing = {**sample_patient, "ca": None, "thal": None}
    results = predict_records(fitted_model, [sample_patient, missing])
    assert len(results) == 2
    for r in results:
        assert r["prediction"] in (0, 1)
        assert r["label"] in ("disease", "no_disease")
        assert 0.5 <= r["confidence"] <= 1.0
        expected = r["probability_disease"] if r["prediction"] else 1 - r["probability_disease"]
        assert r["confidence"] == pytest.approx(expected, abs=1e-4)


def test_evaluation_plots_are_written(fitted_model, patients, tmp_path):
    from heart.evaluate import plot_confusion, plot_importance, plot_roc
    X, y = patients[FEATURES], patients[TARGET]
    probs = fitted_model.predict_proba(X)[:, 1]
    paths = [
        plot_confusion(y, probs >= 0.5, "cm", tmp_path / "cm.png"),
        plot_roc(y, probs, "roc", tmp_path / "roc.png"),
        plot_importance(fitted_model, tmp_path / "imp.png"),
    ]
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)
