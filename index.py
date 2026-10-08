import json
from pathlib import Path
from statistics import mean

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["*"],
)

DATA = json.loads(Path(__file__).with_name("q-vercel-latency.json").read_text())


class RequestBody(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile95(values):
    """95th percentile with linear interpolation (same as numpy default)."""
    values = sorted(values)
    position = (len(values) - 1) * 0.95
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


@app.get("/")
def health():
    return {"status": "ok", "endpoint": "/api/latency"}


@app.post("/")
@app.post("/api/latency")
def analytics(body: RequestBody):
    result = {}
    for region in body.regions:
        records = [row for row in DATA if row["region"] == region]
        if not records:
            result[region] = {"avg_latency": None, "p95_latency": None,
                              "avg_uptime": None, "breaches": 0}
            continue
        latencies = [row["latency_ms"] for row in records]
        result[region] = {
            "avg_latency": mean(latencies),
            "p95_latency": percentile95(latencies),
            "avg_uptime": mean(row["uptime_pct"] for row in records),
            "breaches": sum(value > body.threshold_ms for value in latencies),
        }
    return result
