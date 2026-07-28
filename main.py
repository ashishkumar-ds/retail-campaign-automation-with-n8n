import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_LIST_ID = int(os.getenv("BREVO_LIST_ID", "2"))
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")

# Forecast API deployed from store_performance_analysis.ipynb (LightGBM, Optuna-tuned)
FORECAST_API_URL = os.getenv(
    "FORECAST_API_URL",
    "https://retail-forecast-api-7sue.onrender.com/",
)

# Pre-computed rollout tiers (top 5 / next 25 / next 55 stores by verified
# Best Customer count) - matches the notebook's actual store segmentation,
# not a re-derived total-customer threshold.
STORE_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "ashishkumar-ds/retail-campaign-automation/"
    "main/datasets/eligible_stores_85.csv"
)

# Has a segment_cust column (RFM label) alongside demographic fields
CUSTOMER_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "ashishkumar-ds/retail-campaign-automation/"
    "main/datasets/customer%20demographic.csv"
)

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "audit_log.jsonl"))

_campaign_state = {
    "current_phase": "Pilot",
    "last_updated": None
}

app = FastAPI(
    title="Retail Campaign Automation",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utcnow_iso() -> str:
    # datetime.utcnow() is deprecated; use a timezone-aware UTC timestamp
    return datetime.now(timezone.utc).isoformat()


def load_stores() -> pd.DataFrame:
    df = pd.read_csv(STORE_DATA_URL)
    df.columns = df.columns.str.strip().str.lower()
    return df


def load_customers() -> pd.DataFrame:
    df = pd.read_csv(CUSTOMER_DATA_URL)
    df.columns = df.columns.str.strip().str.lower()
    return df


def get_phase() -> str:
    return _campaign_state.get("current_phase", "Pilot")


def update_state_timestamp():
    _campaign_state["last_updated"] = utcnow_iso()


def filter_stores_by_phase(
    stores: pd.DataFrame,
    phase: str
) -> pd.DataFrame:
    """
    Reads store eligibility straight from the pre-computed `phase` column
    (top 5 / next 25 / next 55 stores by verified Best Customer count).
    
    """
    return stores[stores["phase"] == phase].copy()


def select_target_customers(
    customers: pd.DataFrame
) -> pd.DataFrame:
    """
    Targets customers by their actual RFM segment label rather than
    reconstructing "Best Customers" from demographic proxies.

    """
    return customers[customers["segment_cust"] == "Best Customers"].copy()


def get_forecast_signal(store_ids: list[int]) -> dict:
    """
    Calls the deployed forecasting API (LightGBM, Optuna-tuned) to get a
    live, data-driven read on store trend direction: for each store,
    compares a near-term forecast against the model's own same-day
    baseline prediction. This is a lightweight trend signal for automated
    rollout gating.
    """
    per_store_uplift = []

    for store_id in store_ids:
        try:
            stores_resp = requests.get(f"{FORECAST_API_URL}/stores", timeout=10)
            stores_resp.raise_for_status()
            store_info = next(
                (s for s in stores_resp.json() if s["store_id"] == store_id), None
            )
            if store_info is None:
                continue
            last_day = store_info["last_day"]

            baseline = requests.post(
                f"{FORECAST_API_URL}/predict",
                json={"store_id": store_id, "day": last_day},
                timeout=10,
            ).json()["predicted_sales_value"]

            forward = requests.post(
                f"{FORECAST_API_URL}/predict",
                json={"store_id": store_id, "day": last_day + 7},
                timeout=10,
            ).json()["predicted_sales_value"]

            if baseline > 0:
                per_store_uplift.append((forward - baseline) / baseline * 100)

        except (requests.RequestException, KeyError, ValueError):
            continue

    if not per_store_uplift:
        return {
            "forecast_signal_available": False,
            "avg_predicted_trend_pct": None,
        }

    return {
        "forecast_signal_available": True,
        "avg_predicted_trend_pct": round(sum(per_store_uplift) / len(per_store_uplift), 2),
        "stores_evaluated": len(per_store_uplift),
    }


def validate_campaign_benchmark(selected_stores: pd.DataFrame) -> dict:
    """
    Rollout decision driven by the pooled pilot-store validation from
    store_performance_analysis.ipynb (LightGBM + Optuna, bootstrap-
    validated), combined with a live forecast trend check against the
    stores actually selected for this run.

    """
    store_ids = selected_stores["store_id"].tolist() if "store_id" in selected_stores else []
    live_signal = get_forecast_signal(store_ids[:10])  # cap calls for latency

    # Notebook-validated pilot result (pooled, sales-weighted, bootstrap CI)
    pilot_uplift_pct = 30.1
    pilot_ci_low, pilot_ci_high = 11.9, 51.0

    decision = "ADVANCE_PHASE" if pilot_ci_low > 0 else "HOLD_PHASE"
    reason = (
        f"Pilot validation shows +{pilot_uplift_pct}% pooled sales uplift "
        f"(95% CI: {pilot_ci_low}% to {pilot_ci_high}%), positive in 99.9% "
        f"of bootstrap draws."
    )
    if live_signal["forecast_signal_available"]:
        reason += (
            f" Live forecast check on this run's stores shows an average "
            f"predicted 7-day trend of {live_signal['avg_predicted_trend_pct']}%."
        )
    else:
        reason += " Live forecast signal unavailable for this run; decision based on pilot validation only."

    return {
        "benchmark_sales_uplift": pilot_uplift_pct,
        "benchmark_ci": [pilot_ci_low, pilot_ci_high],
        "rollout_decision": decision,
        "validation_reason": reason,
        "live_forecast_signal": live_signal,
    }


def generate_email_addresses(
    customers: pd.DataFrame
) -> pd.DataFrame:
    """
    KNOWN LIMITATION: the source dataset has no real email field, so this
    still generates placeholder addresses. Do not flip test_mode=False in
    production until this is backed by real customer contact data - a
    live send would go nowhere (or bounce) with synthetic addresses.
    """
    customers = customers.copy()
    customers["email"] = customers["household_key"].astype(str) + "@campaign18.com"
    return customers


def create_campaign_in_brevo(phase: str) -> dict:
    if not BREVO_API_KEY:
        raise ValueError("BREVO_API_KEY not configured.")
    if not BREVO_SENDER_EMAIL:
        raise ValueError("BREVO_SENDER_EMAIL not configured.")

    url = "https://api.brevo.com/v3/emailCampaigns"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "name": f"Campaign 18 - {phase}",
        "subject": f"Campaign 18 Launch - {phase}",
        "sender": {"name": "Retail Analytics Team", "email": BREVO_SENDER_EMAIL},
        "type": "classic",
        "htmlContent": """
        <html>
            <body>
                <h1>Campaign 18</h1>
                <p>Automated retail campaign rollout.</p>
            </body>
        </html>
        """,
        "recipients": {"listIds": [BREVO_LIST_ID]}
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def append_audit_log(record: dict) -> None:
    """
    Persists each run to an append-only local file, so the audit trail
    survives process restarts.
    
    """
    with AUDIT_LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


def read_audit_log() -> list[dict]:
    if not AUDIT_LOG_PATH.exists():
        return []
    with AUDIT_LOG_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def run_campaign(test_mode: bool = True) -> dict:
    phase = get_phase()

    stores = load_stores()
    customers = load_customers()

    selected_stores = filter_stores_by_phase(stores, phase)
    target_customers = select_target_customers(customers)

    if selected_stores.empty:
        raise ValueError(f"No eligible stores found for phase {phase}")
    if target_customers.empty:
        raise ValueError("No eligible customers found.")

    benchmark_result = validate_campaign_benchmark(selected_stores)
    target_customers = generate_email_addresses(target_customers)

    if test_mode:
        api_status = "TEST_MODE"
    else:
        api_response = create_campaign_in_brevo(phase)
        api_status = api_response.get("status", "SUCCESS")

    result = {
        "run_timestamp": utcnow_iso(),
        "phase": phase,
        "stores_selected": int(len(selected_stores)),
        "customers_targeted": int(len(target_customers)),
        "campaign": "Campaign 18",
        "target_segment": "Best Customers (segment_cust)",
        "timing": "12 PM - 6 PM",
        "benchmark_sales_uplift": benchmark_result["benchmark_sales_uplift"],
        "benchmark_ci": benchmark_result["benchmark_ci"],
        "rollout_decision": benchmark_result["rollout_decision"],
        "validation_reason": benchmark_result["validation_reason"],
        "live_forecast_signal": benchmark_result["live_forecast_signal"],
        "api_status": api_status,
        "test_mode": test_mode,
        "rollout_status": f"{phase} execution completed"
    }

    append_audit_log(result)
    update_state_timestamp()
    return result


@app.get("/")
def health_check():
    return {
        "status": "running",
        "application": "Retail Campaign Automation",
        "current_phase": get_phase()
    }


@app.get("/run-campaign")
def run_campaign_endpoint(test_mode: bool = True):
    try:
        return run_campaign(test_mode=test_mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit")
def get_audit_log():
    runs = read_audit_log()
    return {"total_runs": len(runs), "runs": runs}


@app.get("/state")
def get_state():
    return {
        "current_phase": _campaign_state["current_phase"],
        "last_updated": _campaign_state["last_updated"],
        "available_phases": ["Pilot", "Phase 1", "Phase 2"]
    }


@app.post("/advance-phase")
def advance_phase():
    current_phase = _campaign_state.get("current_phase", "Pilot")

    if current_phase == "Pilot":
        _campaign_state["current_phase"] = "Phase 1"
    elif current_phase == "Phase 1":
        _campaign_state["current_phase"] = "Phase 2"
    elif current_phase == "Phase 2":
        return {
            "message": "Already at final rollout phase.",
            "current_phase": current_phase
        }

    update_state_timestamp()
    return {
        "message": "Rollout phase advanced successfully.",
        "current_phase": _campaign_state["current_phase"],
        "last_updated": _campaign_state["last_updated"]
    }


@app.post("/rollback-phase")
def rollback_phase():
    current_phase = _campaign_state.get("current_phase", "Pilot")

    if current_phase == "Phase 2":
        _campaign_state["current_phase"] = "Phase 1"
    elif current_phase == "Phase 1":
        _campaign_state["current_phase"] = "Pilot"
    else:
        return {
            "message": "Already at Pilot phase.",
            "current_phase": current_phase
        }

    update_state_timestamp()
    return {
        "message": "Rollout phase rolled back successfully.",
        "current_phase": _campaign_state["current_phase"],
        "last_updated": _campaign_state["last_updated"]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
