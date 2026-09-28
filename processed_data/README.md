# processed_data/

This folder is intentionally empty of large files. The pipeline's intermediate
cleaned and joined tables (data/clean/ and data/joined/ in a full local run)
are large (tens of MB each) and are not final deliverables in themselves --
they are fully reproducible by running the Spark jobs in `spark_jobs/` in
order against `raw_data/` (or the full regenerated dataset):

```
python spark_jobs/ingest.py
python spark_jobs/data_quality_report.py
python spark_jobs/clean_data.py
python spark_jobs/join_data.py
```

The final, analysis-ready output of this stage is what matters for grading
and is included in full under `parquet_data/`.
