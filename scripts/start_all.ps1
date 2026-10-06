param(
    [ValidateSet('kubernetes', 'compose')]
    [string]$Mode = 'kubernetes',
    [string]$GrafanaPassword = 'assignment-demo-2026'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Find-Tool([string]$Name, [string]$Fallback) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Path }
    if (Test-Path $Fallback) { return $Fallback }
    throw "Cannot find $Name. Install it or add it to PATH."
}

function Run-Checked([string]$Tool, [string[]]$Arguments) {
    & $Tool @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$([IO.Path]::GetFileName($Tool)) failed with exit code $LASTEXITCODE." }
}

function Apply-Generated([string[]]$Arguments) {
    $yaml = & $Kubectl @Arguments '--dry-run=client' '-o' 'yaml'
    if ($LASTEXITCODE -ne 0) { throw 'kubectl could not generate the resource.' }
    $yaml | & $Kubectl apply -f -
    if ($LASTEXITCODE -ne 0) { throw 'kubectl could not apply the generated resource.' }
}

function Wait-Url([string]$Url, [int]$Attempts = 60) {
    for ($i = 0; $i -lt $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return }
        } catch {
            if ($i -eq ($Attempts - 1)) { throw "Timed out waiting for $Url." }
            Start-Sleep -Seconds 1
        }
    }
}

function Start-Mlflow {
    & $Docker rm -f mlflow-ui *> $null
    $volume = "$($Root):/workspace"
    $command = 'python -m pip install -q mlflow==2.17.2 && mlflow ui --backend-store-uri ./mlruns --host 0.0.0.0 --port 5000'
    Run-Checked $Docker @('run', '-d', '--name', 'mlflow-ui', '-p', '127.0.0.1:5000:5000', '-v', $volume, '-w', '/workspace', 'python:3.12-slim', 'sh', '-c', $command)
    Wait-Url 'http://127.0.0.1:5000' 180
}

function Wait-Docker {
    $desktop = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    $started = $false
    for ($i = 0; $i -lt 60; $i++) {
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try { & $Docker info *> $null } catch { }
        $ready = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $previousPreference
        if ($ready) { return }
        if (-not $started) {
            if (Test-Path $desktop) { Start-Process $desktop }
            $started = $true
        }
        Start-Sleep -Seconds 2
    }
    throw 'Docker Desktop did not become ready.'
}

$Docker = Find-Tool 'docker' "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe"

if ($Mode -eq 'compose') {
    Wait-Docker
    $env:GRAFANA_PASSWORD = $GrafanaPassword
    Run-Checked $Docker @('compose', 'up', '-d', '--build')
    Start-Mlflow
    Wait-Url 'http://127.0.0.1:8000/health'
    Wait-Url 'http://127.0.0.1:9090/targets'
    Wait-Url 'http://127.0.0.1:3000'
    Write-Host 'Compose is ready: http://127.0.0.1:8000/docs, http://127.0.0.1:9090/targets, http://127.0.0.1:3000, http://127.0.0.1:5000'
    exit 0
}

$Kubectl = Find-Tool 'kubectl' "$env:ProgramFiles\Docker\Docker\resources\bin\kubectl.exe"
$Minikube = Find-Tool 'minikube' "$env:ProgramFiles\Kubernetes\Minikube\minikube.exe"

Wait-Docker
Run-Checked $Docker @('build', '-t', 'localhost/heart-api:local', '.')

& $Minikube status *> $null
if ($LASTEXITCODE -ne 0) {
    Run-Checked $Minikube @('start', '--driver=docker', '--cpus=2', '--memory=4096')
}
Run-Checked $Minikube @('addons', 'enable', 'ingress')
Run-Checked $Minikube @('addons', 'enable', 'metrics-server')
Run-Checked $Minikube @('image', 'load', 'localhost/heart-api:local')

Run-Checked $Kubectl @('apply', '-f', 'k8s/namespace.yaml')
$Namespace = 'heart-ml'
Apply-Generated @('-n', $Namespace, 'create', 'configmap', 'grafana-datasources', '--from-file=datasource.yml=monitoring/grafana/provisioning/datasources/datasource.yml')
Apply-Generated @('-n', $Namespace, 'create', 'configmap', 'grafana-dashboard-provider', '--from-file=dashboard.yml=monitoring/grafana/provisioning/dashboards/dashboard.yml')
Apply-Generated @('-n', $Namespace, 'create', 'configmap', 'grafana-dashboards', '--from-file=heart-api.json=monitoring/grafana/dashboards/heart-api.json')
Apply-Generated @('-n', $Namespace, 'create', 'secret', 'generic', 'grafana-admin', "--from-literal=password=$GrafanaPassword")

Run-Checked $Kubectl @('apply', '-f', 'k8s/deployment.yaml', '-f', 'k8s/service.yaml', '-f', 'k8s/monitoring/', '-f', 'k8s/ingress.yaml')
Run-Checked $Kubectl @('-n', $Namespace, 'rollout', 'status', 'deployment/heart-api', '--timeout=180s')
Run-Checked $Kubectl @('-n', $Namespace, 'rollout', 'status', 'deployment/prometheus', '--timeout=180s')
Run-Checked $Kubectl @('-n', $Namespace, 'rollout', 'status', 'deployment/grafana', '--timeout=180s')

Start-Process $Minikube -ArgumentList 'tunnel' -WindowStyle Minimized | Out-Null
Start-Process $Kubectl -ArgumentList '-n', $Namespace, 'port-forward', 'service/heart-api', '8000:8000' -WindowStyle Minimized | Out-Null
Start-Process $Kubectl -ArgumentList '-n', $Namespace, 'port-forward', 'service/prometheus', '9090:9090' -WindowStyle Minimized | Out-Null
Start-Process $Kubectl -ArgumentList '-n', $Namespace, 'port-forward', 'service/grafana', '3000:3000' -WindowStyle Minimized | Out-Null

Wait-Url 'http://127.0.0.1:8000/health'
Wait-Url 'http://127.0.0.1:9090/targets'
Wait-Url 'http://127.0.0.1:3000'
Start-Mlflow

Write-Host 'Kubernetes is ready:'
Write-Host '  Swagger:    http://127.0.0.1:8000/docs'
Write-Host '  Prometheus: http://127.0.0.1:9090/targets'
Write-Host '  Grafana:    http://127.0.0.1:3000'
Write-Host '  MLflow:     http://127.0.0.1:5000'
