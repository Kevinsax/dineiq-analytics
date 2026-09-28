"""
join_data.py  --  Document 1, Step 6: Data Integration (Joins)

Connects the cleaned tables into one wide table: one row per order line,
with the customer, dish, category, branch, current price and average
rating all attached. Every join is a LEFT join starting from order_items,
so the row count must stay exactly the same after every step -- if it
doesn't, print a BALLOON or UNMATCHED warning so you catch it immediately
instead of finding out from Pair B three days later.

Run from your project root, after clean_data.py has produced data/clean/:
    python pair_a_data/join_data.py
"""
import os

if os.name == "nt":  # Windows only
    os.environ["HADOOP_HOME"] = r"C:\hadoop"
    os.environ["PATH"] += r";C:\hadoop\bin"

from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.appName("DineIQ_Joins").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

CLEAN_DIR = "data/clean"
OUT_DIR = "data/joined"


def load(table):
    return spark.read.parquet(f"{CLEAN_DIR}/{table}")


def dup_key_count(df, keys):
    return df.groupBy(*keys).count().filter(F.col("count") > 1).count()


log = []


def join_step(name, left, right, key, why, full_match=True):
    keys = [key] if isinstance(key, str) else key
    before = left.count()
    dups = dup_key_count(right, keys)
    unmatched = left.join(right.select(*keys).distinct(), keys, "left_anti").count()

    out = left.join(right, keys, "left").cache()
    after = out.count()

    flags = []
    if after > before:
        flags.append(f"BALLOON (+{after - before:,} rows)")
    if full_match and unmatched > 0:
        flags.append(f"UNMATCHED ({unmatched:,} rows found no partner)")
    result = ", ".join(flags) if flags else "ok"

    print(f"{name:16s} {before:>10,} -> {after:>10,} | "
          f"duplicate keys on right: {dups:>4,} | unmatched: {unmatched:>8,} | {result}")
    log.append((name, ", ".join(keys), why, before, after, unmatched, result))
    return out


# base table: one row per order line. The date comes from orders instead,
# since order_items itself has no date column in this dataset.
lines = load("order_items")
start_rows = lines.count()

orders = load("orders").select(
    "order_id", "customer_id", "location_id", "order_datetime",
    "order_date", "channel", "payment_method", "status",
)

# category_id is what menu_categories joins on -- selecting it here is
# what makes that join work at all.
menu = load("menu_items").select(
    "item_id", "item_name", "category_id", "base_cost", "is_active", "introduced_date"
)

categories = load("menu_categories")

customers = load("customers").select(
    "customer_id",
    F.col("home_city").alias("customer_city"),
    "age_bracket",
    "signup_date",
)

restaurants = load("restaurants").select(
    "location_id",
    "restaurant_name",
    F.col("city").alias("location_city"),
    "area",
)

# pricing_history has several rows per item, so joining it raw would
# multiply every order line. Collapse it to one row per item first.
prices_raw = load("pricing_history")
pricing = prices_raw.groupBy("item_id").agg(
    F.max_by("price", "effective_from").alias("current_price"),
    F.min_by("price", "effective_from").alias("first_price"),
    (F.count("*") - 1).alias("price_changes"),
)

# same problem with ratings: an order can hold the same dish on more than
# one line, so (order_id, item_id) isn't always unique. Average per pair.
ratings_raw = load("ratings")
ratings = ratings_raw.groupBy("order_id", "item_id").agg(
    F.round(F.avg("rating_value"), 2).alias("avg_rating"),
    F.count("*").alias("n_ratings"),
)

print("Before joining:")
print(f"  items with more than one price row: {dup_key_count(prices_raw, ['item_id']):,} (collapsed to one row each)")
print(f"  order/item pairs with more than one rating: {dup_key_count(ratings_raw, ['order_id', 'item_id']):,} (averaged)")
print(f"  starting order lines: {start_rows:,}\n")

joined = join_step("orders", lines, orders, "order_id",
                   "Adds customer, location, channel, payment and status")
joined = join_step("menu_items", joined, menu, "item_id",
                   "Adds dish name, category_id and unit cost")
joined = join_step("menu_categories", joined, categories, "category_id",
                   "Adds the category name")
joined = join_step("customers", joined, customers, "customer_id",
                   "Adds customer city, age bracket and signup date")
joined = join_step("restaurants", joined, restaurants, "location_id",
                   "Adds branch name, city and area")
joined = join_step("pricing", joined, pricing, "item_id",
                   "Adds current price, launch price and number of price changes")
joined = join_step("ratings", joined, ratings, ["order_id", "item_id"],
                   "Adds average rating. Only some lines were rated, so gaps are normal",
                   full_match=False)

final_rows = joined.count()
print(f"\nFinal rows: {final_rows:,} (started with {start_rows:,})")
if final_rows != start_rows:
    print("WARNING: row count changed, check the flagged joins above.")
else:
    print("Row count unchanged, no balloons.")

joined.write.mode("overwrite").parquet(f"{OUT_DIR}/order_lines_joined")

with open("DATA_MODEL.md", "w", encoding="utf-8") as f:
    f.write("# Data Model: joined order lines\n\n")
    f.write("One row per order line, starting from order_items. Every join is a left join, "
            "so the row count should stay the same after each step.\n\n")
    f.write("| # | Table | Joined on | Why | Rows before | Rows after | Unmatched | Result |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for i, (name, key, why, b, a, u, r) in enumerate(log, 1):
        f.write(f"| {i} | {name} | {key} | {why} | {b:,} | {a:,} | {u:,} | {r} |\n")
    f.write(f"\nFinal table: {final_rows:,} rows, {len(joined.columns)} columns, "
            f"saved to {OUT_DIR}/order_lines_joined\n")

print("Saved DATA_MODEL.md")
