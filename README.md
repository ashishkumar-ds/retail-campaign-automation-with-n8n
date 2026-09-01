# Retail Campaign Automation with n8n

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
| **Audit Log** | Google Sheets | Timestamped execution record per run |
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
- **Benchmark validation**: the rollout gate is **env-configurable** — `PILOT_UPLIFT_PCT` / `PILOT_CI_LOW` / `PILOT_CI_HIGH`. Defaults carry the forecast benchmark (+30.1% pooled, which absorbs +9.7% market drift) with an explicit origin label in `validation_reason`; set them to the causal DiD estimate (2.84 / −0.5 / 6.2) to gate on causal impact, matching Part 3's 3% target
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
2. dunnhumby — *Retail:Vision* (2026) — connected AI-powered decision making (series motivation)
3. WARC — *ROI of Successful Campaigns Continues to Grow* (ROI benchmark used in Part 1)
4. Part-1 notebook — `store_performance_analysis_with_DiD.ipynb`, DiD Validation section (causal estimates that gate this system's rollout)

