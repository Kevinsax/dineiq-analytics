# DineIQ Analytics

A Big Data & AI-powered restaurant intelligence platform — built for the
Data Science Intelligence Arena competition by **Team Techwizz**, Aptech
Chevron Data Science Class.

DineIQ Analytics ingests a large, realistically messy restaurant operations
dataset through a Spark pipeline, classifies every menu item and customer
using two independently-built pipelines (Spark SQL and plain Python) that are
cross-checked against each other, mines wastage, basket, and demand patterns,
and serves all of it through an interactive Streamlit dashboard with
evidence-backed recommendations.

**Project Report:** [`reports/DineIQ_Project_Report.docx`](reports/DineIQ_Project_Report.docx)
**AI Tool Usage Declaration:** [`AI_USAGE.md`](AI_USAGE.md) — read this too
**Deployed application:** _[https://dineiq-analytics.streamlit.app/]_
**Demonstration video:** _[add your .mp4 / video link here]_
**Technical blog:** _[https://medium.com/@ibkfresh/inside-dineiq-analytics-building-a-dual-pipeline-big-data-brain-for-a-restaurant-chain-6bd99b29bdc2]_

---

## Table of Contents

1. [Folder Structure](#folder-structure)
2. [Results at a Glance](#results-at-a-glance)
3. [Installation Instructions](#installation-instructions)
4. [Regenerating the Full Dataset](#regenerating-the-full-dataset)
5. [Execution Instructions](#execution-instructions)
6. [Running the Tests](#running-the-tests)
7. [Assumptions](#assumptions)
8. [Limitations](#limitations)
9. [Team](#team)

---

## Folder Structure

```
DineIQ-Analytics/
├── README.md                    <- you are here
├── AI_USAGE.md                  <- required AI tool usage declaration
├── LICENSE
├── requirements.txt
├── .gitignore
├── config/
│   └── paths.py                 <- shared folder-path constants
├── data_generator/               <- Step 0: synthetic dataset generator
│   ├── dineiq_generator.py
│   ├── common.py
│   └── validate_dataset.py
├── spark_jobs/                   <- Pair A: Spark ingestion/quality/cleaning/join/features
│   ├── ingest.py
│   ├── data_quality_report.py
│   ├── clean_data.py
│   ├── join_data.py
│   ├── feature_engineering.py
│   ├── export_parquet.py
│   └── quick_look.py
├── spark_sql/                    <- Pair B: Spark SQL classification pipeline
│   └── classify_spark.py
├── python_pipeline/               <- Pair B/C: plain-Python data science pipeline
│   ├── classify_python.py
│   ├── compare_classifications.py
│   ├── rfm_segments.py
│   ├── basket_analysis.py
│   ├── wastage_prediction.py
│   ├── build_forecast.py         <- Pair C addition, closes an SRS gap -- see README below
│   └── build_recommendations.py
├── src/                           <- Pair C: the Streamlit application
│   ├── Executive_Dashboard.py    <- home page (run this with `streamlit run`)
│   ├── utils.py
│   └── pages/
│       ├── 1_Menu_Intelligence.py
│       ├── 2_Customer_Intelligence.py
│       ├── 3_Wastage.py
│       ├── 4_Demand_Forecast.py
│       ├── 5_Dual_Pipeline_Comparison.py
│       ├── 6_Recommendations.py
│       └── 7_What_If_Simulator.py
├── raw_data/                      <- small samples of the 11 raw tables (full raw_data is regenerable, see below)
├── processed_data/                <- notes on the (regenerable) cleaned/joined intermediates
├── parquet_data/                  <- the real, full-scale feature tables Pair A hands off (item_features, customer_rfm, order_lines_features)
├── models/                        <- the real, full-scale model outputs Pair B/C hand off
├── sample_data/                   <- small, ready-to-open CSV samples of the final output
├── notebooks/                     <- (not used -- see notebooks/README.md for why)
├── database/                      <- (not used -- see database/README.md for why)
├── tests/                         <- pytest smoke tests over the feature tables
├── documentation/                 <- all real process-documentation .md files, the execution log, diagrams, and the pair guides
├── reports/                       <- the Project Report (.docx)
├── screenshots/                   <- add app screenshots here before submission
├── templates/, static/            <- not applicable to a Streamlit app -- kept to match required structure
```

## Results at a Glance

| Stage | Headline result |
|---|---|
| Dataset generated | 11 raw tables, 1,717,201 rows (fixed seed, fully reproducible) |
| Data cleaning | Every defect counted before cleaning; e.g. 6,702 duplicate order lines, 899 duplicate orders — all documented row-by-rule in `documentation/CLEANING_RULES.md` |
| Feature engineering | 1,091,111 order lines, 31,042 customers, 161 items — all keys preserved, 0 unmatched rows on every operational join |
| Menu classification | **100% agreement between the independent Spark SQL and Python pipelines — 161/161 dishes**, including all 6 deliberately-planted tricky test cases |
| Customer segmentation | 8,700 Loyal High Spenders, 5,192 At Risk, 3,253 New, 13,897 Regular (of 31,042 segmented customers) |
| Market-basket analysis | 1,124 association rules found from 104,851 multi-item completed orders |
| Wastage-risk ranking | Top predictor: sales volume (importance 0.307); top-5 highest-risk dishes identified and ranked |
| Demand forecast | Beats a naive baseline on 9 of 12 menu categories (by MAE) |
| Recommendation engine | Evidence-backed, priority-tiered recommendations generated across 7 rule categories |

Full detail, methodology, and an honest account of what was and wasn't
built is in [`reports/DineIQ_Project_Report.docx`](reports/DineIQ_Project_Report.docx).

## Installation Instructions

**Supported OS:** Windows 10/11 or macOS (both used and verified by the team).

1. **Python version:** Python 3.10, 3.11, or 3.12. (Avoid installing Python
   from the Microsoft Store on Windows — a Store-distributed interpreter can
   trigger a Windows Application Control policy block on native DLLs used by
   scipy/scikit-learn. Install from [python.org](https://www.python.org/downloads/) instead.)
2. **Java installation** (required for PySpark): install a JDK matching your
   PySpark version — JDK 11 or 17 is recommended. Verify with `java -version`.
3. **Apache Spark installation:** PySpark is installed via `pip` below and
   bundles Spark itself — no separate Spark download is required for local
   use.
4. **PySpark configuration (Windows only):** PySpark on Windows needs the
   Hadoop `winutils.exe` patch. Download a `winutils.exe` matching your
   Hadoop version, place it in `C:\hadoop\bin\`, and set the environment
   variable `HADOOP_HOME=C:\hadoop` (and add `%HADOOP_HOME%\bin` to `PATH`).
   macOS/Linux users can skip this step.
5. **Virtual environment creation:**
   ```
   python -m venv venv
   venv\Scripts\activate        (Windows)
   source venv/bin/activate     (macOS/Linux)
   ```
6. **Python dependency installation:**
   ```
   pip install -r requirements.txt
   ```
7. **Database setup:** not applicable — this project reads Parquet/CSV files
   directly rather than a database. See `database/README.md`.

## Regenerating the Full Dataset

`raw_data/` in this repository holds small samples (a few hundred rows per
table) rather than the full 1.7-million-row dataset, to keep the repository
lightweight. The full dataset is **exactly reproducible** because the
generator uses a fixed random seed:

```
python data_generator/dineiq_generator.py --scale full --seed 42
```

This produces the same 11 tables (customers, orders, order_items, menu_items,
menu_categories, restaurants, ratings, pricing_history, promotions,
inventory, wastage) with the same row counts and the same planted data
defects and tricky test cases documented in this project's report, into a
local `data/raw/` folder. Use `--scale dev --seed 42` for a small (~1 minute)
version while testing.

## Execution Instructions

Run every command below from the project root, with your virtual environment
activated. Steps must be run **in order** — each one reads the previous
step's output.

**1. Generate the dataset**
```
python data_generator/dineiq_generator.py --scale full --seed 42
```

**2. Run Spark processing (ingestion → quality → cleaning → joining → features → export)**
```
python spark_jobs/ingest.py
python spark_jobs/data_quality_report.py
python spark_jobs/clean_data.py
python spark_jobs/join_data.py
python spark_jobs/feature_engineering.py
python spark_jobs/export_parquet.py
```
This is also where Spark SQL is executed — `join_data.py` and
`classify_spark.py` (next step) both run their logic as Spark SQL queries,
not just DataFrame API calls.

**3. Train/run the Spark model and the Python model, then compare them**
```
python spark_sql/classify_spark.py
python python_pipeline/classify_python.py
python python_pipeline/compare_classifications.py
```

**4. Run the remaining Python Data Science pipeline**
```
python python_pipeline/rfm_segments.py            # customer segments
python python_pipeline/basket_analysis.py          # market-basket analysis
python python_pipeline/wastage_prediction.py       # wastage-risk ranking
python python_pipeline/build_forecast.py           # demand forecast
python python_pipeline/build_recommendations.py    # recommendation engine (run last -- reads everything above)
```

**5. Launch the dashboard application**

Run this from the **repo root** (not from inside `src/`) — `utils.py` loads
data using paths like `parquet_data/...` and `models/...`, which only
resolve correctly if Streamlit's working directory is the repo root:
```
streamlit run src/Executive_Dashboard.py
```
This opens the Executive Dashboard in your browser, with the other seven
pages listed in the sidebar. From here you can: view customer segments
(Customer Intelligence page), perform menu analysis (Menu Intelligence
page), view the market-basket rules and recommendations (Recommendations
page), view demand forecasts (Demand Forecast page), analyze wastage
(Wastage page), perform what-if analysis (What-If Simulator page), and
compare the Spark/Python pipelines (Dual-Pipeline Comparison page). Every
page has date/location/category/channel filters in the sidebar and a
"Download (CSV)" button to export what's currently shown.

**6. Execute automated tests**
```
pytest tests/ -v
```

## Deploying to Streamlit Community Cloud

The dashboard only needs `pandas`, `numpy`, `pyarrow`, `plotly`,
`scikit-learn` and `streamlit` at runtime — it reads the pre-computed
`parquet_data/` and `models/` files directly, so PySpark/Java/mlxtend
(needed only to *build* those files, not to serve the dashboard) are
deliberately **not** installed on the deployed app. `src/requirements.txt`
lists only what the app needs; Streamlit Cloud automatically prefers a
`requirements.txt` in the same folder as the main script over the one at
the repo root.

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   your GitHub account.
2. Click **New app** → **Deploy a public app from GitHub**.
3. Repository: `Kevinsax/dineiq-analytics`. Branch: `main`.
   Main file path: `src/Executive_Dashboard.py`.
4. Click **Deploy**. The first build takes a couple of minutes while it
   installs `src/requirements.txt`.
5. Once it's live, copy the app's URL (`https://<something>.streamlit.app`)
   into this README's top section and into your Project Report /
   submission checklist as the Deployed Application URL (SRS Section
   1.10, Item 13).

**Login:** this application has no authentication layer in this submission
(see Limitations) — there is no login step.

**Troubleshooting:** see `documentation/DineIQ_Execution_Log.txt` for the
team's real, detailed run log including exact errors hit and how each was
resolved (date-parsing errors, Parquet folder-vs-file confusion, and a
Windows DLL-blocking issue), and `documentation/DineIQ_1_PairA_StepByStep_Guide.docx`
/ `documentation/DineIQ_5_PairC_StepByStep_Guide.docx` for fully worked,
screenshot-level walkthroughs of each stage.

## Running the Tests

```
pip install pytest
pytest tests/ -v
```
`tests/test_feature_tables.py` checks that the three feature tables in
`parquet_data/` have the expected grain, required columns, and sane value
ranges — a fast way to catch a broken upstream change before it reaches the
dashboard.

## Assumptions

- The dataset is synthetically generated (with a fixed seed for
  reproducibility) rather than sourced from a real restaurant chain.
- "Completed" orders are the basis for all revenue/profit/demand
  calculations; cancelled orders are retained but flagged (`is_completed`),
  not deleted.
- Local execution/deployment is an accepted fallback to a public URL, per
  SRS Section 1.10, Item 13.

Full assumptions and constraints are in the Project Report, Sections 6–7.

## Limitations

Stated plainly, in full in the Project Report (Section 38):

- No database backend — flat Parquet/CSV files instead.
- No user authentication or audit trail.
- No Spark job monitoring dashboard.
- The demand forecast underperforms its own naive baseline on 3 of 12
  categories (Snacks & Small Chops, Specials & Combos, Stews & Sauces).
- No dedicated pricing-elasticity or promotion-effectiveness model was
  fitted (the What-If Simulator uses a user-adjustable estimate instead).
- No formal statistical anomaly-detection model.
- No automated CI pipeline; `tests/` is a manually-run smoke-test suite.

## Team

**Team Techwizz** — Aptech Chevron Data Science Class, Data Science
Intelligence Arena competition.

| Pair | Responsibility | Member(s) |
|---|---|---|
| Pair A | Big Data Foundation (Spark ingestion, quality, cleaning, joins, features) | _Nmesoma, Irene Okoji_ |
| Pair B | Data Science & Machine Learning (classification, segmentation, basket analysis, wastage) | _Adeshina Adekunle , Caleb Edoho_ |
| Pair C | Application & Visualization (forecasting, recommendations, Streamlit dashboard) | _Oyibo Nuhu, Anieto_ |

**Evaluator / administrator login credentials:** not applicable — the
application has no authentication layer (see Limitations).
