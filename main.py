"""
Retail Campaign Automation System
--------------------------------
Render-ready FastAPI application for retail campaign automation.

Architecture:
GitHub Raw CSV → FastAPI → Store Rollout Logic →
Customer Segmentation → Brevo → n8n Cloud
"""

import os
from datetime import datetime

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_LIST_ID = int(os.getenv("BREVO_LIST_ID", "2"))
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")

STORE_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "ashishkumar-ds/retail-campaign-automation/"
    "main/datasets/stores.csv"
)

CUSTOMER_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "ashishkumar-ds/retail-campaign-automation/"
    "main/datasets/customer%20demographic.csv"
)

_campaign_state = {
    "current_phase": "Pilot",
    "last_updated": None
}

_audit_log = []

app = FastAPI(
    title="Retail Campaign Automation",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_stores() -> pd.DataFrame:

    df = pd.read_csv(STORE_DATA_URL)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    return df


def load_customers() -> pd.DataFrame:

    df = pd.read_csv(CUSTOMER_DATA_URL)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    return df


def get_phase() -> str:

    return _campaign_state.get(
        "current_phase",
        "Pilot"
    )


def update_state_timestamp():

    _campaign_state[
        "last_updated"
    ] = datetime.utcnow().isoformat()


def filter_stores_by_phase(
    stores: pd.DataFrame,
    phase: str
) -> pd.DataFrame:

    if phase == "Pilot":

        return stores[
            (stores["total_customer"] >= 70)
            &
            (stores["sales_value"] >= 50000)
        ].copy()

    elif phase == "Phase 1":

        return stores[
            stores["total_customer"]
            .between(50, 69)
        ].copy()

    elif phase == "Phase 2":

        return stores[
            stores["total_customer"]
            .between(20, 49)
        ].copy()

    return pd.DataFrame()


def select_target_customers(
    customers: pd.DataFrame
) -> pd.DataFrame:

    return customers[
        (customers["age_desc"] == "45-54")
        &
        (customers["income_desc"] == "50-74K")
        &
        (
            customers["hh_comp_desc"]
            == "2 Adults No Kids"
        )
        &
        (
            customers["kid_category_desc"]
            == "None/Unknown"
        )
    ].copy()

def generate_email_addresses(
    customers: pd.DataFrame
) -> pd.DataFrame:

    customers = customers.copy()

    customers["email"] = (
        customers["household_key"]
        .astype(str)
        + "@campaign18.com"
    )

    return customers
    
def create_campaign_in_brevo(
    phase: str
) -> dict:

    if not BREVO_API_KEY:
        raise ValueError(
            "BREVO_API_KEY not configured."
        )

    if not BREVO_SENDER_EMAIL:
        raise ValueError(
            "BREVO_SENDER_EMAIL not configured."
        )

    url = (
        "https://api.brevo.com/"
        "v3/emailCampaigns"
    )

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    payload = {
        "name": f"Campaign 18 - {phase}",
        "subject": (
            f"Campaign 18 Launch - {phase}"
        ),
        "sender": {
            "name": "Retail Analytics Team",
            "email": BREVO_SENDER_EMAIL
        },
        "type": "classic",
        "htmlContent": """
        <html>
            <body>
                <h1>Campaign 18</h1>
                <p>
                    Automated retail campaign rollout.
                </p>
            </body>
        </html>
        """,
        "recipients": {
            "listIds": [BREVO_LIST_ID]
        }
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def append_audit_log(
    record: dict
) -> None:

    _audit_log.append(record)


def run_campaign(
    test_mode: bool = True
) -> dict:

    phase = get_phase()

    stores = load_stores()

    customers = load_customers()

    selected_stores = (
        filter_stores_by_phase(
            stores,
            phase
        )
    )

    target_customers = (
    select_target_customers(
        customers
    )
)

target_customers = (
    generate_email_addresses(
        target_customers
    )
)

    if selected_stores.empty:

        raise ValueError(
            f"No eligible stores "
            f"found for phase {phase}"
        )

    if target_customers.empty:

        raise ValueError(
            "No eligible customers found."
        )

    if test_mode:

        api_status = "TEST_MODE"

    else:

        api_response = (
            create_campaign_in_brevo(
                phase
            )
        )

        api_status = (
            api_response.get(
                "status",
                "SUCCESS"
            )
        )

    result = {
    "run_timestamp":
        datetime.utcnow().isoformat(),

    "phase":
        phase,

    "stores_selected":
        int(len(selected_stores)),

    "customers_targeted":
        int(len(target_customers)),

    "campaign":
        "Campaign 18",

    "target_segment":
        (
            "Age 45-54 | "
            "Income 50-74K | "
            "2 Adults No Kids"
        ),

    "timing":
        "12 PM - 6 PM",

    "api_status":
        api_status,

    "test_mode":
        test_mode,

    "rollout_status":
        f"{phase} execution completed"
}

    append_audit_log(result)

    update_state_timestamp()

    return result


@app.get("/")
def health_check():

    return {
        "status": "running",
        "application":
            "Retail Campaign Automation",
        "current_phase":
            get_phase()
    }


@app.get("/run-campaign")
def run_campaign_endpoint(
    test_mode: bool = True
):

    try:

        return run_campaign(
            test_mode=test_mode
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/audit")
def get_audit_log():

    return {
        "total_runs":
            len(_audit_log),

        "runs":
            _audit_log
    }


@app.get("/state")
def get_state():

    return {
        "current_phase":
            _campaign_state[
                "current_phase"
            ],

        "last_updated":
            _campaign_state[
                "last_updated"
            ],

        "available_phases": [
            "Pilot",
            "Phase 1",
            "Phase 2"
        ]
    }


@app.post("/advance-phase")
def advance_phase():

    current_phase = (
        _campaign_state.get(
            "current_phase",
            "Pilot"
        )
    )

    if current_phase == "Pilot":

        _campaign_state[
            "current_phase"
        ] = "Phase 1"

    elif current_phase == "Phase 1":

        _campaign_state[
            "current_phase"
        ] = "Phase 2"

    elif current_phase == "Phase 2":

        return {
            "message":
                "Already at final rollout phase.",
            "current_phase":
                current_phase
        }

    update_state_timestamp()

    return {
        "message":
            "Rollout phase advanced successfully.",

        "current_phase":
            _campaign_state[
                "current_phase"
            ],

        "last_updated":
            _campaign_state[
                "last_updated"
            ]
    }

@app.post("/rollback-phase")
def rollback_phase():

    current_phase = _campaign_state.get(
        "current_phase",
        "Pilot"
    )

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

    port = int(
        os.environ.get(
            "PORT",
            8000
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
