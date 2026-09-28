"""
clean_data.py  --  Document 1, Step 5: Data Cleaning

Applies one clear, defensible rule per problem found in Step 4, prints
before/after row counts for every rule, and writes CLEANING_RULES.md so
the "why did you drop this record?" question always has an answer.

Cancelled orders are KEPT -- "Cancelled" is a valid status, not an error.
Filter status == "Completed" later when calculating revenue (Step 7 does
this for you).

Run from your project root:
    python pair_a_data/clean_data.py
"""
import os

if os.name == "nt":  # Windows only
    os.environ["HADOOP_HOME"] = r"C:\hadoop"
    os.environ["PATH"] += r";C:\hadoop\bin"

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, try_to_date, initcap, trim, lower, lit

spark = SparkSession.builder.appName("DineIQ_Cleaning").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"

TABLES = [
    "menu_categories", "menu_items", "restaurants", "customers",
    "pricing_history", "promotions", "orders", "order_items",
    "ratings", "inventory", "wastage",
]

raw = {}
for t in TABLES:
    path = f"{RAW_DIR}/order_items/*.csv" if t == "order_items" else f"{RAW_DIR}/{t}.csv"
    raw[t] = spark.read.csv(path, header=True, inferSchema=True)

VALID_LOCATIONS = [f"L{i:02d}" for i in range(1, 21)]
clean = {}
summary = []  # (table, rule, rows removed)


def apply(table, before, rule, after):
    removed = before.count() - after.count()
    summary.append((table, rule, removed))
    print(f"{table:16s} | {rule:55s} | removed {removed:,}")
    return after


# ---- menu_items, restaurants: needed by later filters, clean first ----
menu = raw["menu_items"]
clean["menu_items"] = apply("menu_items", menu, "exact duplicate rows", menu.dropDuplicates())

restaurants = raw["restaurants"]
clean["restaurants"] = apply("restaurants", restaurants, "exact duplicate rows", restaurants.dropDuplicates())

# ---- orders ----
orders = raw["orders"]
orders = apply("orders", orders, "exact duplicate rows", orders.dropDuplicates())
orders = apply("orders", orders, "missing customer_id", orders.filter(col("customer_id").isNotNull()))
orders = apply("orders", orders, "invalid location_id (not a real branch)",
               orders.filter(col("location_id").isin(VALID_LOCATIONS)))
# try_to_date returns NULL instead of throwing on unparseable input (e.g. "2025-13-45" --
# a planted defect). Plain to_date() hard-crashes the whole job under Spark's ANSI mode.
orders = orders.withColumn("_parsed_order_date", try_to_date(col("order_date"), "yyyy-MM-dd"))
orders = apply("orders", orders, "order_date cannot be parsed",
               orders.filter(col("_parsed_order_date").isNotNull()))
orders = apply("orders", orders, "order_date implausible (before 2015 or after today)",
               orders.filter((col("_parsed_order_date") >= to_date(lit("2015-01-01")))
                             & (col("_parsed_order_date") <= to_date(lit("2026-09-28")))))
orders = orders.drop("_parsed_order_date")
# standardise text: "dine-in" / "DINE-IN " -> "Dine-in", "cancelled " -> "Cancelled"
orders = orders.withColumn("channel", initcap(trim(col("channel")))) \
               .withColumn("status", initcap(trim(lower(col("status")))))
clean["orders"] = orders

# ---- order_items ----
items = raw["order_items"]
items = apply("order_items", items, "exact duplicate rows", items.dropDuplicates())
items = apply("order_items", items, "missing item_id", items.filter(col("item_id").isNotNull()))
items = apply("order_items", items, "unknown item_id (not in menu_items)",
              items.join(clean["menu_items"].select("item_id"), "item_id", "left_semi"))
items = apply("order_items", items, "quantity is zero or negative", items.filter(col("quantity") > 0))
items = apply("order_items", items, "unit_price is zero or negative", items.filter(col("unit_price") > 0))
items = apply("order_items", items, "discount_pct outside 0-100",
              items.filter(col("discount_pct").between(0, 100)))
items = apply("order_items", items, "orphan lines (order was dropped or never existed)",
              items.join(clean["orders"].select("order_id"), "order_id", "left_semi"))
clean["order_items"] = items

# ---- ratings ----
ratings = raw["ratings"]
ratings = apply("ratings", ratings, "exact duplicate rows", ratings.dropDuplicates())
ratings = apply("ratings", ratings, "rating_value outside 1-5", ratings.filter(col("rating_value").between(1, 5)))
ratings = apply("ratings", ratings, "orphan rating (order was dropped or never existed)",
                ratings.join(clean["orders"].select("order_id"), "order_id", "left_semi"))
# missing customer_id on a rating is left as null -- the rating still counts toward the
# dish's average, it just can't be tied to a specific customer's history
clean["ratings"] = ratings

