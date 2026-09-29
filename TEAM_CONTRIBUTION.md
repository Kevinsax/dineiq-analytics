# Team Contribution Record

**Project:** DineIQ Analytics
**Team:** Team Techwizz — Aptech Chevron Data Science Class
**Competition:** Data Science Intelligence Arena

This record states what each team member actually did on this project, per
SRS Section 1.10's Final Submission Checklist requirement for a team
contribution record. It complements — and should be read alongside —
`README.md` (folder-level ownership) and `AI_USAGE.md` (who verified each
AI-assisted output).

---

## Team structure

The team organized into three pairs, each owning one stage of the pipeline
end to end — from raw data through to the final deployed application.

| Pair | Members | Responsibility |
|---|---|---|
| Pair A | Nmesoma, Irene Okoji | Big Data Foundation — Spark ingestion, data-quality analysis, cleaning, joins, feature engineering |
| Pair B | Adeshina Adekunle, Caleb Edoho | Data Science & Machine Learning — dual-pipeline classification, customer segmentation, market-basket analysis, wastage-risk prediction |
| Pair C | Oyibo Nuhu, Anieto | Application & Visualization — demand forecasting, recommendation engine, the Streamlit dashboard |

---

## Individual contributions

### Nmesoma — Pair A
- Big Data Foundation work: dataset ingestion and Spark pipeline execution.
- Verified the technical diagrams (architecture, ERD, DFD, use case,
  activity, sequence) against the team's actual join logic and data model
  (`documentation/DATA_MODEL.md`, `documentation/HANDOFF.md`) before they
  were included in the Project Report.

### Irene Okoji — Pair A
- Big Data Foundation work: data-quality analysis and cleaning rules,
  documented in `documentation/CLEANING_RULES.md` and
  `documentation/DATA_QUALITY_REPORT.md`.
- Verified the Project Report's figures against the team's own markdown
  notes and execution log before it was finalized.

### Adeshina Adekunle — Pair B
- Data Science & Machine Learning work: dual-pipeline classification
  (`classify_spark.py`, `classify_python.py`) and the comparison logic.
- Diagnosed and verified the fix for a Spark date-parsing crash
  (`DateTimeException` on malformed dates) during pipeline execution.
- Verified the repository's restructuring into the SRS-required folder
  layout, including `README.md`, `AI_USAGE.md`, `requirements.txt`, and the
  test suite.
- Diagnosed and resolved a Windows environment issue (a Microsoft Store
  Python interpreter triggering a DLL-blocking policy) that was preventing
  scipy/scikit-learn from importing on a team member's machine.

### Caleb Edoho — Pair B
- Data Science & Machine Learning work: customer segmentation (RFM),
  market-basket analysis, and wastage-risk prediction
  (`rfm_segments.py`, `basket_analysis.py`, `wastage_prediction.py`).
- Verified the fix that made the Spark and Python classification outputs
  file-format-consistent (both single-file Parquet plus CSV export) after
  a mismatch was found during the handoff to Pair C.

### Oyibo Nuhu — Pair C
- Application & Visualization work: the eight-page Streamlit dashboard
  (`src/Executive_Dashboard.py` and `src/pages/`), demand forecasting
  (`build_forecast.py`), and the recommendation engine
  (`build_recommendations.py`).
- Verified the deployed application end-to-end on Streamlit Community
  Cloud, confirming the live dashboard's computed totals (revenue, profit,
  orders, active customers, menu item count) matched the pipeline's actual
  output.
- Co-verified the technical diagrams against the data model.

### Anieto — Pair C
- Application & Visualization work: dashboard UI, filters, and the
  What-If Simulator page; ran the full local pipeline end-to-end to confirm
  every page resolved its data correctly after the repository restructuring.
- Co-verified the Pair C application build (forecast numbers and
  recommendation logic) against the team's real full-scale dataset before
  it was accepted into the submission.

---

## How this record was produced

Each pair verified their own section of `AI_USAGE.md` — the "Verified by"
name on each entry is the person who actually ran, tested, and confirmed
that piece of the pipeline, not a nominal sign-off. This document summarizes
those same verifications by person rather than by task, so a reviewer can
see at a glance what each individual contributed.

## Statement

All code, analytical outputs, and documentation in this submission were
produced by the team's own effort, with AI assistance used and declared per
`AI_USAGE.md` where applicable. Every AI-assisted script or document was
independently run, tested, and verified by a named team member before being
accepted into the final submission — consistent with the SRS's requirement
that final analytics, predictions, classifications, and recommendations be
produced by the team's own logic.
