"""
wastage_prediction.py  --  Document 4, Step 7: Wastage Prediction

First-pass ranking model: predicts wastage_percent from sales volume,
rating and category, using a RandomForestRegressor. This is a snapshot
(one wastage_percent per dish, not a real week-over-week trend) -- good
enough for a first submission, and clearly documented as such.

Run from your project root, after Pair A has produced data/features/:
    python pair_b_models/wastage_prediction.py
"""
import os

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

items = pd.read_parquet("data/features/item_features.parquet")
n_before = len(items)
items = items.dropna(subset=["wastage_percent"])
n_dropped = n_before - len(items)
if n_dropped:
    print(f"Dropped {n_dropped} dishes with no wastage_percent (no wastage/inventory record for them)")

X = pd.get_dummies(items[["total_quantity_sold", "avg_rating", "category_name"]], columns=["category_name"])
y = items["wastage_percent"]

model = RandomForestRegressor(n_estimators=200, random_state=42)
model.fit(X, y)
items["predicted_wastage_risk"] = model.predict(X)

importances = sorted(zip(X.columns, model.feature_importances_), key=lambda kv: -kv[1])
print("Feature importances (top 8):")
for name, val in importances[:8]:
    print(f"  {name:35s} {val:.3f}")

top10 = items.sort_values("predicted_wastage_risk", ascending=False).head(10)
print("\nTop 10 dishes by predicted wastage risk:")
print(top10[["item_id", "item_name", "wastage_percent", "predicted_wastage_risk"]].to_string(index=False))

os.makedirs("data/models", exist_ok=True)
items.to_parquet("data/models/item_wastage_risk.parquet")
print("\nSaved data/models/item_wastage_risk.parquet")

with open("WASTAGE_PREDICTION_NOTES.md", "w", encoding="utf-8") as f:
    f.write("# Wastage Prediction\n\n")
    f.write("First-pass ranking model: RandomForestRegressor predicting `wastage_percent` from "
            "`total_quantity_sold`, `avg_rating` and `category_name` (one-hot encoded). This is a "
            "snapshot model -- item_features.parquet has one wastage_percent per dish, not a "
            "week-over-week series, so this ranks dishes by risk rather than forecasting a trend.\n\n")
    f.write("## Feature importances\n\n")
    f.write("| Feature | Importance |\n|---|---|\n")
    for name, val in importances[:10]:
        f.write(f"| {name} | {val:.3f} |\n")
    f.write("\n## Top 10 dishes by predicted wastage risk\n\n")
    f.write("| item_id | item_name | actual wastage_percent | predicted_wastage_risk |\n|---|---|---|---|\n")
    for _, r in top10.iterrows():
        f.write(f"| {r.item_id} | {r.item_name} | {r.wastage_percent:.4f} | {r.predicted_wastage_risk:.4f} |\n")
    f.write("\nIf there's time to go further: a real trend model needs more than one row per item -- "
            "join data/clean/wastage against data/clean/inventory on item_id, aggregated by week "
            "instead of collapsed into a single total. That weekly table isn't in data/features/ yet; "
            "flag it to Pair A early if it turns out to matter.\n")
print("Saved WASTAGE_PREDICTION_NOTES.md")
