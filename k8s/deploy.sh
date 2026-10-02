#!/usr/bin/env bash
# Deploy the API, Prometheus and Grafana into the heart-ml namespace.
set -euo pipefail
cd "$(dirname "$0")/.."

NS=heart-ml
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-change-me}"

kubectl apply -f k8s/namespace.yaml

kubectl -n "$NS" create configmap grafana-datasources \
  --from-file=monitoring/grafana/provisioning/datasources/datasource.yml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap grafana-dashboard-provider \
  --from-file=monitoring/grafana/provisioning/dashboards/dashboard.yml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap grafana-dashboards \
  --from-file=monitoring/grafana/dashboards/heart-api.json \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create secret generic grafana-admin \
  --from-literal=password="$GRAFANA_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
kubectl apply -f k8s/monitoring/
if kubectl get ingressclass nginx >/dev/null 2>&1; then
  kubectl apply -f k8s/ingress.yaml
else
  echo "No nginx IngressClass found - skipping ingress (run: minikube addons enable ingress)"
fi

kubectl -n "$NS" rollout status deployment/heart-api --timeout=180s
kubectl -n "$NS" get pods,svc,ingress
