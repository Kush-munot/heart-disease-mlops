# 2. External tools: install and configure

The verified local workflow uses Windows PowerShell, Docker Desktop, Minikube with the Docker driver, and kubectl. macOS/Linux alternatives are included where useful.

| Tool | Required? | Used for |
|---|---|---|
| Python 3.12 | yes | code, training, tests |
| Git + GitHub account | yes | repo, Actions |
| GitHub CLI `gh` | optional | create repo, watch runs from terminal |
| Docker Desktop | yes for the verified Windows workflow | build/run containers and Compose |
| Podman | optional | alternative container engine |
| Docker Compose v2 | included with Docker Desktop | one-command local monitoring stack |
| Minikube | yes (for task 7) | local Kubernetes cluster |
| kubectl | yes (for task 7) | apply manifests |
| MLflow | installed via pip | experiment tracking |
| Prometheus + Grafana | pulled as containers | monitoring |
| Screen recorder | yes | pipeline video |

## 2.1 Python 3.12
```powershell
py -3.12 --version
docker --version
docker compose version
minikube version
kubectl version --client
```
Windows: install Python from https://www.python.org/downloads/ and tick "Add to PATH" if local training is required. Docker Desktop includes Docker Compose.

## 2.2 Git, GitHub and gh
Install Git for Windows and optionally GitHub CLI. Then configure Git from PowerShell:
```powershell
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
gh auth login                        # choose GitHub.com, HTTPS, login with browser
```
Create and push the repo:
```powershell
git init -b main
git add .
git commit -m "Heart disease MLOps pipeline"
gh repo create heart-disease-mlops --public --source . --push
```
Without `gh`: create an empty repo on github.com, then run `git remote add origin https://github.com/<user>/heart-disease-mlops.git && git push -u origin main`.

## 2.3 Docker Desktop (recommended on Windows)
```powershell
docker --version
docker compose version
docker run --rm hello-world
```

Docker Desktop must be running before Docker or Minikube commands are used. The project image is tagged `localhost/heart-api:local` because that is the tag referenced by the Kubernetes Deployment.

Podman remains a valid alternative on macOS/Linux:
```bash
brew install podman
podman machine init --cpus 4 --memory 8192 --disk-size 40
podman machine start
podman run --rm quay.io/podman/hello
```
- Podman builds the standard `Dockerfile` unchanged, and `podman` accepts the same flags as `docker`.
- Podman stores the image as `localhost/heart-api:local`, which is why the manifests use that name.
- The `HEALTHCHECK` instruction only applies with `--format docker` (`podman build --format docker ...`). Kubernetes uses its own probes, so this does not matter there.
- Docker Desktop: https://www.docker.com/products/docker-desktop/

Compose, for the local monitoring stack:
```powershell
docker compose up -d
```

## 2.4 Minikube and kubectl
```powershell
minikube version
kubectl version --client
minikube start --driver=docker --cpus=2 --memory=4096
minikube addons enable ingress
minikube addons enable metrics-server
```
Linux: https://minikube.sigs.k8s.io/docs/start/ and https://kubernetes.io/docs/tasks/tools/.

Minikube's Podman driver needs a **rootful** Podman machine:
```bash
podman machine stop
podman machine set --rootful --cpus 4 --memory 8192
podman machine start
minikube start --driver=podman --container-runtime=cri-o --cpus=2 --memory=4096
minikube addons enable ingress
minikube addons enable metrics-server
kubectl get nodes
```
- With Docker Desktop: `minikube start --driver=docker`.
- With Docker Desktop's built-in Kubernetes: enable it in Settings -> Kubernetes, then run `kubectl config use-context docker-desktop`.
- With kind on Podman: `brew install kind`, then `KIND_EXPERIMENTAL_PROVIDER=podman kind create cluster --name heart`.

The full deployment walk-through is in [04_DEPLOYMENT.md](04_DEPLOYMENT.md).

## 2.5 MLflow
MLflow is installed by `pip install -r requirements.txt`, with no separate server needed. Runs go to the local `./mlruns` file store. On Windows without local Python, use the temporary MLflow Docker command in [01_SETUP.md](01_SETUP.md#111-mlflow-ui).
```powershell
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root .\mlartifacts --host 127.0.0.1 --port 5000
$env:MLFLOW_TRACKING_URI='http://127.0.0.1:5000'
python -m heart.train
```

## 2.6 Prometheus and Grafana
You do not need to install either one. Both run as pinned container images:
- `docker.io/prom/prometheus:v2.54.1`
- `docker.io/grafana/grafana:11.2.2`

`compose.yaml` runs them locally, and `k8s/monitoring/` runs them in the cluster. The Grafana admin user is `admin`, with the password taken from `GRAFANA_PASSWORD`. The verified launcher/demo password is `assignment-demo-2026`.

## 2.7 GitHub Container Registry (GHCR)
The CI pipeline pushes the image to `ghcr.io/<owner>/heart-api` on every push to `main`, using the built-in `GITHUB_TOKEN`, so no secret needs to be created. After the first push:
1. Go to GitHub -> your profile -> Packages -> `heart-api` -> Package settings.
2. Either make the package public, or keep it private and create a pull secret in the cluster (see 04_DEPLOYMENT.md section 4.7).

Pull it locally with `docker pull ghcr.io/<owner>/heart-api:latest`.

## 2.8 Screen recording
- macOS: QuickTime Player -> File -> New Screen Recording, or press `Cmd+Shift+5`.
- Cross-platform: OBS Studio (https://obsproject.com).

Suggested video flow (60-90 seconds):
1. Show the repository and run `.\scripts\start_all.ps1`.
2. Execute one prediction in Swagger.
3. Show Kubernetes pods, Prometheus targets, and the Grafana dashboard.
4. Show the MLflow experiment and registered model.
5. Mention that CI runs lint, tests, training, and the container smoke test.
