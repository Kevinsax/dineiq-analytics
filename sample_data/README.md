# sample_data/

Small, ready-to-open CSV samples so a grader can look at real output without
installing PySpark, pyarrow, or cloning the full data/ folder.

| File | What it is | Rows |
|---|---|---|
| item_features_classified_sample.csv | Every menu item, with its profit_margin/volume classification label | 161 (full table -- it's small) |
| recommendations_sample.csv | The rule-based recommendation engine's full output | all generated recommendations |
| basket_rules_sample.csv | Market-basket association rules, sorted by lift | all 1,124 rules |

For the full-scale, order-line-grain data (1,091,111 rows), see `parquet_data/`
(the real Parquet files are included there in full -- they're only ~22MB) or
regenerate everything from scratch with `data_generator/dineiq_generator.py`
(fixed seed, so the regenerated dataset is identical -- see the root README).
