# Screenshots checklist

Save the images here with these names so the report can reference them. The repository currently contains the checklist but not the runtime PNG files.

| File | What to capture | Guide |
|---|---|---|
| `01_mlflow_experiments.png` | MLflow experiment with parent + 3 nested runs | docs/01_SETUP.md 1.4 |
| `02_mlflow_compare.png` | comparison of the 3 model runs | docs/01_SETUP.md 1.11 |
| `03_mlflow_artifacts.png` | one run's evaluation artifacts | docs/01_SETUP.md 1.11 |
| `04_mlflow_registry.png` | registered model versions | docs/01_SETUP.md 1.11 |
| `05_pytest.png` | `python -m pytest` output | docs/01_SETUP.md 1.5 |
| `06_actions_green.png` | 4 green jobs | docs/03_GITHUB_ACTIONS.md |
| `07_actions_summary.png` | training job summary table | 03 |
| `08_actions_artifacts.png` | artifacts list | 03 |
| `09_actions_failed.png` | deliberately failing PR | 03 section 3.5 |
| `10_container_smoke.png` | `docker build` + smoke test | docs/04_DEPLOYMENT.md 4.2 |
| `11_k8s_resources.png` | `kubectl -n heart-ml get all,ingress` | docs/04_DEPLOYMENT.md 4.5 |
| `12_k8s_predict_lb.png` | PowerShell prediction through LoadBalancer/port-forward | docs/04_DEPLOYMENT.md 4.6 |
| `13_k8s_ingress.png` | PowerShell request through the `heart.local` Host header | docs/04_DEPLOYMENT.md 4.6 |
| `14_swagger.png` | `/docs` executing a prediction | docs/01_SETUP.md 1.6 |
| `15_prometheus_targets.png` | targets UP | docs/05_MONITORING.md |
| `16_grafana_dashboard.png` | dashboard with traffic | 05 |
| `17_json_logs.png` | request logs in terminal | 05 |
