import pytest
from fastapi.testclient import TestClient

import api.app as api_app


@pytest.fixture
def client(model_dir, monkeypatch):
    monkeypatch.setattr(api_app, "MODEL_PATH", model_dir / "model.joblib")
    monkeypatch.setattr(api_app, "METADATA_PATH", model_dir / "metadata.json")
    with TestClient(api_app.app) as c:
        yield c
    api_app.state.update(model=None, meta={})


def test_health_reports_loaded_model(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_name": "test_lr"}


def test_predict_returns_prediction_and_confidence(client, sample_patient):
    r = client.post("/predict", json=sample_patient)
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"] in (0, 1)
    assert 0.5 <= body["confidence"] <= 1
    assert body["model_name"] == "test_lr"
    assert "x-request-id" in r.headers


def test_predict_accepts_missing_optional_fields(client, sample_patient):
    payload = {k: v for k, v in sample_patient.items() if k not in ("ca", "thal")}
    assert client.post("/predict", json=payload).status_code == 200


@pytest.mark.parametrize("field,value", [("age", 5), ("sex", 3), ("cp", 0), ("chol", "high")])
def test_predict_rejects_invalid_input(client, sample_patient, field, value):
    r = client.post("/predict", json={**sample_patient, field: value})
    assert r.status_code == 422


def test_predict_rejects_missing_required_field(client, sample_patient):
    payload = dict(sample_patient)
    payload.pop("age")
    assert client.post("/predict", json=payload).status_code == 422


def test_metrics_exposes_request_and_prediction_counters(client, sample_patient):
    client.post("/predict", json=sample_patient)
    text = client.get("/metrics").text
    assert "api_requests_total" in text
    assert "model_predictions_total" in text
    assert "api_request_duration_seconds_bucket" in text


def test_health_is_503_without_model(tmp_path, monkeypatch):
    monkeypatch.setattr(api_app, "MODEL_PATH", tmp_path / "absent.joblib")
    with TestClient(api_app.app) as c:
        assert c.get("/health").status_code == 503
        assert c.post("/predict", json={}).status_code == 422
