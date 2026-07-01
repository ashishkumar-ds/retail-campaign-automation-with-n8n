# Retail Campaign Automation with n8n

> Part 2 of the Dunnhumby series. See [Part 1 — Retail Store Performance Analysis](https://github.com/ashishkumar-ds/dunnhumby-retail-performance) for the full analytical foundation.

---

## Project Summary

This project operationalizes the findings from the Retail Store Performance Analysis by building an **end-to-end campaign automation system** across 85 eligible underperforming stores. Using **FastAPI, n8n, and Brevo**, the system automates store eligibility scoring, customer targeting, campaign delivery, audit logging, and stakeholder reporting — replacing a fully manual, per-store analyst process with a single scheduled trigger.

Validated on a pilot at Store 289: **+10.8% sales uplift, 411% gross ROI over 55 days**.

---

## Problem Statement

- Previous analysis proved **Campaign 18 + Best Customers + afternoon timing** as the strongest growth drivers
- Manual execution required per-store analyst review, making consistent deployment across **85 stores impossible**

**Business Question**:
> How can proven campaign strategies be scaled efficiently while maintaining execution control and operational visibility?

---

## System Architecture

| Layer | Tool | Role |
|---|---|---|
| **Business Logic** | FastAPI on Render | Store scoring, eligibility, targeting rules |
| **Orchestration** | n8n | Scheduled workflow, phase advancement, failure handling |
| **Campaign Delivery** | Brevo | Email campaign execution |
| **Audit Log** | Google Sheets | Timestamped execution record per run |
| **Stakeholder Alerts** | Gmail | Automated deployment summary per phase |

---

## Rollout Design

Phase eligibility is determined by `filter_stores_by_phase()` in `main.py` using the following criteria:

| Phase | Min Best Customers | Min Sales Value |
|---|---|---|
| **Pilot** | ≥ 70 | ≥ $50,000 |
| **Phase 1** | 50–69 | $35K–$50K |
| **Phase 2** | 20–49 | $20K–$35K |

***356 zombie stores excluded. Total eligible: 85 stores across all phases.
Note:Successful completion of Phase 2 represents full rollout across all 85 eligible stores.***
---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check and current phase |
| `/run-campaign` | GET | Execute campaign for current phase |
| `/advance-phase` | POST | Advance rollout to next phase |
| `/rollback-phase` | POST | Roll back to previous phase |
| `/audit` | GET | View all execution run records |
| `/state` | GET | View current phase and last updated timestamp |

`/run-campaign` accepts `?test_mode=true` (default) to run without hitting Brevo.

---

## Key Outputs

| Output | Description |
|---|---|
| **Execution log** | Timestamped in-memory record per run, accessible via `/audit` |
| **Rollout decision** | Advance or hold based on Campaign 18 benchmark |
| **Stakeholder email** | Gmail summary with phase, stores, customers, and status |
| **Failure flag** | Failed runs surface a 500 error with detail for manual review |

---

## Business Impact

| Focus Area | Before | After |
|---|---|---|
| **Execution process** | Manual per-store analyst review | Single n8n trigger, fully automated |
| **Business rule application** | Inconsistent across stores | Centralized in FastAPI, applied uniformly |
| **Audit trail** | None | Timestamped log per run in Google Sheets |
| **Stakeholder visibility** | Ad hoc reporting | Automated Gmail alert per deployment |
| **Failure handling** | Silent failures | Logged and flagged for review |

*Note: portfolio-scale system validated on a single historical dataset. Impact is directional, not measured against a timed production baseline.*

---

## Current Scope and Known Limitations

This is a portfolio-scale system built on a single historical dataset, not a live production deployment.

- **In-memory state**: campaign phase and audit log reset on server restart. In production this would persist to a database
- **Benchmark validation**: the 10.7% uplift threshold is hardcoded from Campaign 18 historical results, not computed from live run data
- **Synthetic emails**: customer emails are generated as `household_key@campaign18.com` and do not represent real CRM contacts
- **No retry logic**: failed runs are surfaced as errors but not automatically retried

---

## Tools and Technologies

- **Python**: FastAPI, Pandas, Requests
- **Orchestration**: n8n
- **Deployment**: Render
- **Campaign Delivery**: Brevo
- **Logging and Alerts**: Google Sheets, Gmail

---

## Project Structure

```bash
dunnhumby-campaign-automation/
│
├── datasets/          # Static source datasets (CSV/Excel) from Dunnhumby
│
├── main.py            # FastAPI app: store scoring, eligibility, campaign logic
├── render.yaml        # Render deployment configuration
├── requirements.txt   # Python dependencies
├── runtime.txt        # Python runtime version for Render
├── .gitignore
└── README.md
```
