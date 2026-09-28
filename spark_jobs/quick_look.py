"""
quick_look.py  --  Document 1, Step 2: a fast peek at the mess baked into the data

Pure pandas, no Spark -- just a quick eyeball before the real (Spark)
Data Quality Report in Step 4. Run from your project root:
    python pair_a_data/quick_look.py
"""
import pandas as pd

orders = pd.read_csv("data/raw/orders.csv")
print("=== orders ===")
print("Missing values per column:")
print(orders.isnull().sum())
print("Duplicate rows:", orders.duplicated().sum())

inventory = pd.read_csv("data/raw/inventory.csv")
print("\n=== inventory ===")
print("Missing values per column:")
print(inventory.isnull().sum())
print("Duplicate rows:", inventory.duplicated().sum())

ratings = pd.read_csv("data/raw/ratings.csv")
print("\n=== ratings ===")
print("Missing values per column:")
print(ratings.isnull().sum())
print("Duplicate rows:", ratings.duplicated().sum())
print("Ratings outside 1-5:", (~ratings.rating_value.between(1, 5)).sum())

wastage = pd.read_csv("data/raw/wastage.csv")
print("\n=== wastage ===")
print("Missing values per column:")
print(wastage.isnull().sum())
print("Duplicate rows:", wastage.duplicated().sum())

print("\nThis is just a peek. Step 4's data_quality_report.py checks every table")
print("properly in Spark and writes DATA_QUALITY_REPORT.md -- that file is the")
print("real deliverable, not this script's printout.")
