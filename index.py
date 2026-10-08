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
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def ensure_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

DATA = json.loads(Path(__file__).with_name("q-vercel-latency.json").read_text())

class RequestBody(BaseModel):
    regions: list[str]
    threshold_ms: float

def percentile95(values):
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
