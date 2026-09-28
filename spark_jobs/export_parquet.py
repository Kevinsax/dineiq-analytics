"""
export_parquet.py  --  Document 1, Step 8: Parquet Export

Reloads each of the three feature tables from disk and confirms the row
count matches what feature_engineering.py just wrote -- this is the
write-then-reload-then-verify pattern the SRS calls proof of proper
Parquet storage. It also copies the order-line table to
output/dineiq_final_dataset.parquet, since that's the single combined
file this step's instructions describe pushing to the shared repo.

Run from your project root, after feature_engineering.py:
    python pair_a_data/export_parquet.py
"""
import os

if os.name == "nt":  # Windows only
    os.environ["HADOOP_HOME"] = r"C:\hadoop"
    os.environ["PATH"] += r";C:\hadoop\bin"

from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("DineIQ_Export").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

FEATURES_DIR = "data/features"
FINAL_PATH = "output/dineiq_final_dataset.parquet"

tables = {}
for name in ["item_features", "customer_rfm", "order_lines_features"]:
    path = f"{FEATURES_DIR}/{name}.parquet"
    df = spark.read.parquet(path)
    n = df.count()
    tables[name] = (df, n)
    print(f"{name}: {n:,} rows, {len(df.columns)} columns -- loaded OK from {path}")

order_lines, n_lines = tables["order_lines_features"]
order_lines.write.mode("overwrite").parquet(FINAL_PATH)
check = spark.read.parquet(FINAL_PATH)
check_rows = check.count()
print(f"\nWritten combined final dataset to {FINAL_PATH}")
print(f"Reloaded row count: {check_rows:,}")
print("Row counts match" if check_rows == n_lines else f"MISMATCH: expected {n_lines:,}, got {check_rows:,}")

print("\nSchema of the final dataset:")
check.printSchema()
print("Preview:")
check.show(5, truncate=False)

with open("HANDOFF.md", "w", encoding="utf-8") as f:
    f.write("# Pair A to Pair B Handoff\n\n")
    f.write("Three feature tables in `data/features/`, plus one combined file for the record:\n\n")
    f.write("| File | Rows | Columns | Grain |\n|---|---|---|---|\n")
    f.write(f"| item_features.parquet | {tables['item_features'][1]:,} | {len(tables['item_features'][0].columns)} | one row per dish |\n")
    f.write(f"| customer_rfm.parquet | {tables['customer_rfm'][1]:,} | {len(tables['customer_rfm'][0].columns)} | one row per customer with >=1 completed order |\n")
    f.write(f"| order_lines_features.parquet | {n_lines:,} | {len(order_lines.columns)} | one row per order line (cancelled lines included, flagged) |\n")
    f.write(f"| output/dineiq_final_dataset.parquet | {check_rows:,} | {len(check.columns)} | copy of order_lines_features.parquet |\n\n")
    f.write("Load any of them like this:\n\n```python\ndf = spark.read.parquet(\"data/features/item_features.parquet\")\n```\n")
    f.write("or in pandas (needs `pip install pyarrow`):\n\n```python\nimport pandas as pd\ndf = pd.read_parquet(\"data/features/item_features.parquet\")\n```\n\n")
    f.write("Feature formulas are in FEATURE_DICTIONARY.md. Cleaning rules are in CLEANING_RULES.md. "
            "The join order is in DATA_MODEL.md.\n")

print("\nSaved HANDOFF.md")
