# 5. Monitoring and logging

## 5.1 Request logging

`api/app.py` has one HTTP middleware that writes a structured JSON line for every request (except `/metrics` scrapes) and returns an `x-request-id` header. If the client sends its own `x-request-id`, that value is echoed back:

```json
{"ts": "2026-09-30T06:28:51+0000", "event": "request", "request_id": "4a5627a06a35", "method": "POST",
 "path": "/predict", "status": 200, "latency_ms": 4.13, "client": "10.88.0.2"}
{"ts": "...", "event": "prediction", "prediction": 1, "label": "disease", "probability_disease": 0.8756, "confidence": 0.8756}
```
Other events are `model_loaded` and `model_missing` at startup. Set the log level with `LOG_LEVEL`.

Where to read the logs on Windows:
```powershell
docker logs -f heart-api
kubectl -n heart-ml logs -l app=heart-api -f --prefix
kubectl -n heart-ml logs -l app=heart-api --prefix --tail=100
```
The logs are one JSON object per line, so a log shipper such as Loki/Promtail, Fluent Bit or CloudWatch can parse them without extra configuration.

## 5.2 Metrics exposed at `/metrics`

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `api_requests_total` | counter | method, path, status | request volume and status codes |
| `api_request_duration_seconds` | histogram | path | latency (p50/p95 in Grafana) |
| `model_predictions_total` | counter | label | prediction mix (disease vs no_disease) |
| `model_disease_probability` | histogram | - | distribution of predicted probabilities; a shift in its mean is a simple drift signal |
| `model_loaded` | gauge | - | 1 once the model is loaded |

The `path` label uses the route template, and unknown URLs become `unmatched`. This keeps label cardinality bounded.

## 5.3 Local stack with Docker Compose

```powershell
docker build -t localhost/heart-api:local .
$env:GRAFANA_PASSWORD = 'assignment-demo-2026'
docker compose up -d
python scripts/generate_traffic.py --url http://127.0.0.1:8000 --count 300 --delay 0.01
```
| UI | URL |
|---|---|
| API | http://127.0.0.1:8000/docs |
| Prometheus | http://127.0.0.1:9090 (Status -> Targets: `heart-api` should be UP) |
| Grafana | http://127.0.0.1:3000 (admin / `$GRAFANA_PASSWORD`), dashboard "Heart Disease API" |

Stop it with:
```powershell
docker compose down
```

The Compose file already contains the networks, volume mounts, health dependencies, ports, and dashboard provisioning. A manual three-container setup is not needed for this repository.

## 5.4 In Kubernetes

The Windows launcher (`scripts/start_all.ps1`) or the Unix helper (`k8s/deploy.sh`) deploys Prometheus and Grafana into `heart-ml`. Prometheus finds every pod annotated `prometheus.io/scrape: "true"` and scrapes each replica separately, not through the Service.

```powershell
kubectl -n heart-ml port-forward service/prometheus 9090:9090
kubectl -n heart-ml port-forward service/grafana 3000:3000
python scripts/generate_traffic.py --url http://127.0.0.1:8000 --count 300 --delay 0.01
```
Run the two port-forwards in separate PowerShell windows. Prometheus should list both `heart-api` pods as UP. Then open the Grafana dashboard.

## 5.5 Dashboard panels (`monitoring/grafana/dashboards/heart-api.json`)

| Panel | PromQL |
|---|---|
| Model loaded | `sum(model_loaded)` |
| Total predictions | `sum(model_predictions_total)` |
| Error rate (5xx) | `sum(rate(api_requests_total{status=~"5.."}[5m])) / sum(rate(api_requests_total[5m]))` |
| Validation errors | `sum(increase(api_requests_total{status="422"}[5m]))` |
| Requests/s by endpoint | `sum by (path, status) (rate(api_requests_total[1m]))` |
| Latency p50/p95 | `histogram_quantile(0.95, sum by (le) (rate(api_request_duration_seconds_bucket{path="/predict"}[5m])))` |
| Prediction mix | `sum by (label) (model_predictions_total)` |
| Mean predicted probability | `rate(model_disease_probability_sum[5m]) / rate(model_disease_probability_count[5m])` |

## 5.6 Screenshots for the report
- Prometheus Targets page (all UP)
- A Prometheus graph of `rate(api_requests_total[1m])`
- The Grafana dashboard after running the traffic generator
- A terminal showing the JSON request logs
