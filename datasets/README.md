# Datasets

This folder contains the two static CSV files used to seed the Campaign 18 automation system. Both files are derived from the [Dunnhumby Retail Store Public Dataset](https://www.dunnhumby.com/source-files/) and preprocessed from the Part 1 analysis.

These files are hosted on GitHub and fetched directly by the FastAPI app at runtime via raw URL.

---

## customer demographic.csv

Customer-level demographic and RFM segment data used for Best Customer targeting in Campaign 18.

| Column | Description |
|---|---|
| `household_key` | Unique customer identifier |
| `AGE_DESC` | Age bracket of the household head |
| `MARITAL_STATUS_CODE` | Marital status (A = Married, B = Single, etc.) |
| `INCOME_DESC` | Annual household income bracket |
| `HOMEOWNER_DESC` | Homeowner or renter status |
| `HH_COMP_DESC` | Household composition (e.g. 2 Adults No Kids) |
| `HOUSEHOLD_SIZE_DESC` | Number of people in the household |
| `KID_CATEGORY_DESC` | Presence and age category of children |
| `segment_cust` | RFM segment assigned in Part 1 analysis (e.g. Loyal, Best, Promising) |
| `SALES_VALUE` | Total historical sales value for the household |
| `QUANTITY` | Total historical units purchased |

**Used by:** `select_target_customers()` in `main.py` to filter Best Customers matching the Campaign 18 target profile: Age 45-54, Income $50-74K, 2 Adults No Kids.

---

## stores.csv

Store-level performance data used for eligibility scoring and phased rollout filtering.

| Column | Description |
|---|---|
| `STORE_ID` | Unique store identifier |
| `total_customer` | Number of Best Customers associated with the store |
| `SALES_VALUE` | Total historical sales value for the store |
| `QUANTITY` | Total historical units sold |
| `RETAIL_DISC` | Total retail discounts applied |
| `cumpercent` | Cumulative revenue percentage used in Pareto segmentation |

**Used by:** `filter_stores_by_phase()` in `main.py` to select eligible stores per rollout phase based on `total_customer` and `SALES_VALUE` thresholds.

---

## Source

Both files are derived from the Dunnhumby The Complete Journey dataset. For the full preprocessing and segmentation methodology see [Part 1 — Retail Store Performance Analysis](https://github.com/ashishkumar-ds/dunnhumby-retail-performance).

