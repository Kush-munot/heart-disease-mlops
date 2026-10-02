import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from api.schemas import PatientFeatures, PredictionResponse
from heart.predict import load_model, predict_records

MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/model.joblib"))
METADATA_PATH = MODEL_PATH.with_name("metadata.json")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
logger = logging.getLogger("heart-api")

REQUESTS = Counter("api_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("api_request_duration_seconds", "Request latency", ["path"])
PREDICTIONS = Counter("model_predictions_total", "Predictions served", ["label"])
DISEASE_PROB = Histogram("model_disease_probability", "Predicted disease probability",
                         buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
MODEL_LOADED = Gauge("model_loaded", "1 when a model is loaded")

state = {"model": None, "meta": {}}


# Emit one structured JSON log line.
def log_event(**fields) -> None:
    logger.info(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **fields}))


# Load the model and its metadata once at startup.
@asynccontextmanager
async def lifespan(app: FastAPI):
    if MODEL_PATH.exists():
        state["model"] = load_model(MODEL_PATH)
        if METADATA_PATH.exists():
            state["meta"] = json.loads(METADATA_PATH.read_text())
        MODEL_LOADED.set(1)
        log_event(event="model_loaded", path=str(MODEL_PATH),
                  model=state["meta"].get("model_name", "unknown"))
    else:
        log_event(event="model_missing", path=str(MODEL_PATH))
    yield


app = FastAPI(title="Heart Disease Risk API", version="1.0.0", lifespan=lifespan)


# Log every request and record Prometheus counters and latency.
@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    route = request.scope.get("route")
    path = route.path if route else "unmatched"
    REQUESTS.labels(request.method, path, response.status_code).inc()
    LATENCY.labels(path).observe(elapsed)
    if path != "/metrics":
        log_event(event="request", request_id=request_id, method=request.method, path=path,
                  status=response.status_code, latency_ms=round(elapsed * 1000, 2),
                  client=request.client.host if request.client else None)
    response.headers["x-request-id"] = request_id
    return response


# Basic service info.
@app.get("/")
def root():
    return {"service": "heart-disease-risk-api", "docs": "/docs", "predict": "/predict"}


# Liveness/readiness probe used by Docker and Kubernetes.
@app.get("/health")
def health():
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ok", "model_name": state["meta"].get("model_name", "unknown")}


# Return the training metadata of the served model.
@app.get("/model-info")
def model_info():
    return state["meta"]


# Predict heart disease risk for one patient record.
@app.post("/predict", response_model=PredictionResponse)
def predict(patient: PatientFeatures):
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    result = predict_records(state["model"], [patient.model_dump()])[0]
    PREDICTIONS.labels(result["label"]).inc()
    DISEASE_PROB.observe(result["probability_disease"])
    log_event(event="prediction", **result)
    return {
        **result,
        "model_name": state["meta"].get("model_name", "unknown"),
        "model_version": state["meta"].get("trained_at", "unknown"),
    }


# Prometheus scrape endpoint.
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
