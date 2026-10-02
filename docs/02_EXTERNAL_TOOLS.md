# 2. External tools: install and configure

The macOS commands use Homebrew (https://brew.sh). Linux and Windows equivalents follow where they differ.

| Tool | Required? | Used for |
|---|---|---|
| Python 3.12 | yes | code, training, tests |
| Git + GitHub account | yes | repo, Actions |
| GitHub CLI `gh` | optional | create repo, watch runs from terminal |
| Podman (or Docker) | yes | build/run the container |
| podman-compose / docker-compose | optional | one-command local monitoring stack |
| Minikube | yes (for task 7) | local Kubernetes cluster |
| kubectl | yes (for task 7) | apply manifests |
| MLflow | installed via pip | experiment tracking |
| Prometheus + Grafana | pulled as containers | monitoring |
| Screen recorder | yes | pipeline video |

## 2.1 Python 3.12
```bash
brew install python@3.12            # macOS
sudo apt install python3.12 python3.12-venv   # Ubuntu 24.04
python3.12 --version
```
Windows: install from https://www.python.org/downloads/ and tick "Add to PATH".

## 2.2 Git, GitHub and gh
```bash
brew install git gh
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
gh auth login                        # choose GitHub.com, HTTPS, login with browser
```
Create and push the repo:
```bash
git init -b main
git add .
git commit -m "Heart disease MLOps pipeline"
gh repo create heart-disease-mlops --public --source . --push
```
Without `gh`: create an empty repo on github.com, then run `git remote add origin https://github.com/<user>/heart-disease-mlops.git && git push -u origin main`.

## 2.3 Podman (preferred) or Docker
```bash
brew install podman
podman machine init --cpus 4 --memory 8192 --disk-size 40
podman machine start
podman run --rm quay.io/podman/hello
```
- Podman builds the standard `Dockerfile` unchanged, and `podman` accepts the same flags as `docker`.
- Podman stores the image as `localhost/heart-api:local`, which is why the manifests use that name.
- The `HEALTHCHECK` instruction only applies with `--format docker` (`podman build --format docker ...`). Kubernetes uses its own probes, so this does not matter there.
- Docker alternative: install Docker Desktop (https://www.docker.com/products/docker-desktop/) and pass `ENGINE=docker` to the make targets.

Compose, for the local monitoring stack:
```bash
brew install podman-compose        # then: podman compose up -d
# or with Docker Desktop:            docker compose up -d
```

## 2.4 Minikube and kubectl
```bash
brew install minikube kubectl
minikube version && kubectl version --client
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
- With Docker Desktop instead: `minikube start --driver=docker`.
- With Docker Desktop's built-in Kubernetes: enable it in Settings -> Kubernetes, then run `kubectl config use-context docker-desktop`.
- With kind on Podman: `brew install kind`, then `KIND_EXPERIMENTAL_PROVIDER=podman kind create cluster --name heart`.

The full deployment walk-through is in [04_DEPLOYMENT.md](04_DEPLOYMENT.md).

## 2.5 MLflow
MLflow is installed by `pip install -r requirements.txt`, with no separate server needed. Runs go to the local `./mlruns` file store. To use a shared tracking server:
```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts \
              --host 127.0.0.1 --port 5000
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
make train
```

## 2.6 Prometheus and Grafana
You do not need to install either one. Both run as pinned container images:
- `docker.io/prom/prometheus:v2.54.1`
- `docker.io/grafana/grafana:11.2.2`

`compose.yaml` runs them locally, and `k8s/monitoring/` runs them in the cluster. The Grafana admin user is `admin`, with the password taken from the `GRAFANA_PASSWORD` environment variable (default `change-me`). Set your own before recording.

## 2.7 GitHub Container Registry (GHCR)
The CI pipeline pushes the image to `ghcr.io/<owner>/heart-api` on every push to `main`, using the built-in `GITHUB_TOKEN`, so no secret needs to be created. After the first push:
1. Go to GitHub -> your profile -> Packages -> `heart-api` -> Package settings.
2. Either make the package public, or keep it private and create a pull secret in the cluster (see 04_DEPLOYMENT.md section 4.7).

Pull it locally with `podman pull ghcr.io/<owner>/heart-api:latest`.

## 2.8 Screen recording
- macOS: QuickTime Player -> File -> New Screen Recording, or press `Cmd+Shift+5`.
- Cross-platform: OBS Studio (https://obsproject.com).

Suggested video flow (5-8 min):
1. Repo tour.
2. `make data eda train` and the MLflow UI.
3. `make test`.
4. Push, then show the green Actions run and its artifacts.
5. `make image run smoke`.
6. Minikube deploy, `kubectl get all`, and curl through the LoadBalancer and Ingress.
7. Run the traffic generator and show the Grafana dashboard.