# ---- customers: missing signup_date stays null, standardise city casing ----
customers = raw["customers"]
customers = apply("customers", customers, "exact duplicate rows", customers.dropDuplicates())
customers = customers.withColumn("home_city", initcap(trim(col("home_city"))))
clean["customers"] = customers

# ---- wastage ----
wastage = raw["wastage"]
wastage = apply("wastage", wastage, "exact duplicate rows", wastage.dropDuplicates())
wastage = apply("wastage", wastage, "impossible quantity_wasted (<=0 or >1000)",
                wastage.filter(col("quantity_wasted").between(1, 1000)))
wastage = apply("wastage", wastage, "invalid location_id", wastage.filter(col("location_id").isin(VALID_LOCATIONS)))
wastage = apply("wastage", wastage, "missing item_id", wastage.filter(col("item_id").isNotNull()))
wastage = apply("wastage", wastage, "unknown item_id (not in menu_items)",
                wastage.join(clean["menu_items"].select("item_id"), "item_id", "left_semi"))
clean["wastage"] = wastage

# ---- inventory ----
inventory = raw["inventory"]
inventory = apply("inventory", inventory, "exact duplicate rows", inventory.dropDuplicates())
inventory = apply("inventory", inventory, "negative closing_stock", inventory.filter(col("closing_stock") >= 0))
inventory = apply("inventory", inventory, "invalid location_id", inventory.filter(col("location_id").isin(VALID_LOCATIONS)))
inventory = inventory.withColumn("unit", lower(trim(col("unit"))))  # "PORTION" -> "portion"
clean["inventory"] = inventory

# ---- remaining tables: duplicate check only ----
for t in ["menu_categories", "pricing_history", "promotions"]:
    df = raw[t]
    clean[t] = apply(t, df, "exact duplicate rows", df.dropDuplicates())

# ---- save ----
for t, df in clean.items():
    df.write.mode("overwrite").parquet(f"{CLEAN_DIR}/{t}")

print("\nRow counts, raw -> clean")
for t in TABLES:
    print(f"{t:16s} {raw[t].count():>10,} -> {clean[t].count():>10,}")

# ---- cleaning rules file ----
why = {
    "exact duplicate rows": "Same record loaded twice, so one copy is kept.",
    "missing customer_id": "An order with no customer can't feed segmentation or repeat-order features.",
    "invalid location_id (not a real branch)": "A location code that doesn't match any of the 20 real branches -- a data entry error, dropped rather than guessed.",
    "order_date cannot be parsed": "Not a valid calendar date at all (e.g. month 13). Can't be fixed, so the row is dropped.",
    "order_date implausible (before 2015 or after today)": "Dates like 1970-01-01 or next year are clearly wrong, not real orders. Dropped.",
    "missing item_id": "Can't join the line to a dish, so it can't be classified or costed.",
    "unknown item_id (not in menu_items)": "References a dish that doesn't exist on the menu -- a data entry error, dropped.",
    "quantity is zero or negative": "A negative or zero quantity is a data entry error. Dropped rather than guessed.",
    "unit_price is zero or negative": "Nothing on the menu is free or negative, so the price is unusable.",
    "discount_pct outside 0-100": "A discount can't be negative or over 100%. Dropped, since we can't know what was meant.",
    "orphan lines (order was dropped or never existed)": "The parent order was dropped above, so the line has nothing to attach to.",
    "rating_value outside 1-5": "The scale is 1 to 5. Dropped rather than capped, since we can't know what the customer meant.",
    "orphan rating (order was dropped or never existed)": "The order this rating belongs to was dropped, so the rating can't be trusted either.",
    "impossible quantity_wasted (<=0 or >1000)": "Zero or negative waste isn't waste, and over 1000 units in one record is a data entry error, not a real kitchen event.",
    "invalid location_id": "A location code that doesn't match any of the 20 real branches. Dropped.",
    "negative closing_stock": "Stock can't be negative -- a counting error, dropped.",
}

with open("CLEANING_RULES.md", "w", encoding="utf-8") as f:
    f.write("# Cleaning Rules\n\n")
    f.write("| Table | Problem | Why we handled it this way | Rows removed |\n")
    f.write("|---|---|---|---|\n")
    for table, rule, removed in summary:
        f.write(f"| {table} | {rule} | {why.get(rule, '')} | {removed:,} |\n")
    f.write("\nNotes\n\n")
    f.write("- Cancelled orders are kept. Filter `status == \"Completed\"` when calculating revenue.\n")
    f.write("- Missing `signup_date` on a customer is left as null, not guessed.\n")
    f.write("- Missing `customer_id` on a rating is left as null; the rating still counts toward the dish average.\n")
    f.write("- `channel` and `status` on orders, `home_city` on customers, and `unit` on inventory are "
            "standardised to one consistent casing (e.g. \"dine-in\" and \"DINE-IN \" both become \"Dine-in\").\n")

print("\nSaved CLEANING_RULES.md")
