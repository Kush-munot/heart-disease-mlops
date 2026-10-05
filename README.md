# Heart Disease Risk Prediction - End-to-End MLOps

A heart disease classifier trained on the UCI Cleveland dataset and served as a monitored REST API. The repository covers the full path: data acquisition, EDA, experiment tracking, a CI/CD pipeline, container build, and Kubernetes deployment. The verified local workflow uses Windows PowerShell, Docker Desktop, and Minikube with the Docker driver.

| Stage | Tooling |
|---|---|
| Data + EDA | pandas, seaborn (`heart/data.py`, `heart/eda.py`, `notebooks/01_eda.ipynb`) |
| Features + models | scikit-learn Pipeline: Logistic Regression, Random Forest, Gradient Boosting |
| Experiment tracking | MLflow (params, CV + test metrics, plots, models, model registry) |
| Packaging | joblib pipeline + MLflow model, pinned `requirements.txt` |
| Tests + CI/CD | pytest, flake8, GitHub Actions (lint -> test -> train -> container -> GHCR) |
| Serving | FastAPI + uvicorn in a non-root container (`Dockerfile`) |
| Deployment | Kubernetes manifests (Minikube), LoadBalancer Service + nginx Ingress |
| Monitoring | JSON request logs, Prometheus metrics, provisioned Grafana dashboard |

## Results (5-fold stratified CV on 242 training rows, 61-row hold-out test set)

| Model | CV accuracy | CV precision | CV recall | CV F1 | CV ROC-AUC |
|---|---|---|---|---|---|
| **Logistic Regression** (C=0.3, balanced) | **0.847** | **0.879** | **0.783** | **0.824** | **0.908** |
| Random Forest (400 trees, leaf=5) | 0.810 | 0.825 | 0.756 | 0.783 | 0.895 |
| Gradient Boosting (100, lr=0.03, depth 2) | 0.810 | 0.822 | 0.765 | 0.786 | 0.881 |

The selected model scores **ROC-AUC 0.960, accuracy 0.869 and recall 0.929 on the hold-out set**.

## Repository layout

```
heart/                 ML package: config, data, features, models, train, evaluate, predict, eda
api/                   FastAPI app (app.py), request/response schemas, slim runtime requirements
tests/                 pytest suite for data, features, model and API (29 tests)
notebooks/             01_eda, 02_training, 03_inference (executed, outputs stored)
data/raw/              raw UCI file (re-downloadable)
data/processed/        cleaned dataset heart_clean.csv
scripts/               download_data.sh, smoke_test.py, generate_traffic.py, start_all.ps1
samples/               example /predict payloads
models/                trained pipeline + metadata.json (committed; regenerate with python -m heart.train)
reports/figures/       EDA and evaluation plots, model comparison table
monitoring/            Prometheus config, Grafana provisioning + dashboard
k8s/                   namespace, deployment, service, ingress, monitoring stack, deploy.sh
.github/workflows/     ci.yml
docs/                  setup, tools, CI/CD, deployment, monitoring, assignment report
screenshots/           evidence for the report
Dockerfile, compose.yaml, Makefile, requirements.txt
```

## Quick start on Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_all.ps1
```

The launcher builds the Docker image, starts Minikube, deploys the API and monitoring stack, starts the tunnel and port-forwards, and waits for the API health check. Use one deployment mode at a time.

Open:

- Swagger: http://127.0.0.1:8000/docs
- Prometheus: http://127.0.0.1:9090/targets
- Grafana: http://127.0.0.1:3000

The local Grafana credentials are `admin` / `assignment-demo-2026` when using the launcher or the documented Compose command.

For Docker Compose instead of Kubernetes:

```powershell
.\scripts\start_all.ps1 -Mode compose
```

Python is optional for the Docker serving path. To retrain, test, or generate traffic locally, create a Python 3.12 environment and follow [docs/01_SETUP.md](docs/01_SETUP.md).

```powershell
$body = Get-Content .\samples\sample_request.json -Raw
Invoke-RestMethod http://127.0.0.1:8000/predict -Method Post -ContentType 'application/json' -Body $body
```

## Documentation

1. [Setup and running locally](docs/01_SETUP.md)
2. [External tools: install and configure](docs/02_EXTERNAL_TOOLS.md)
3. [CI/CD with GitHub Actions](docs/03_GITHUB_ACTIONS.md)
4. [Container and Kubernetes deployment](docs/04_DEPLOYMENT.md)
5. [Monitoring and logging](docs/05_MONITORING.md)
6. [Assignment report](docs/REPORT.md)

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/predict` | JSON patient record -> `prediction`, `label`, `probability_disease`, `confidence` |
| GET | `/health` | readiness/liveness (503 until the model is loaded) |
| GET | `/model-info` | training metadata of the served model |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Swagger UI |

The API has no authentication. It is meant for local or cluster-internal use, and every host port in this repo binds to `127.0.0.1`. Put an auth layer (API gateway, OAuth2 proxy or API key) in front of it before exposing it publicly.
