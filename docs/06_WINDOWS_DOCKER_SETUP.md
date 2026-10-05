# Windows setup and execution guide

This guide is the Windows path for the Heart Disease Risk Prediction MLOps assignment. It uses **PowerShell**, **Docker Desktop**, **Docker Compose**, **Minikube with the Docker driver**, and **kubectl**.

Use this guide from the root of the cloned repository. Commands are written for PowerShell, not Git Bash.

## 1. What you will install

| Tool | Purpose |
|---|---|
| Git for Windows | Clone the repository and create commits |
| Python 3.12 | Run tests, notebooks, training and smoke tests |
| Docker Desktop | Build and run the API and monitoring containers |
| Minikube | Run the local Kubernetes cluster |
| kubectl | Apply and inspect Kubernetes resources |
| Optional: VS Code | Edit notebooks, YAML and Markdown |
| Optional: OBS Studio | Record the assignment demonstration video |

Install these tools before starting:

- [Git for Windows](https://git-scm.com/download/win)
- [Python 3.12](https://www.python.org/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl for Windows](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)
- [VS Code](https://code.visualstudio.com/) (optional)
- [OBS Studio](https://obsproject.com/) (optional)

During Python installation, enable **Add python.exe to PATH**. After installing Minikube or kubectl, close and reopen PowerShell.

## 2. Verify the Windows installation

Start Docker Desktop and wait until it reports that Docker is running. Then open a new PowerShell window and run:

```powershell
git --version
py -3.12 --version
py -m pip --version
docker --version
docker compose version
minikube version
kubectl version --client
```

Expected results are Python 3.12.x, a Docker Engine version, Docker Compose v2.x, a Minikube version and a kubectl client version.

If a command is not recognized, restart PowerShell first. If it still fails, add the relevant installation directory to the Windows PATH and reopen PowerShell.

## 3. Clone the repository

Replace the URL with the actual public repository URL:

```powershell
Set-Location $HOME
git clone https://github.com/Kush-munot/heart-disease-mlops.git
Set-Location .\heart-disease-mlops
git status
Get-ChildItem
```

The repository root should contain `Dockerfile`, `compose.yaml`, `heart`, `api`, `models`, `scripts`, `k8s` and `docs`.

All remaining commands in this document assume the current directory is the repository root:

```powershell
Set-Location "$HOME\heart-disease-mlops"
```

### Recommended one-command Kubernetes path

After Docker Desktop is running and the repository is open, the launcher performs the complete deployment in the correct order:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_all.ps1
```

It builds and loads the image, starts Minikube, enables Ingress and metrics-server, applies the Kubernetes resources, waits for the API, Prometheus, and Grafana deployments, and starts the tunnel and port-forwards. Use `-Mode compose` when you want the Docker Compose stack instead of Kubernetes. Do not run both modes together because they use the same local ports.

## 4. Prepare Python locally

The container already contains the serving dependencies. A local Python environment is only needed for tests, training, notebooks and the smoke test.

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, allow scripts for the current user and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Confirm that the virtual environment is active:

```powershell
python --version
python -c "import sklearn, fastapi, mlflow; print('Python dependencies are ready')"
```

## 5. Run the local tests and training

Run the tests and lint checks before building the image:

```powershell
python -m pytest -v --cov=heart --cov=api
python -m flake8 heart api tests scripts
```

If the trained model is not present or you want to regenerate it, run the project modules directly. This is the PowerShell equivalent of the Unix `make data eda train` target:

```powershell
python -m heart.data
python -m heart.eda
python -m heart.train
```

The container requires these files:

```powershell
Test-Path .\models\model.joblib
Test-Path .\models\metadata.json
```

Both commands should return `True` before building the image.

## 6. Build and run the API with Docker

Build the image using the same tag referenced by the Kubernetes manifests:

```powershell
docker build -t localhost/heart-api:local .
docker image ls localhost/heart-api
```

Run the API in the background. The host port is bound to loopback so it is available only on this Windows machine:

```powershell
docker run --rm -d `
  --name heart-api `
  -p 127.0.0.1:8000:8000 `
  localhost/heart-api:local
```

Check the container and health endpoint:

```powershell
docker ps
docker logs heart-api
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
Invoke-WebRequest http://127.0.0.1:8000/model-info | Select-Object -ExpandProperty Content
```

Run the repository smoke test from another PowerShell window, or from the same window while the container is running:

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\smoke_test.py --url http://127.0.0.1:8000
```

The smoke test checks health, both sample predictions, invalid input handling and the Prometheus metrics endpoint. It should end with:

```text
smoke test passed
```

Open the API documentation in a browser:

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>
- Metrics: <http://127.0.0.1:8000/metrics>

Stop the API when finished with the standalone test:

```powershell
docker stop heart-api
```

## 7. Run the local monitoring stack with Docker Compose

The Compose file starts the API, Prometheus and Grafana. Set a password for the Grafana admin account in the current PowerShell session:

```powershell
$env:GRAFANA_PASSWORD = "choose-a-password"
docker compose up -d
docker compose ps
```

Check the service logs:

```powershell
docker compose logs api
docker compose logs prometheus
docker compose logs grafana
```

Open these pages:

| Service | URL | Login |
|---|---|---|
| API Swagger UI | <http://127.0.0.1:8000/docs> | none |
| Prometheus | <http://127.0.0.1:9090> | none |
| Grafana | <http://127.0.0.1:3000> | `admin` / value of `$env:GRAFANA_PASSWORD` |

Generate API traffic so that the Grafana panels contain data:

```powershell
python .\scripts\generate_traffic.py --url http://127.0.0.1:8000 --count 300
```

In Prometheus, open **Status > Targets** and confirm that the API target is UP. In Grafana, open the provisioned **Heart Disease API** dashboard.

Capture the monitoring screenshots required by the assignment before stopping the stack. Then stop it with:

```powershell
docker compose down
```

To remove the named API container if you ran the standalone Docker command earlier:

```powershell
docker rm -f heart-api 2>$null
```

## 8. Start Minikube with Docker Desktop

Make sure Docker Desktop is running. Start a Minikube cluster with the Docker driver:

```powershell
minikube start --driver=docker --cpus=2 --memory=4096
minikube status
kubectl get nodes
```

The node should show `Ready`.

Enable the nginx Ingress controller and metrics server:

```powershell
minikube addons enable ingress
minikube addons enable metrics-server
kubectl get pods -n ingress-nginx
```

Wait until the Ingress controller is ready:

```powershell
kubectl wait --namespace ingress-nginx `
  --for=condition=Ready pod `
  --selector=app.kubernetes.io/component=controller `
  --timeout=180s
```

If the selector does not match your installed Minikube version, inspect the namespace and wait for the controller pod shown there:

```powershell
kubectl get pods -n ingress-nginx -o wide
kubectl get ingressclass
```

## 9. Load the image into Minikube

The Kubernetes Deployment uses `imagePullPolicy: Never`, so Kubernetes must be able to find the image in Minikube's image store. The verified Windows method is to build with Docker Desktop and load the image explicitly:

```powershell
docker build -t localhost/heart-api:local .
minikube image load localhost/heart-api:local
minikube image ls | Select-String "heart-api"
```

The output should contain `localhost/heart-api:local`.

Alternatively, Minikube can build the image directly:

```powershell
docker build -t localhost/heart-api:local .
docker save -o .\heart-api.tar localhost/heart-api:local
minikube image load .\heart-api.tar
Remove-Item .\heart-api.tar
minikube image ls | Select-String "heart-api"
```

## 10. Deploy the API to Kubernetes

The repository's `k8s/deploy.sh` is a Bash script. Do not run it from ordinary PowerShell. Run the equivalent commands below instead.

Create the namespace and apply the API resources:

```powershell
kubectl apply -f .\k8s\namespace.yaml
kubectl apply -f .\k8s\deployment.yaml
kubectl apply -f .\k8s\service.yaml
```

Create the monitoring ConfigMaps and Grafana Secret. Replace the password with the same password you want to use for the Grafana login:

```powershell
$grafanaPassword = "choose-a-password"

kubectl -n heart-ml create configmap grafana-datasources `
  --from-file=datasource.yml=.\monitoring\grafana\provisioning\datasources\datasource.yml `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n heart-ml create configmap grafana-dashboard-provider `
  --from-file=dashboard.yml=.\monitoring\grafana\provisioning\dashboards\dashboard.yml `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n heart-ml create configmap grafana-dashboards `
  --from-file=heart-api.json=.\monitoring\grafana\dashboards\heart-api.json `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n heart-ml create secret generic grafana-admin `
  --from-literal=password=$grafanaPassword `
  --dry-run=client -o yaml | kubectl apply -f -
```

Apply Prometheus and Grafana:

```powershell
kubectl apply -f .\k8s\monitoring\
kubectl apply -f .\k8s\ingress.yaml
```

Wait for all workloads:

```powershell
kubectl -n heart-ml rollout status deployment/heart-api --timeout=180s
kubectl -n heart-ml rollout status deployment/prometheus --timeout=180s
kubectl -n heart-ml rollout status deployment/grafana --timeout=180s
kubectl -n heart-ml get pods,svc,ingress -o wide
```

Expected API state:

- Two `heart-api` pods are `Running` and `2/2` or `1/1` Ready, depending on the displayed container count.
- The `heart-api` Service exists as a `LoadBalancer` on port 8000.
- Prometheus and Grafana pods are Running.
- The `heart-api` Ingress has host `heart.local`.

## 11. Verify the Kubernetes deployment

First inspect the resources and events if anything is not ready:

```powershell
kubectl -n heart-ml get all,ingress
kubectl -n heart-ml describe deployment heart-api
kubectl -n heart-ml get events --sort-by=.lastTimestamp
kubectl -n heart-ml logs -l app=heart-api --tail=50 --prefix
```

### 11.1 LoadBalancer access

Run this in a separate **Administrator PowerShell** window and leave it running:

```powershell
minikube tunnel
```

In the project PowerShell window, wait for the external address:

```powershell
kubectl -n heart-ml get service heart-api -w
```

When the `EXTERNAL-IP` is assigned, use the address shown by Windows. If the Docker driver does not provide a usable external address, use the reliable local fallback:

```powershell
kubectl -n heart-ml port-forward service/heart-api 8000:8000
```

Keep port forwarding running and test from another PowerShell window:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
python .\scripts\smoke_test.py --url http://127.0.0.1:8000
```

For assignment evidence, capture `kubectl get service`, the running tunnel or port-forward terminal, and a successful API request.

### 11.2 Ingress access through `heart.local`

Get the Minikube IP:

```powershell
$minikubeIp = minikube ip
$minikubeIp
```

Open **Notepad as Administrator**, open:

```text
C:\Windows\System32\drivers\etc\hosts
```

Add this line, replacing the address with the value printed by `minikube ip`:

```text
192.168.49.2 heart.local
```

Do not add the line a second time if it already exists. Verify name resolution:

```powershell
Resolve-DnsName heart.local
```

Test the Ingress:

```powershell
Invoke-WebRequest http://heart.local/health | Select-Object -ExpandProperty Content
python .\scripts\smoke_test.py --url http://heart.local
```

Open <http://heart.local/docs> for Swagger UI. If the Ingress returns 404, check that the request uses the `heart.local` host and that the nginx controller is ready:

```powershell
kubectl get ingressclass
kubectl -n heart-ml get ingress
kubectl -n ingress-nginx get pods
```

If editing the Windows hosts file is not permitted, test the same Ingress route with an explicit Host header:

```powershell
Invoke-WebRequest http://127.0.0.1/health -Headers @{ Host = 'heart.local' } | Select-Object -ExpandProperty Content
```

The API port-forward at `http://127.0.0.1:8000/docs` is the reliable Swagger URL for the local demonstration.

## 12. Access Kubernetes monitoring

Port-forward Prometheus and Grafana in separate PowerShell windows:

```powershell
kubectl -n heart-ml port-forward service/prometheus 9090:9090
```

```powershell
kubectl -n heart-ml port-forward service/grafana 3000:3000
```

Open:

- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000>

Log in to Grafana with:

```text
Username: admin
Password: the value assigned to $grafanaPassword during deployment
```

Generate traffic through the forwarded API or Ingress while the monitoring port-forwards are running:

```powershell
python .\scripts\generate_traffic.py --url http://127.0.0.1:8000 --count 300
```

In Prometheus, check **Status > Targets**. In Grafana, open the **Heart Disease API** dashboard and wait for the panels to refresh.

View JSON application logs from both API replicas:

```powershell
kubectl -n heart-ml logs -l app=heart-api --prefix --tail=100
```

## 13. Rolling update demonstration

The Deployment is configured with `maxUnavailable: 0`. Demonstrate a rolling restart and verify that it completes:

```powershell
kubectl -n heart-ml rollout restart deployment/heart-api
kubectl -n heart-ml rollout status deployment/heart-api --timeout=180s
kubectl -n heart-ml get pods -w
```

In another window, continue requesting the health endpoint while the rollout runs:

```powershell
while ($true) {
  try {
    $response = Invoke-WebRequest http://heart.local/health -TimeoutSec 5
    Write-Host (Get-Date -Format T) $response.StatusCode
  } catch {
    Write-Host (Get-Date -Format T) $_.Exception.Message
  }
  Start-Sleep -Seconds 2
}
```

Press `Ctrl+C` to stop the loop.

## 14. Evidence checklist for the submission

Capture screenshots after the relevant command succeeds:

1. `docker build` completed and the image is listed.
2. Standalone container health and `python scripts/smoke_test.py` output.
3. Swagger UI executing `/predict`.
4. Docker Compose services showing API, Prometheus and Grafana running.
5. Prometheus Targets page showing the API target UP.
6. Grafana dashboard after generated traffic.
7. `minikube status` and `kubectl get nodes`.
8. `kubectl -n heart-ml get pods,svc,ingress -o wide`.
9. API pod description showing probes and resource limits.
10. LoadBalancer or port-forward request returning a successful health response.
11. Ingress request through `http://heart.local/health`.
12. Kubernetes Swagger UI executing `/predict`.
13. Kubernetes Prometheus and Grafana pages.
14. Kubernetes JSON logs showing prediction requests.
15. Rolling update status.

Save screenshots under the repository's `screenshots` directory using the filenames in `screenshots/README.md`.

## 15. Common Windows problems

| Problem | Fix |
|---|---|
| `docker` is not recognized | Start Docker Desktop, reopen PowerShell, then rerun `docker --version`. |
| Docker daemon connection error | Docker Desktop is not ready; wait for the whale icon to become healthy. |
| PowerShell says script execution is disabled | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate `.venv` again. |
| `ErrImageNeverPull` | Run `minikube image build -t localhost/heart-api:local .` or load the saved image into Minikube. |
| API pod is `CrashLoopBackOff` | Run `kubectl -n heart-ml logs <pod-name> --previous`; confirm `models/model.joblib` was present when the image was built. |
| API pod is Running but not Ready | Check `/health` through the pod logs; the model may not have loaded. |
| Service `EXTERNAL-IP` remains pending | Keep `minikube tunnel` running as Administrator, or use `kubectl port-forward service/heart-api 8000:8000`. |
| Ingress returns 404 | Confirm the `heart.local` hosts entry, `kubectl get ingressclass`, and the `heart-ml` Ingress resource. |
| `kubectl apply -f k8s/monitoring/` fails | Run the command from the repository root and confirm the path uses backslashes in PowerShell. |
| Grafana login fails | Use `admin` and the exact value assigned to `$grafanaPassword`; recreate the `grafana-admin` Secret if needed. |
| Port 8000, 9090 or 3000 is busy | Run `docker ps`, stop the conflicting process/container, or choose a different local port for port-forwarding. |
| `make` is not recognized | This guide does not require Make. Use the PowerShell equivalents in each section. |
| `bash k8s/deploy.sh` fails | The script is for Unix-like shells. Use the manual ConfigMap, Secret and `kubectl apply` commands in section 10. |

## 16. Clean up after the demonstration

Delete the Kubernetes namespace and stop Minikube:

```powershell
kubectl delete namespace heart-ml --ignore-not-found
minikube stop
```

Delete the cluster only when you no longer need its images or evidence:

```powershell
minikube delete
```

Stop the local Compose stack if it is still running:

```powershell
docker compose down
```

The API has no authentication and is intended for local or cluster-internal use. Do not expose it publicly without adding authentication and an appropriate network boundary.
