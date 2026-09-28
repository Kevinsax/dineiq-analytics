"""
classify_spark.py  --  Document 4, Step 2: Item Classification, the Spark path (Partner 1)

Labels every dish as Profit Driver / Volume Driver / Hidden Opportunity /
Low Performer using Spark SQL CASE WHEN against the median profit_margin
and median total_quantity_sold -- a rule-based split, no MLlib required.

Build this WITHOUT looking at Partner 2's plain-Python version (Step 3).
The comparison in Step 4 only means something if the two were genuinely
independent.

Windows note: same Hadoop patch as every other Spark script in this
project. Not needed on Mac.

Run from your project root, after Pair A has produced data/features/:
    python pair_b_models/classify_spark.py
"""
import os

if os.name == "nt":  # Windows only
    os.environ["HADOOP_HOME"] = r"C:\hadoop"
    os.environ["PATH"] += r";C:\hadoop\bin"

from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("DineIQ_Classify_Spark").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

items = spark.read.parquet("data/features/item_features.parquet")
print(f"Loaded item_features.parquet: {items.count():,} rows")

items.createOrReplaceTempView("items")

labeled = spark.sql("""
    SELECT *,
        CASE
            WHEN profit_margin >= (SELECT percentile_approx(profit_margin, 0.5) FROM items)
             AND total_quantity_sold >= (SELECT percentile_approx(total_quantity_sold, 0.5) FROM items)
                THEN 'Profit Driver'
            WHEN profit_margin < (SELECT percentile_approx(profit_margin, 0.5) FROM items)
             AND total_quantity_sold >= (SELECT percentile_approx(total_quantity_sold, 0.5) FROM items)
                THEN 'Volume Driver'
            WHEN profit_margin >= (SELECT percentile_approx(profit_margin, 0.5) FROM items)
             AND total_quantity_sold < (SELECT percentile_approx(total_quantity_sold, 0.5) FROM items)
                THEN 'Hidden Opportunity'
            ELSE 'Low Performer'
        END AS spark_label
    FROM items
""")

# print the two threshold values actually used, for the report
thresholds = spark.sql("""
    SELECT percentile_approx(profit_margin, 0.5) AS median_margin,
           percentile_approx(total_quantity_sold, 0.5) AS median_units
    FROM items
""").collect()[0]
print(f"\nThresholds used: median profit_margin = {thresholds['median_margin']:.4f}, "
      f"median total_quantity_sold = {thresholds['median_units']:.0f}")

print("\nLabel counts:")
labeled.groupBy("spark_label").count().orderBy("spark_label").show()

os.makedirs("data/models", exist_ok=True)
labeled.write.mode("overwrite").parquet("data/models/item_classification_spark.parquet")
print("Saved data/models/item_classification_spark.parquet")

# item_features is one row per dish (161 rows), so pulling it into pandas here is
# trivial -- this .csv is what's easiest to open in Excel and send to your partner.
labeled.toPandas().to_csv("data/models/item_classification_spark.csv", index=False)
print("Saved data/models/item_classification_spark.csv (open this one in Excel)")

with open("CLASSIFICATION_SPARK_NOTES.md", "w", encoding="utf-8") as f:
    f.write("# Spark Classification -- Thresholds\n\n")
    f.write(f"- median profit_margin: {thresholds['median_margin']:.4f}\n")
    f.write(f"- median total_quantity_sold: {thresholds['median_units']:.0f}\n\n")
    f.write("| Label | Count |\n|---|---|\n")
    for row in labeled.groupBy("spark_label").count().collect():
        f.write(f"| {row['spark_label']} | {row['count']:,} |\n")
print("Saved CLASSIFICATION_SPARK_NOTES.md")
