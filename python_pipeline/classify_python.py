"""
classify_python.py  --  Document 4, Step 3: Item Classification, the plain-Python path (Partner 2)

Same four labels, same table, built independently in pandas -- no Spark
anywhere in this file. Calculate your own medians fresh from
item_features.parquet; don't copy the Spark side's threshold numbers.

Windows/Mac: no platform-specific code at all in this script. If
something breaks here, it's a library version issue, not an OS one.

Run from your project root, after Pair A has produced data/features/:
    python pair_b_models/classify_python.py
"""
import os

import numpy as np
import pandas as pd

items = pd.read_parquet("data/features/item_features.parquet")
print(f"Loaded item_features.parquet: {items.shape[0]:,} rows, {items.shape[1]} columns")

margin_med = items["profit_margin"].median()
volume_med = items["total_quantity_sold"].median()
print(f"\nThresholds used: median profit_margin = {margin_med:.4f}, "
      f"median total_quantity_sold = {volume_med:.0f}")

conditions = [
    (items.profit_margin >= margin_med) & (items.total_quantity_sold >= volume_med),
    (items.profit_margin < margin_med) & (items.total_quantity_sold >= volume_med),
    (items.profit_margin >= margin_med) & (items.total_quantity_sold < volume_med),
]
choices = ["Profit Driver", "Volume Driver", "Hidden Opportunity"]
items["python_label"] = np.select(conditions, choices, default="Low Performer")

print("\nLabel counts:")
print(items["python_label"].value_counts())

os.makedirs("data/models", exist_ok=True)
items.to_parquet("data/models/item_classification_python.parquet")
print("\nSaved data/models/item_classification_python.parquet")

items.to_csv("data/models/item_classification_python.csv", index=False)
print("Saved data/models/item_classification_python.csv (open this one in Excel)")

with open("CLASSIFICATION_PYTHON_NOTES.md", "w", encoding="utf-8") as f:
    f.write("# Plain-Python Classification -- Thresholds\n\n")
    f.write(f"- median profit_margin: {margin_med:.4f}\n")
    f.write(f"- median total_quantity_sold: {volume_med:.0f}\n\n")
    f.write("| Label | Count |\n|---|---|\n")
    for label, count in items["python_label"].value_counts().sort_index().items():
        f.write(f"| {label} | {count:,} |\n")
print("Saved CLASSIFICATION_PYTHON_NOTES.md")
