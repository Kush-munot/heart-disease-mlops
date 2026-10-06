# 1. Setup and running locally

This guide describes the verified Windows workflow for the project. Commands use PowerShell and should be run from the repository root.

For detailed Windows troubleshooting, see [06_WINDOWS_DOCKER_SETUP.md](06_WINDOWS_DOCKER_SETUP.md).

## 1.1 What the project does

The project cleans the UCI Cleveland heart-disease data, trains and compares three models, tracks the runs with MLflow, packages the selected model in a FastAPI Docker image, and deploys the service to Kubernetes with Prometheus and Grafana monitoring.

The repository already contains the trained model at models/model.joblib, so the API can be built without retraining.

## 1.2 Prerequisites

| Tool | Purpose |
|---|---|
| Docker Desktop | Builds and runs the API and local monitoring services |
| Minikube | Runs the local Kubernetes cluster |
| kubectl | Applies Kubernetes manifests and checks resources |
| Python 3.12 | Optional for training, tests, linting, and traffic generation |
| Git | Clones and updates the repository |

Check the tools:

~~~powershell
docker --version
docker compose version
minikube version
kubectl version --client
~~~

Start Docker Desktop before using Docker or Minikube. The Docker engine must be running, not only the desktop window.

## 1.3 Clone the repository

~~~powershell
git clone https://github.com/Kush-munot/heart-disease-mlops
Set-Location heart-disease-mlops
~~~

For the existing checkout:

~~~powershell
Set-Location D:\Github\MLOPS
~~~

## 1.4 Optional Python environment

Python is needed for local training and tests. It is not required to run the committed model through Docker.

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
~~~

If PowerShell blocks activation:

~~~powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
~~~

## 1.5 Train and test locally

~~~powershell
python -m heart.data
python -m heart.eda
python -m heart.train
python -m pytest -v --cov=heart --cov=api
python -m flake8 heart api tests scripts
~~~

The commands create the cleaned data, EDA figures, MLflow runs, model files, and metadata. The verified test run completed with 29 passing tests and Flake8 passed.

The current selected model is balanced Logistic Regression. Its CV ROC-AUC is 0.908 and its hold-out ROC-AUC is 0.960.

## 1.6 Build and run the API container

Build the image:

~~~powershell
docker build --progress=plain -t localhost/heart-api:local .
~~~

Run it:

~~~powershell
docker run --rm -d --name heart-api -p 127.0.0.1:8000:8000 localhost/heart-api:local
~~~

Open Swagger at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The health endpoint should return:

~~~json
{"status":"ok","model_name":"logistic_regression"}
~~~

The verified sample results were:

| Sample | Prediction | Label | Disease probability |
|---|---:|---|---:|
| sample_request.json | 1 | disease | 0.8756 |
| sample_request_low_risk.json | 0 | no_disease | 0.069 |

Stop the standalone container:

~~~powershell
docker stop heart-api
~~~

If Python is installed locally, run:

~~~powershell
python scripts/smoke_test.py --url http://127.0.0.1:8000
~~~

## 1.7 Run Docker Compose

Compose starts the API, Prometheus, and Grafana. Do not run Compose at the same time as the Kubernetes port-forwards because both use ports 8000, 9090, and 3000.

~~~powershell
$env:GRAFANA_PASSWORD = 'assignment-demo-2026'
docker compose up -d --build
docker compose ps
~~~

Open:

| Service | URL |
|---|---|
| API Swagger | http://127.0.0.1:8000/docs |
| Prometheus targets | http://127.0.0.1:9090/targets |
| Grafana | http://127.0.0.1:3000 |

Grafana credentials:

~~~text
Username: admin
Password: assignment-demo-2026
~~~

Generate dashboard traffic when Python is installed:

~~~powershell
python scripts/generate_traffic.py --url http://127.0.0.1:8000 --count 300 --delay 0.01
~~~

Stop Compose:

~~~powershell
docker compose down
~~~

## 1.8 Recommended Kubernetes startup

Use the Windows launcher for the full deployment:

~~~powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_all.ps1
~~~

The launcher starts Docker Desktop if needed, builds and loads the image, starts Minikube, enables Ingress and metrics-server, applies the Kubernetes resources, waits for all deployments, starts the tunnel and port-forwards, starts the MLflow UI container, and verifies all four service URLs.

The default mode is Kubernetes. Compose is an alternative:

~~~powershell
.\scripts\start_all.ps1 -Mode compose
~~~

Use one mode at a time.

## 1.9 Manual Kubernetes workflow

Use these commands when the launcher needs troubleshooting:

~~~powershell
minikube start --driver=docker --cpus=2 --memory=4096
minikube addons enable ingress
minikube addons enable metrics-server
docker build -t localhost/heart-api:local .
minikube image load localhost/heart-api:local
kubectl apply -f .\k8s\namespace.yaml
~~~

Create the Grafana ConfigMaps and Secret:

