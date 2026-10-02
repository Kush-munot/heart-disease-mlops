# 1. Setup and running locally

This guide goes from a clean clone to a trained model, a running API and tracked experiments. Every command runs from the repo root.

## 1.1 Prerequisites

| Tool | Version used | Needed for |
|---|---|---|
| Python | 3.12 | everything |
| Git | any recent | version control |
| Podman (or Docker) | Podman 5+/6 | container build/run |
| make | preinstalled on macOS/Linux | shortcuts (optional) |

Installation steps for each tool are in [02_EXTERNAL_TOOLS.md](02_EXTERNAL_TOOLS.md).

## 1.2 Create the environment

```bash
git clone https://github.com/<your-user>/heart-disease-mlops.git
cd heart-disease-mlops
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Every dependency in `requirements.txt` is pinned to an exact version, so a clean install matches CI and the container. The container uses the smaller `api/requirements.txt`: the same pins, minus MLflow, the plotting libraries and the test tools.

On macOS, if `python -m venv` produces an environment without pip (an `ensurepip` failure), install Python from python.org or run `brew reinstall python@3.12`. Conda also works: `conda create -n heart python=3.12 && conda activate heart && pip install -r requirements.txt`.

## 1.3 Pipeline step by step

| Step | Command | Output |
|---|---|---|
| 1. Get + clean data | `make data` (= `python -m heart.data`) | `data/raw/processed.cleveland.data`, `data/processed/heart_clean.csv` |
| 2. EDA figures | `make eda` (= `python -m heart.eda`) | `reports/figures/eda_*.png` |
| 3. Train + track | `make train` (= `python -m heart.train`) | `mlruns/`, `models/model.joblib`, `models/metadata.json`, `reports/figures/best_*.png` |
| 4. Tests | `make test` | 29 passing tests + coverage |
| 5. Lint | `make lint` | no output = clean |
| 6. Serve locally | `make serve` | API on http://127.0.0.1:8000 |

### Data acquisition
`heart/data.py` downloads `processed.cleveland.data` from the UCI repository:
https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data

It caches the file in `data/raw/`. Pass `--force` to download it again. The script then:
- names the 14 columns and reads `?` as missing (4 rows in `ca`, 2 in `thal`);
- converts every column to numeric;
- turns the 0-4 diagnosis `num` into the binary `target` (0 = none, 1 = any disease);
- drops exact duplicate rows.

Missing values are left in the cleaned CSV on purpose. The model pipeline imputes them, learning the fill values on training folds only, which avoids test-set leakage.

Manual alternative: download the file from https://archive.ics.uci.edu/dataset/45/heart+disease (the `processed.cleveland.data` file inside the zip), save it to `data/raw/`, then run `make data`.

### Training options
```bash
python -m heart.train --folds 5 --experiment heart-disease-classification
python -m heart.train --no-register        # skip the MLflow model-registry step
MLFLOW_TRACKING_URI=http://127.0.0.1:5000 python -m heart.train   # log to an MLflow server
```

### Notebooks
```bash
jupyter lab                    # open notebooks/01_eda.ipynb, 02_training.ipynb, 03_inference.ipynb
make notebooks                 # re-execute all three headlessly
```
The notebooks call the same `heart` package as the scripts, so both paths produce the same results.

## 1.4 Experiment tracking UI

```bash
make mlflow-ui     # mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000
```
Open http://127.0.0.1:5000 and select the experiment **heart-disease-classification**:
- A parent run `model-selection` holds the comparison table and chart, the best-model tags and `metadata.json`.
- There is one nested run per model family. Each has its best hyper-parameters, `cv_*` metrics (mean and std), `test_*` metrics, `evaluation/` artifacts (confusion matrix, ROC curve, feature importance, full `cv_results.csv`) and the logged `model` with its signature and input example.
- The **Models** tab shows `heart-disease-classifier`, with a new version for every training run.

Screenshots to capture: the experiment list, a run-comparison view (select the 3 nested runs, then Compare), one run's artifacts, and the registered model.

## 1.5 Run the API

Without a container:
```bash
make serve                                        # uvicorn with --reload on 127.0.0.1:8000
python scripts/smoke_test.py                      # health, two predictions, 422 check, metrics
```

With a container:
```bash
make image          # podman build -t localhost/heart-api:local .
make run            # podman run -d -p 127.0.0.1:8000:8000 ...
make smoke
podman logs -f heart-api
podman stop heart-api
```
For Docker, use `make image run ENGINE=docker`.

## 1.6 Reproducibility checklist

- Every package is pinned in `requirements.txt` and `api/requirements.txt`.
- `RANDOM_STATE=42` is used for the split, the CV folds and the models (`heart/config.py`).
- Preprocessing lives inside the saved pipeline, so raw JSON goes straight in and no hand-coded transforms are needed at serving time.
- `models/metadata.json` records the model, parameters, metrics, sklearn and Python versions, a timestamp and the MLflow run id.
- The MLflow model artifact can be loaded independently: `mlflow.sklearn.load_model("models:/heart-disease-classifier/1")`.
- To prove a clean setup works, run `make clean && make data train test image run smoke`.
