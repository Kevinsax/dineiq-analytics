"""
feature_engineering.py  --  Document 1, Step 7: Feature Engineering

Builds the three tables Pair B actually needs (matches Document 4, Step 1):
  - item_features.parquet     one row per dish   -- for classification (Step 2/3) and wastage prediction (Step 7)
  - customer_rfm.parquet      one row per customer -- for segmentation (Step 5)
  - order_lines_features.parquet  one row per order line -- for market basket analysis (Step 6)

Only COMPLETED orders count toward revenue, profit, ratings-based sales
figures and RFM -- a cancelled order didn't happen, so it can't make a
dish look more (or less) profitable than it is. Cancelled lines are kept
in order_lines_features.parquet so Pair C can still show cancellation
rates, just flagged with is_completed = 0.

Run from your project root, after join_data.py has produced data/joined/:
    python pair_a_data/feature_engineering.py
"""
import os

if os.name == "nt":  # Windows only
    os.environ["HADOOP_HOME"] = r"C:\hadoop"
    os.environ["PATH"] += r";C:\hadoop\bin"

from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.appName("DineIQ_Features").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

JOINED_PATH = "data/joined/order_lines_joined"   # output of join_data.py
CLEAN_DIR = "data/clean"                          # output of clean_data.py
FEATURES_DIR = "data/features"

lines = spark.read.parquet(JOINED_PATH)
start_rows = lines.count()
print(f"Joined order lines loaded: {start_rows:,} rows, {len(lines.columns)} columns")

required = ["order_id", "item_id", "customer_id", "quantity", "unit_price", "discount_pct",
            "base_cost", "status", "order_date", "item_name", "category_id", "category_name"]
missing_cols = [c for c in required if c not in lines.columns]
if missing_cols:
    raise SystemExit(f"The joined table is missing these columns: {missing_cols}\n"
                      f"Actual columns: {lines.columns}\n"
                      f"Did join_data.py finish without errors?")

print("\nOrder statuses in the data (revenue, profit and RFM use 'Completed' only):")
lines.groupBy("status").count().orderBy(F.desc("count")).show()

# ---------------------------------------------------------------------------
# 1. Order-line-level features
# ---------------------------------------------------------------------------
lines = (
    lines
    .withColumn("order_date", F.to_date("order_date"))
    .withColumn("net_revenue", F.col("unit_price") * F.col("quantity") * (1 - F.col("discount_pct") / 100))
    .withColumn("line_cost", F.col("base_cost") * F.col("quantity"))
    .withColumn("line_profit", F.col("net_revenue") - F.col("line_cost"))
    .withColumn("is_completed", (F.col("status") == "Completed").cast("int"))
    .withColumn("day_of_week", F.dayofweek("order_date"))   # 1 = Sunday ... 7 = Saturday
    .withColumn("is_weekend", F.col("day_of_week").isin(1, 7).cast("int"))
)

order_lines_features = lines.select(
    "order_id", "item_id", "item_name", "category_id", "category_name",
    "customer_id", "location_id", "order_date", "channel", "status", "is_completed",
    "quantity", "unit_price", "discount_pct", "net_revenue", "line_cost", "line_profit",
    "day_of_week", "is_weekend", "avg_rating",
).cache()
n_lines = order_lines_features.count()
order_lines_features.write.mode("overwrite").parquet(f"{FEATURES_DIR}/order_lines_features.parquet")
print(f"\nSaved order_lines_features.parquet ({n_lines:,} rows)")

completed = lines.filter(F.col("is_completed") == 1)

# ---------------------------------------------------------------------------
# 2. Customer-level RFM (completed orders only)
# ---------------------------------------------------------------------------
# Recency counts back from the dataset's own latest completed-order date, not
# today's real calendar date -- the dataset stops months ago, so using
# today would make every customer look permanently inactive.
ref_date = completed.agg(F.max("order_date")).collect()[0][0]
print(f"RFM reference date: {ref_date} (the dataset's own latest completed order)\n")

customer_rfm = (
    completed.groupBy("customer_id")
    .agg(
        F.max("order_date").alias("last_order_date"),
        F.countDistinct("order_id").alias("frequency"),
        F.round(F.sum("net_revenue"), 2).alias("monetary"),
    )
    .withColumn("recency_days", F.datediff(F.lit(ref_date), F.col("last_order_date")))
    .drop("last_order_date")
)
n_customers_total = spark.read.parquet(f"{CLEAN_DIR}/customers").count()
n_customers_rfm = customer_rfm.count()
print(f"Customers with at least one completed order: {n_customers_rfm:,} of {n_customers_total:,} total "
      f"(the rest never completed an order and correctly have no RFM row)")
customer_rfm.write.mode("overwrite").parquet(f"{FEATURES_DIR}/customer_rfm.parquet")
print(f"Saved customer_rfm.parquet ({n_customers_rfm:,} rows)")

