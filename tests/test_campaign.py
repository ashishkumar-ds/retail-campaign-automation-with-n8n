"""Offline tests for the campaign automation API.

No network: store/customer data comes from inline fixtures, the forecast
signal from a patched client, Brevo from test_mode. Run with: pytest -q
"""

import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main as campaign


@pytest.fixture()
def stores_df():
    # total_customer drives phase ranking; store_id is the output field
    return pd.DataFrame(
        {
            "store_id": [1, 2, 3, 4, 5, 6],
            "total_customer": [10, 90, 30, 70, 50, 20],
        }
    )


@pytest.fixture()
def customers_df():
    return pd.DataFrame(
        {
            "household_key": [101, 102, 103],
            "segment_cust": ["Best Customers", "Loyal", "Best Customers"],
        }
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "AUDIT_LOG_PATH", tmp_path / "audit_log.jsonl")
    monkeypatch.setitem(campaign._campaign_state, "current_phase", "Pilot")
    monkeypatch.setitem(campaign._campaign_state, "last_updated", None)
    return TestClient(campaign.app)


# ---- pure logic ----

def test_filter_stores_by_phase_ranks_by_best_customer_count(stores_df):
    ranked = stores_df.sort_values("total_customer", ascending=False).reset_index(drop=True)
    pilot = campaign.filter_stores_by_phase(stores_df, "Pilot")
    assert pilot["store_id"].tolist() == ranked.iloc[0:5]["store_id"].tolist()
    assert list(pilot["total_customer"]) == sorted(pilot["total_customer"], reverse=True)


def test_filter_stores_by_phase_slices_do_not_overlap(stores_df):
    ids = {
        phase: set(campaign.filter_stores_by_phase(stores_df, phase)["store_id"])
        for phase in ("Pilot", "Phase 1", "Phase 2")
    }
    assert len(ids["Pilot"] | ids["Phase 1"] | ids["Phase 2"]) == 6


def test_filter_stores_by_phase_rejects_unknown_phase(stores_df):
    with pytest.raises(ValueError, match="Invalid rollout phase"):
        campaign.filter_stores_by_phase(stores_df, "Phase 99")


def test_select_target_customers_only_best(customers_df):
    targets = campaign.select_target_customers(customers_df)
    assert targets["segment_cust"].eq("Best Customers").all()
    assert len(targets) == 2


def test_generate_email_addresses_deterministic(customers_df):
    out = campaign.generate_email_addresses(customers_df)
    assert out["email"].tolist() == ["101@campaign18.com", "102@campaign18.com", "103@campaign18.com"]


def test_local_dataset_loaders_match_remote_contract():
    """The local-first loaders must produce the columns the rules rely on."""
    stores = campaign.load_stores()
    customers = campaign.load_customers()
    assert {"store_id", "total_customer"} <= set(stores.columns)
    assert {"household_key", "segment_cust"} <= set(customers.columns)
    assert "Best Customers" in set(customers["segment_cust"])


def test_audit_log_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "AUDIT_LOG_PATH", tmp_path / "audit_log.jsonl")
    assert campaign.read_audit_log() == []
    campaign.append_audit_log({"campaign": "Campaign 18", "store_ids": [1, 2]})
    campaign.append_audit_log({"campaign": "Campaign 18", "store_ids": [3]})
    assert [r["store_ids"] for r in campaign.read_audit_log()] == [[1, 2], [3]]


# ---- forecast signal (patched HTTP) ----

class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_get_forecast_signal_computes_avg_uplift(monkeypatch):
    def fake_get(url, timeout):
        return FakeResp([{"store_id": 7, "last_day": 100}])

    calls = []

    def fake_post(url, json, timeout):
        calls.append(json)
        value = 100.0 if json["day"] == 100 else 110.0
        return FakeResp({"predicted_sales_value": value})

    monkeypatch.setattr(campaign.requests, "get", fake_get)
    monkeypatch.setattr(campaign.requests, "post", fake_post)

    signal = campaign.get_forecast_signal([7])
    assert signal["forecast_signal_available"] is True
    assert signal["avg_predicted_trend_pct"] == 10.0
    assert signal["stores_evaluated"] == 1
    assert calls == [{"store_id": 7, "day": 100}, {"store_id": 7, "day": 107}]


def test_get_forecast_signal_unavailable_when_all_calls_fail(monkeypatch):
    def boom(*a, **k):
        raise campaign.requests.ConnectionError("offline")

    monkeypatch.setattr(campaign.requests, "get", boom)
    monkeypatch.setattr(campaign.requests, "post", boom)
    signal = campaign.get_forecast_signal([7])
    assert signal == {"forecast_signal_available": False, "avg_predicted_trend_pct": None}


# ---- endpoints ----

def test_health_check(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["current_phase"] == "Pilot"


def test_advance_and_rollback_phase(client):
    assert client.post("/advance-phase").json()["current_phase"] == "Phase 1"
    assert client.post("/advance-phase").json()["current_phase"] == "Phase 2"
    final = client.post("/advance-phase").json()
    assert final["current_phase"] == "Phase 2"  # already at final phase
    assert client.post("/rollback-phase").json()["current_phase"] == "Phase 1"


def test_run_campaign_test_mode_end_to_end(client, stores_df, customers_df, monkeypatch):
    monkeypatch.setattr(campaign, "load_stores", lambda: stores_df)
    monkeypatch.setattr(campaign, "load_customers", lambda: customers_df)
    monkeypatch.setattr(
        campaign, "get_forecast_signal", lambda ids: {"forecast_signal_available": False}
    )

    r = client.get("/run-campaign", params={"test_mode": True})
    assert r.status_code == 200
    body = r.json()
    assert body["api_status"] == "TEST_MODE"
    assert body["stores_selected"] == 5
    assert body["customers_targeted"] == 2
    assert body["test_mode"] is True

    # run was persisted to the (tmp) audit log and exposed via /audit
    audit = client.get("/audit").json()
    assert audit["total_runs"] == 1
    assert audit["runs"][0]["campaign"] == "Campaign 18"


def test_audit_contract_schema_filters_fields(client, stores_df, customers_df, monkeypatch):
    monkeypatch.setattr(campaign, "load_stores", lambda: stores_df)
    monkeypatch.setattr(campaign, "load_customers", lambda: customers_df)
    monkeypatch.setattr(
        campaign, "get_forecast_signal", lambda ids: {"forecast_signal_available": False}
    )
    client.get("/run-campaign", params={"test_mode": True})

    contract = client.get("/audit", params={"schema": "contract"}).json()["runs"][0]
    assert set(contract) == {"campaign", "timing", "run_timestamp", "store_ids"}

    bad = client.get("/audit", params={"schema": "nope"})
    assert bad.status_code == 400