~~~powershell
kubectl -n heart-ml create configmap grafana-datasources --from-file=datasource.yml=.\monitoring\grafana\provisioning\datasources\datasource.yml --dry-run=client -o yaml | kubectl apply -f -
kubectl -n heart-ml create configmap grafana-dashboard-provider --from-file=dashboard.yml=.\monitoring\grafana\provisioning\dashboards\dashboard.yml --dry-run=client -o yaml | kubectl apply -f -
kubectl -n heart-ml create configmap grafana-dashboards --from-file=heart-api.json=.\monitoring\grafana\dashboards\heart-api.json --dry-run=client -o yaml | kubectl apply -f -
kubectl -n heart-ml create secret generic grafana-admin --from-literal=password=assignment-demo-2026 --dry-run=client -o yaml | kubectl apply -f -
~~~

Apply the application and monitoring manifests:

~~~powershell
kubectl apply -f .\k8s\deployment.yaml -f .\k8s\service.yaml
kubectl apply -f .\k8s\monitoring\
kubectl apply -f .\k8s\ingress.yaml
kubectl -n heart-ml rollout status deployment/heart-api --timeout=180s
kubectl -n heart-ml rollout status deployment/prometheus --timeout=180s
kubectl -n heart-ml rollout status deployment/grafana --timeout=180s
~~~

Start these in separate PowerShell windows:

~~~powershell
minikube tunnel
kubectl -n heart-ml port-forward service/heart-api 8000:8000
kubectl -n heart-ml port-forward service/prometheus 9090:9090
kubectl -n heart-ml port-forward service/grafana 3000:3000
~~~

## 1.10 Verify Kubernetes

~~~powershell
minikube status
kubectl get nodes
kubectl -n heart-ml get pods,svc,ingress -o wide
Invoke-WebRequest http://127.0.0.1:8000/health
~~~

Expected state:

- two Ready heart-api pods;
- one Prometheus pod;
- one Grafana pod;
- a heart-api LoadBalancer Service;
- an nginx Ingress for heart.local.

If Windows cannot edit the hosts file, test the Ingress with an explicit Host header:

~~~powershell
Invoke-WebRequest http://127.0.0.1/health -Headers @{ Host = 'heart.local' }
~~~

Generate traffic and inspect the dashboards:

~~~powershell
python scripts/generate_traffic.py --url http://127.0.0.1:8000 --count 300 --delay 0.01
~~~

Prometheus should show both API replicas as UP. Grafana should show request rate, latency, validation errors, prediction mix, total predictions, and model-loaded status.

Demonstrate a rolling update:

~~~powershell
kubectl -n heart-ml rollout restart deployment/heart-api
kubectl -n heart-ml rollout status deployment/heart-api
kubectl -n heart-ml logs -l app=heart-api --prefix --tail=20
~~~

## 1.11 MLflow UI

The launcher starts MLflow automatically at `http://127.0.0.1:5000`. To run it manually instead, use Python and MLflow:

~~~powershell
mlflow ui --backend-store-uri .\mlruns --host 127.0.0.1 --port 5000
~~~

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) and inspect the heart-disease-classification experiment and heart-disease-classifier model.

Without local Python, use a temporary container:

~~~powershell
docker run --rm -d --name mlflow-ui -p 127.0.0.1:5000:5000 -v "$($PWD):/workspace" -w /workspace python:3.12-slim sh -c "python -m pip install -q mlflow==2.17.2 && mlflow ui --backend-store-uri ./mlruns --host 0.0.0.0 --port 5000"
~~~

Stop it when finished:

~~~powershell
docker rm -f mlflow-ui
~~~

## 1.12 Troubleshooting

| Problem | Fix |
|---|---|
| Docker cannot connect | Start Docker Desktop and wait until the engine is Running. |
| Swagger does not open but Prometheus and Grafana do | Restart the API forward: kubectl -n heart-ml port-forward service/heart-api 8000:8000. |
| ErrImageNeverPull | Rebuild the image and run minikube image load localhost/heart-api:local. |
| API pod is Running but not Ready | Inspect kubectl -n heart-ml logs -l app=heart-api. |
| LoadBalancer external IP is pending | Keep minikube tunnel running or use the API port-forward. |
| Ingress returns 404 | Send the Host header heart.local and check the Ingress resource. |
| Port 8000, 9090, or 3000 is busy | Stop the conflicting container or port-forward. |
| Port 5000 is busy | Stop the existing `mlflow-ui` container with `docker rm -f mlflow-ui`. |
| PowerShell blocks the launcher | Run Set-ExecutionPolicy -Scope Process Bypass. |

## 1.13 Clean shutdown

For Kubernetes:

~~~powershell
docker rm -f mlflow-ui 2>$null
minikube stop
~~~

For Compose:

~~~powershell
docker compose down
~~~

To remove the Kubernetes namespace:

~~~powershell
kubectl delete namespace heart-ml --ignore-not-found
~~~

Use minikube delete only when the cluster should be removed and recreated from scratch.
