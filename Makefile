PYTHON ?= python
IMAGE ?= localhost/heart-api:local
ENGINE ?= podman

.PHONY: install data eda train test lint serve mlflow-ui notebooks image run smoke \
        k8s-load k8s-deploy k8s-delete traffic clean

install:
	$(PYTHON) -m pip install -r requirements.txt

data:
	$(PYTHON) -m heart.data

eda: data
	$(PYTHON) -m heart.eda

train: data
	$(PYTHON) -m heart.train

test:
	$(PYTHON) -m pytest -v --cov=heart --cov=api

lint:
	$(PYTHON) -m flake8 heart api tests scripts

serve:
	MODEL_PATH=models/model.joblib $(PYTHON) -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload

mlflow-ui:
	mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000

notebooks:
	jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

image:
	test -f models/model.joblib || $(MAKE) train
	$(ENGINE) build -t $(IMAGE) .

run:
	$(ENGINE) run --rm -d --name heart-api -p 127.0.0.1:8000:8000 $(IMAGE)

smoke:
	$(PYTHON) scripts/smoke_test.py --url http://127.0.0.1:8000

traffic:
	$(PYTHON) scripts/generate_traffic.py --url http://127.0.0.1:8000

k8s-load:
	$(ENGINE) save $(IMAGE) -o /tmp/heart-api.tar
	minikube image load /tmp/heart-api.tar
	rm -f /tmp/heart-api.tar

k8s-deploy:
	bash k8s/deploy.sh

k8s-delete:
	kubectl delete namespace heart-ml --ignore-not-found

clean:
	rm -rf mlruns models/*.joblib models/metadata.json .pytest_cache .coverage
