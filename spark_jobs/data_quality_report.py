"""
data_quality_report.py  --  Document 1, Step 4: Data Quality Report

Checks every one of the 11 tables for missing values, duplicates and the
specific business-rule problems this dataset is known to contain, and
writes the results to DATA_QUALITY_REPORT.md. This step only LOOKS -- it
changes nothing. clean_data.py (Step 5) is where fixes happen.

Run from your project root:
    python pair_a_data/data_quality_report.py
"""
import os

if os.name == "nt":  # Windows only
    os.environ["HADOOP_HOME"] = r"C:\hadoop"
    os.environ["PATH"] += r";C:\hadoop\bin"

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, current_date, try_to_date, to_date, lower, trim, initcap, lit

spark = SparkSession.builder.appName("DineIQ_DataQuality").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

DATA_DIR = "data/raw"
TABLES = [
    "menu_categories", "menu_items", "restaurants", "customers",
    "pricing_history", "promotions", "orders", "order_items",
    "ratings", "inventory", "wastage",
]

dfs = {}
for t in TABLES:
    path = f"{DATA_DIR}/order_items/*.csv" if t == "order_items" else f"{DATA_DIR}/{t}.csv"
    dfs[t] = spark.read.csv(path, header=True, inferSchema=True)

lines = []


def log(text=""):
    print(text)
    lines.append(text)


def missing_counts(df):
    row = df.select([count(when(col(c).isNull(), c)).alias(c) for c in df.columns]).collect()[0]
    return {c: row[c] for c in df.columns if row[c] and row[c] > 0}


# Business rules: anything matching a condition here is a bad record.
# These target the specific problems this generator plants on purpose.
rules = {
    "orders": [
        # try_to_date returns NULL instead of throwing on unparseable input (e.g. "2025-13-45" --
        # a planted defect). Plain to_date() hard-crashes the whole job under Spark's ANSI mode.
        ("order_date cannot be parsed as a date", try_to_date(col("order_date"), "yyyy-MM-dd").isNull() & col("order_date").isNotNull()),
        ("order_date is in the future", try_to_date(col("order_date"), "yyyy-MM-dd") > current_date()),
        ("order_date is implausibly old (before 2015)", try_to_date(col("order_date"), "yyyy-MM-dd") < to_date(lit("2015-01-01"))),
        ("invalid location_id (not a real branch)", ~col("location_id").isin([f"L{i:02d}" for i in range(1, 21)])),
        ("channel needs standardising (case/spacing)", col("channel").isNotNull() & (col("channel") != initcap(trim(col("channel"))))),
        ("status needs standardising (case/spacing)", col("status") != initcap(trim(lower(col("status"))))),
    ],
    "order_items": [
        ("quantity is zero or negative", col("quantity") <= 0),
        ("unit_price is zero or negative", col("unit_price") <= 0),
        ("discount_pct outside 0-100", (col("discount_pct") < 0) | (col("discount_pct") > 100)),
    ],
    "ratings": [
        ("rating_value outside 1-5", (col("rating_value") < 1) | (col("rating_value") > 5)),
    ],
    "wastage": [
        ("quantity_wasted is impossible (<=0 or >1000)", (col("quantity_wasted") <= 0) | (col("quantity_wasted") > 1000)),
    ],
    "inventory": [
        ("closing_stock is negative", col("closing_stock") < 0),
        ("unit is not lower-case", col("unit") != lower(col("unit"))),
    ],
}

log("# DineIQ Data Quality Report\n")
log("Produced by data_quality_report.py (Spark). Nothing is changed in this step.\n")

menu_ids = dfs["menu_items"].select("item_id").distinct()
order_ids = dfs["orders"].select("order_id").distinct()

for name, df in dfs.items():
    total = df.count()
    dupes = total - df.dropDuplicates().count()

    log(f"## {name}")
    log(f"- Rows: {total:,}")
    log(f"- Exact duplicate rows: {dupes:,}")

    missing = missing_counts(df)
    if missing:
        for c, n in missing.items():
            log(f"- Missing {c}: {n:,} ({n / total:.2%})")
    else:
        log("- No missing values")

    for label, condition in rules.get(name, []):
        n = df.filter(condition).count()
        log(f"- {label}: {n:,}")

    # referential-integrity checks that need a second table
    if name == "order_items":
        n = df.filter(col("item_id").isNotNull()).join(menu_ids, "item_id", "left_anti").count()
        log(f"- item_id not found in menu_items (unknown dish): {n:,}")
        n = df.join(order_ids, "order_id", "left_anti").count()
        log(f"- order_id not found in orders (orphan line): {n:,}")
    if name == "ratings":
        n = df.join(order_ids, "order_id", "left_anti").count()
        log(f"- order_id not found in orders (orphan rating): {n:,}")

    log()

with open("DATA_QUALITY_REPORT.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Saved DATA_QUALITY_REPORT.md")
