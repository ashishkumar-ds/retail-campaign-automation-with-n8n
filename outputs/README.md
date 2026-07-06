# Outputs

This folder contains execution output samples from a live Campaign 18 automation run, demonstrating the system working end-to-end across all three layers: orchestration, API, and stakeholder communication.

---

## n8n Workflow Execution

**File:** [`n8n_workflow_execution.jpg`](https://github.com/ashishkumar-ds/retail-campaign-automation-with-n8n/blob/main/outputs/n8n%20workflow%20execution.jpg)

Shows the 7-node n8n workflow after a successful campaign run. The execution path follows: Schedule Trigger → Run Campaign API → Execution Successful? → Advance Phase → Prepare Audit Log → Send Gmail. The false branch (Failure Log) is visible but inactive, confirming the run completed without errors.

---

## API Response

**File:** [`api_response.jpg`](https://github.com/ashishkumar-ds/retail-campaign-automation-with-n8n/blob/main/outputs/api%20response.jpg)

Shows the structured JSON output returned by the `/run-campaign` endpoint after a Pilot phase execution. Key fields visible:

- `phase`: Pilot
- `stores_selected`: number of stores that met eligibility criteria
- `customers_targeted`: Best Customers identified for campaign delivery
- `campaign`: Campaign 18
- `target_segment`: Age 45-54 | Income 50-74K | 2 Adults No Kids
- `timing`: 12 PM - 6 PM
- `benchmark_sales_uplift`: 10.7%
- `rollout_decision`: ADVANCE_PHASE
- `rollout_status`: Pilot execution completed

---

## Stakeholder Email Alert

**File:** [`stakeholder_email.jpg`](https://github.com/ashishkumar-ds/retail-campaign-automation-with-n8n/blob/main/outputs/stakeholder%20email.jpg)

Shows the automated Gmail notification sent by n8n after the Pilot phase completed successfully. The email confirms:

- Campaign 18 executed successfully
- Phase: Pilot
- Stores qualified and customers targeted
- Benchmark: 10.7% Historical Sales Growth
- Decision: Advance to Phase 1
- Timestamp of execution

Sent automatically via n8n to the designated stakeholder email address.

