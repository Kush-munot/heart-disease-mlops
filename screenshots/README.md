# Screenshots checklist

Save the images here with these names so the report can reference them. The repository currently contains the checklist but not the runtime PNG files.

| File | What to capture | Guide |
|---|---|---|
| `01_mlflow_experiments.png` | MLflow experiment with parent + 3 nested runs | docs/01_SETUP.md 1.4 |
| `02_mlflow_compare.png` | comparison of the 3 model runs | docs/01_SETUP.md 1.11 |
| `03_mlflow_artifacts.png` | one run's evaluation artifacts | docs/01_SETUP.md 1.11 |
| `04_mlflow_registry.png` | registered model versions | docs/01_SETUP.md 1.11 |
| `05_pytest.png` | Passing `pytest` output | Windows capture steps below |
| `06_actions_green.png` | 4 green jobs | docs/03_GITHUB_ACTIONS.md |
| `07_actions_summary.png` | training job summary table | 03 |
| `08_actions_artifacts.png` | artifacts list | 03 |
| `09_actions_failed.png` | deliberately failing PR | 03 section 3.5 |
| `10_container_smoke.png` | `docker build` + standalone container smoke test | Windows capture steps below |
| `11_k8s_resources.png` | Kubernetes pods, Services, and Ingress | Windows capture steps below |
| `12_k8s_predict_lb.png` | Prediction through the Kubernetes API port-forward | Windows capture steps below |
| `13_k8s_ingress.png` | Prediction through the `heart.local` Ingress host | Windows capture steps below |
| `14_swagger.png` | `/docs` executing a prediction | docs/01_SETUP.md 1.6 |
| `15_prometheus_targets.png` | targets UP | docs/05_MONITORING.md |
| `16_grafana_dashboard.png` | dashboard with traffic | 05 |
| `17_json_logs.png` | request logs in terminal | 05 |

## Windows capture steps

Run these commands from the repository root:

```powershell
Set-Location D:\Github\MLOPS
```

Start the Kubernetes stack before taking screenshots:

```powershell
.\scripts\start_all.ps1
```

Capture the evidence after each command succeeds. Use `Win + Shift + S` and save each image with the exact filename shown in the table.

### `05_pytest.png`

If pytest is not installed, install the repository dependencies first:

```powershell
python -m pip install -r requirements.txt
```

Run the tests:

```powershell
python -m pytest -v --cov=heart --cov=api
```

The screenshot should show the final passing result, including `29 passed`.

### `10_container_smoke.png`

Use port `8010` so the standalone container does not conflict with the Kubernetes API on port `8000`:

```powershell
docker build -t localhost/heart-api:local
docker rm -f heart-api 2>$null
docker run --rm -d --name heart-api -p 127.0.0.1:8010:8000 localhost/heart-api:local
python .\scripts\smoke_test.py --url http://127.0.0.1:8010
```

Capture the output showing the health response, sample predictions, validation check, and `smoke test passed`. Stop the temporary container afterwards:

```powershell
docker stop heart-api
```

### `11_k8s_resources.png`

```powershell
minikube status
kubectl get nodes
kubectl -n heart-ml get pods,svc,ingress -o wide
kubectl get ingressclass
```

The screenshot should show the Ready node, two API pods, Prometheus, Grafana, the `LoadBalancer` Service, and the `heart.local` Ingress.

### `12_k8s_predict_lb.png`

The launcher creates the API port-forward on port `8000`. Run:

```powershell
kubectl -n heart-ml get svc heart-api
$body = Get-Content .\samples\sample_request.json -Raw
Invoke-RestMethod http://127.0.0.1:8000/predict -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json
```

Capture the Service details and successful prediction JSON. If port `8000` is not forwarded, run this in another PowerShell window and leave it open:

```powershell
kubectl -n heart-ml port-forward service/heart-api 8000:8000
```

### `13_k8s_ingress.png`

This Windows-friendly method sends the `heart.local` host to the Ingress without editing the hosts file:

```powershell
Write-Host "Prediction through heart.local Ingress:"
$headers = @{ Host = "heart.local" }
$body = Get-Content .\samples\sample_request.json -Raw
Invoke-RestMethod http://127.0.0.1/predict -Headers $headers -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json
```

Capture the visible `heart.local` label and successful prediction JSON.
