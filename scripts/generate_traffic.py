import argparse
import json
import random
import time
import urllib.error
import urllib.request


# Build a random but valid patient record.
def random_patient() -> dict:
    return {
        "age": random.randint(30, 77), "sex": random.randint(0, 1), "cp": random.randint(1, 4),
        "trestbps": random.randint(95, 190), "chol": random.randint(130, 400),
        "fbs": random.randint(0, 1), "restecg": random.choice([0, 1, 2]),
        "thalach": random.randint(90, 200), "exang": random.randint(0, 1),
        "oldpeak": round(random.uniform(0, 4), 1), "slope": random.randint(1, 3),
        "ca": random.choice([0, 1, 2, 3, None]), "thal": random.choice([3, 6, 7, None]),
    }


# Send a stream of predictions (plus a few invalid calls) to populate the dashboard.
def main(url: str, count: int, delay: float) -> None:
    for i in range(count):
        body = random_patient() if i % 10 else {"age": 200}
        req = urllib.request.Request(f"{url}/predict", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5).read()
        except urllib.error.HTTPError:
            pass
        time.sleep(delay)
    print(f"sent {count} requests to {url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate demo traffic for monitoring")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--delay", type=float, default=0.2)
    args = parser.parse_args()
    main(args.url.rstrip("/"), args.count, args.delay)
