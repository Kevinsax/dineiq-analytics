"""
ingest.py  --  Document 1, Step 3: Spark Ingestion

What this does: loads all 11 raw CSV tables into Spark DataFrames, prints
each schema and row count, so you can see what Spark thinks each column's
data type is before you clean anything in Step 4/5.

Run from your project root (the folder that contains data/), not from
inside pair_a_data/:
    python pair_a_data/ingest.py

Windows note: Spark needs a small Hadoop helper (winutils.exe + hadoop.dll)
to write files locally. This script only READS, so it will run without
that fix -- but every later script (clean_data.py onward) writes Parquet
and needs it. See Document 3 for the one-time HADOOP_HOME setup, or the
os.environ block copied into every later script here.
"""
import os

if os.name == "nt":  # Windows only -- macOS/Linux never need this
    os.environ["HADOOP_HOME"] = r"C:\hadoop"
    os.environ["PATH"] += r";C:\hadoop\bin"

from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("DineIQ_Ingestion").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

DATA_DIR = "data/raw"

# order_items is delivered as several monthly files (one CSV per month),
# not a single file -- a "*" wildcard reads all of them as one DataFrame.
CSV_FILES = {
    "customers": "customers.csv",
    "inventory": "inventory.csv",
    "menu_categories": "menu_categories.csv",
    "menu_items": "menu_items.csv",
    "order_items": "order_items/*.csv",
    "pricing_history": "pricing_history.csv",
    "promotions": "promotions.csv",
    "ratings": "ratings.csv",
    "restaurants": "restaurants.csv",
    "wastage": "wastage.csv",
    "orders": "orders.csv",
}

dataframes = {}
for name, filename in CSV_FILES.items():
    df = spark.read.csv(f"{DATA_DIR}/{filename}", header=True, inferSchema=True)
    dataframes[name] = df
    print(f"\n{name} schema:")
    df.printSchema()
    print(f"{name} row count: {df.count():,}")

print("\nAll 11 tables loaded. Row counts above are what Step 4's Data Quality")
print("Report should also see -- if a number here looks off, check the file path first.")
