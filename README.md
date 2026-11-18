# Retail Campaign Automation with n8n

[![CI](https://github.com/ashishkumar-ds/retail-campaign-automation-with-n8n/actions/workflows/ci.yml/badge.svg)](https://github.com/ashishkumar-ds/retail-campaign-automation-with-n8n/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![n8n](https://img.shields.io/badge/orchestration-n8n-EA4B71?logo=n8n&logoColor=white)](https://n8n.io)
[![Live API](https://img.shields.io/badge/api-render-46e3b7?logo=render&logoColor=white)](https://retail-campaign-automation.onrender.com/)
[![Brevo](https://img.shields.io/badge/delivery-brevo-0B996E)](https://www.brevo.com)

> Part 2 of the Dunnhumby series. See [Part 1 — Retail Store Performance Analysis](https://github.com/ashishkumar-ds/data-science-projects/tree/main/dunnhumby-retail-performance-analysis) for the full analytical foundation.

---

## Project Summary

This project operationalizes the findings from the Retail Store Performance Analysis by building an **end-to-end campaign automation system** across 85 eligible underperforming stores. Using **FastAPI, n8n, and Brevo**, the system automates store eligibility scoring, customer targeting, campaign delivery, audit logging, and stakeholder reporting, replacing a fully manual, per-store analyst process with a single scheduled trigger.


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
| **Audit Log** | Append-only JSONL (`audit_log.jsonl`) | Timestamped execution record per run, served at `/audit` |
| **Stakeholder Alerts** | Gmail | Automated deployment summary per phase |

---

## Notebooks

| Notebook | Description |
|----------|-------------|
| `campaign_automation_analysis.ipynb` | Executable walkthrough of the automation logic: store eligibility, phase selection, customer targeting, audit trail, and the forecast-vs-causal rollout gate — every `main.py` rule reproduced in inspectable pandas. Start here. |
| `main.py` | FastAPI service implementing the same rules for the deployed n8n workflow. |

## Rollout Design

Phase eligibility is determined by `filter_stores_by_phase()` in `main.py` using the following criteria:

| Phase | Stores | Selection Rule |
|-------|-------:|----------------|
| **Pilot** | 5 | Top 5 stores ranked by Best Customer Count |
| **Phase 1** | 25 | Next 25 stores ranked by Best Customer Count |
| **Phase 2** | 55 | Next 55 stores ranked by Best Customer Count |

356 zombie stores excluded. Total eligible: 85 stores across all phases.

*Note: Successful completion of Phase 2 represents full rollout across all 85 eligible stores.*

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
| **Execution log** | Timestamped record appended to `audit_log.jsonl` per run, accessible via `/audit` |
| **Rollout decision** | Advance or hold: causal DiD benchmark by default, forecast benchmark on env override |
| **Stakeholder email** | Gmail summary with phase, stores, customers, and status |
| **Failure flag** | Failed runs surface a 500 error with detail for manual review |

---

## Business Impact

| Focus Area | Before | After |
|---|---|---|
| **Execution process** | Manual per-store analyst review | Single n8n trigger, fully automated |
| **Business rule application** | Inconsistent across stores | Centralized in FastAPI, applied uniformly |
| **Audit trail** | None | Timestamped record appended to `audit_log.jsonl` per run |
| **Stakeholder visibility** | Ad hoc reporting | Automated Gmail alert per deployment |
| **Failure handling** | Silent failures | Logged and flagged for review |

*Note: portfolio-scale system validated on a single historical dataset. Impact is directional, not measured against a timed production baseline.*

---

## Current Scope and Known Limitations

This is a portfolio-scale system built on a single historical dataset, not a live production deployment.

- **In-memory state**: campaign phase resets on server restart. The audit log is an append-only local `audit_log.jsonl`, so it survives restarts but not redeploys on ephemeral hosting; in production both would persist to a database
- **Benchmark validation**: the rollout gate is **env-configurable** — `PILOT_UPLIFT_PCT` / `PILOT_CI_LOW` / `PILOT_CI_HIGH`. Defaults carry the causal DiD estimate (2.84 / −0.5 / 6.2), whose CI admits zero, so the default decision is `HOLD_PHASE`; `validation_reason` records the figure's origin. The forecast benchmark (+30.1%, which absorbs +9.7% market drift) is an explicit opt-in, not the default
- **Synthetic emails**: customer emails are generated as `household_key@campaign18.com` and do not represent real CRM contacts
- **No retry logic**: failed runs are surfaced as errors but not automatically retried

---

## Tools and Technologies

- **Python**: FastAPI, Pandas, Requests
- **Orchestration**: n8n
- **Deployment**: Render
- **Campaign Delivery**: Brevo
- **Logging and Alerts**: append-only JSONL audit log; Gmail summary from the n8n workflow

---

## Project Structure

```bash
dunnhumby-campaign-automation/
│
├── datasets/          # Static source datasets (CSV/Excel) from Dunnhumby
├── outputs/           # Workflow execution output, API response, and stakeholder email samples
│
├── campaign_automation_analysis.ipynb  # Executable analysis notebook (start here)
├── main.py            # FastAPI app: store scoring, eligibility, campaign logic
├── audit_log.jsonl    # Append-only execution audit log (consumed by Part 3)
├── render.yaml        # Render deployment configuration
├── requirements.txt   # Python dependencies
├── runtime.txt        # Python runtime version for Render
├── .gitignore
└── README.md
```

---

## References

1. dunnhumby — *Personalised Offers for Retailers* (campaign framework, addressable-base targeting)
2. dunnhumby — [Retail:Vision](https://www.dunnhumby.com/reports/retail-vision-report/) (2026) — connected, AI-powered retail decision-making (series motivation)
3. WARC — [ROI of Successful Campaigns Continues to Grow](https://www.warc.com/en/feed/roi-of-successful-campaigns-continues-to-grow-7a1825cccc034f6ea0a62ecb0c7d9997) (2024; ROI benchmark used in Part 1)
4. Part-1 notebook — [store_performance_analysis_with_DiD.ipynb](https://github.com/ashishkumar-ds/data-science-projects/blob/main/dunnhumby-retail-performance-analysis/notebooks/store_performance_analysis_with_DiD.ipynb), DiD Validation section (causal estimates that gate this system's rollout)

## License

MIT — see [LICENSE](LICENSE).
