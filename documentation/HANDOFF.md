# Pair A to Pair B Handoff

Three feature tables in `data/features/`, plus one combined file for the record:

| File | Rows | Columns | Grain |
|---|---|---|---|
| item_features.parquet | 161 | 15 | one row per dish |
| customer_rfm.parquet | 31,042 | 4 | one row per customer with >=1 completed order |
| order_lines_features.parquet | 1,091,111 | 20 | one row per order line (cancelled lines included, flagged) |
| output/dineiq_final_dataset.parquet | 1,091,111 | 20 | copy of order_lines_features.parquet |

Load any of them like this:

```python
df = spark.read.parquet("data/features/item_features.parquet")
```
or in pandas (needs `pip install pyarrow`):

```python
import pandas as pd
df = pd.read_parquet("data/features/item_features.parquet")
```

Feature formulas are in FEATURE_DICTIONARY.md. Cleaning rules are in CLEANING_RULES.md. The join order is in DATA_MODEL.md.