# ---------------------------------------------------------------------------
# 3. Item-level features (completed orders only)
# ---------------------------------------------------------------------------
item_sales = completed.groupBy("item_id").agg(
    F.first("item_name").alias("item_name"),
    F.first("category_id").alias("category_id"),
    F.first("category_name").alias("category_name"),
    F.first("base_cost").alias("base_cost"),
    F.sum("quantity").alias("total_quantity_sold"),
    F.countDistinct("order_id").alias("n_orders"),
    F.round(F.sum("net_revenue"), 2).alias("net_revenue"),
    F.round(F.sum("line_cost"), 2).alias("total_cost"),
    F.round(F.sum("line_profit"), 2).alias("total_profit"),
    F.round(F.avg("avg_rating"), 3).alias("avg_rating"),
    F.round(F.avg("discount_pct"), 2).alias("avg_discount_pct"),
    F.round(F.avg("is_weekend").cast("double"), 3).alias("weekend_share"),
).withColumn("profit_margin", F.round(F.col("total_profit") / F.col("net_revenue"), 4))

waste_df = spark.read.parquet(f"{CLEAN_DIR}/wastage")
prep_df = spark.read.parquet(f"{CLEAN_DIR}/inventory")
wasted = waste_df.groupBy("item_id").agg(F.sum("quantity_wasted").alias("total_wasted"))
prepared = prep_df.groupBy("item_id").agg(F.sum("prepared_qty").alias("total_prepared"))
item_waste = (
    prepared.join(wasted, "item_id", "left")
    .withColumn("wastage_percent",
                F.when(F.col("total_prepared") > 0,
                       F.round(F.coalesce(F.col("total_wasted"), F.lit(0)) / F.col("total_prepared"), 4)))
    .select("item_id", "wastage_percent")
)

item_features = item_sales.join(item_waste, "item_id", "left")
n_items_menu = spark.read.parquet(f"{CLEAN_DIR}/menu_items").count()
n_items_featured = item_features.count()
print(f"\nItem features built for {n_items_featured:,} of {n_items_menu:,} menu items")
if n_items_featured < n_items_menu:
    print("Some dishes had zero completed sales in this dataset -- they won't have a row here. "
          "That's expected for a brand-new or discontinued item, not a bug.")

item_features.write.mode("overwrite").parquet(f"{FEATURES_DIR}/item_features.parquet")
print(f"Saved item_features.parquet ({n_items_featured:,} rows)")

# ---------------------------------------------------------------------------
# 4. Sanity check: nulls in the key columns Pair B will build on
# ---------------------------------------------------------------------------
print("\nNull counts in item_features (should be 0 everywhere except wastage_percent):")
item_features.select([F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in item_features.columns]).show(vertical=True)

# ---------------------------------------------------------------------------
# 5. Feature dictionary (deliverable for Step 7 -- Pair B's Document 4 reads this)
# ---------------------------------------------------------------------------
dictionary = [
    ("item_features.parquet", "item_id", "profit_margin", "total_profit / net_revenue", "Share of revenue kept as profit. 0.34 means 34%."),
    ("item_features.parquet", "item_id", "total_quantity_sold", "sum(quantity), completed orders only", "How many portions of the dish were sold."),
    ("item_features.parquet", "item_id", "wastage_percent", "sum(quantity_wasted) / sum(prepared_qty), all branches combined", "Share of prepared food that was thrown away. Null means no wastage/inventory record exists for that dish."),
    ("item_features.parquet", "item_id", "avg_rating", "average rating across all completed order lines for the dish", "1 to 5. Null if the dish was never rated."),
    ("item_features.parquet", "item_id", "category_name", "from menu_categories via category_id", "One of the 12 menu categories -- used as a categorical feature in wastage prediction."),
    ("customer_rfm.parquet", "customer_id", "recency_days", "days between the customer's last completed order and the newest completed order in the whole dataset", "Lower means more recently active."),
    ("customer_rfm.parquet", "customer_id", "frequency", "count of distinct completed orders", "How often the customer orders."),
    ("customer_rfm.parquet", "customer_id", "monetary", "sum of net_revenue across completed orders", "How much the customer has spent in total."),
    ("order_lines_features.parquet", "order_id + item_id", "is_completed", "1 if status == 'Completed', else 0", "Cancelled lines are kept but flagged, not dropped -- filter on this before summing revenue."),
    ("order_lines_features.parquet", "order_id + item_id", "net_revenue", "unit_price * quantity * (1 - discount_pct/100)", "Money actually charged for this line, after discount."),
]

with open("FEATURE_DICTIONARY.md", "w", encoding="utf-8") as f:
    f.write("# Feature Dictionary\n\n")
    f.write("Three tables live in `data/features/`. Pair B (Document 4) reads all three directly.\n\n")
    f.write("| File | Grain (one row per) | Feature | Formula | What it means |\n|---|---|---|---|---|\n")
    for file, grain, name, formula, meaning in dictionary:
        f.write(f"| {file} | {grain} | {name} | {formula} | {meaning} |\n")
    f.write(f"\n## Row counts from this run\n\n")
    f.write(f"- item_features.parquet: {n_items_featured:,} rows (of {n_items_menu:,} menu items)\n")
    f.write(f"- customer_rfm.parquet: {n_customers_rfm:,} rows (of {n_customers_total:,} customers)\n")
    f.write(f"- order_lines_features.parquet: {n_lines:,} rows "
            f"(one per order line, cancelled lines included)\n")
    f.write(f"- RFM reference date: {ref_date}\n")

print("\nSaved FEATURE_DICTIONARY.md")
