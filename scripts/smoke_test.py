import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


# Call an endpoint and return (status, parsed JSON body).
def call(url: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


# Poll /health until the service answers or the timeout expires.
def wait_until_healthy(base: str, timeout: int) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if call(f"{base}/health")[0] == 200:
                return
        except (urllib.error.URLError, ConnectionError):
            pass
        time.sleep(2)
    sys.exit(f"API at {base} not healthy after {timeout}s")


# Check health, both sample predictions, input validation and the metrics endpoint.
def main(base: str, timeout: int) -> None:
    wait_until_healthy(base, timeout)
    print("health:", call(f"{base}/health")[1])
    for sample in sorted(SAMPLES.glob("*.json")):
        status, body = call(f"{base}/predict", json.loads(sample.read_text()))
        assert status == 200 and 0.5 <= body["confidence"] <= 1, (sample.name, status, body)
        print(f"{sample.name}: {body}")
    status, _ = call(f"{base}/predict", {"age": "not-a-number"})
    assert status == 422, f"expected 422 for bad input, got {status}"
    metrics = urllib.request.urlopen(f"{base}/metrics", timeout=10).read().decode()
    assert "model_predictions_total" in metrics
    print("smoke test passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test a running heart API")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    main(args.url.rstrip("/"), args.timeout)
