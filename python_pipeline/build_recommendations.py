"""
build_recommendations.py  --  Pair C, Step 8: Recommendation Engine

Builds evidence-backed, prioritized recommendations from everything Pair B
handed over. This is rule-based on purpose (SRS Step 37 asks for
"evidence-based recommendations", not a trained recommender model) -- every
row has to justify itself with real numbers, or it doesn't get written.

Reads from data/models/ (Pair B's handoff) and data/models/demand_forecast.parquet
(built by build_forecast.py in this folder -- run that first).

Run from your project root:
    python pair_c_app/build_recommendations.py
"""
import os

import pandas as pd

items = pd.read_parquet("data/models/item_classification_python.parquet")
wastage_risk = pd.read_parquet("data/models/item_wastage_risk.parquet")[["item_id", "predicted_wastage_risk"]]
items = items.merge(wastage_risk, on="item_id", how="left")
print(f"Loaded {len(items):,} classified dishes")

basket_path = "data/models/basket_rules.csv"
basket = pd.read_csv(basket_path) if os.path.exists(basket_path) else pd.DataFrame()

forecast_path = "data/models/demand_forecast.parquet"
forecast = pd.read_parquet(forecast_path) if os.path.exists(forecast_path) else pd.DataFrame()

recs = []


def add(item_id, item_name, action, reasons, priority):
    recs.append({
        "item_id": item_id,
        "item_name": item_name,
        "recommended_action": action,
        "reason": " | ".join(reasons),
        "priority": priority,
    })


margin_med = items["profit_margin"].median()
margin_p90 = items["profit_margin"].quantile(0.90)
wastage_p85 = items["wastage_percent"].quantile(0.85)
wastage_p95 = items["wastage_percent"].quantile(0.95)
discount_med = items["avg_discount_pct"].median()

# ---- 1. Promote high-margin Hidden Opportunities ----
hidden = items[items["python_label"] == "Hidden Opportunity"].sort_values("profit_margin", ascending=False)
for _, r in hidden.head(15).iterrows():
    add(r.item_id, r.item_name, f"Promote {r.item_name}",
        [f"{r.profit_margin:.1%} profit margin (dataset median is {margin_med:.1%})",
         f"only {r.total_quantity_sold:,.0f} units sold in the period -- under-ordered for how profitable it is",
         f"{r.avg_rating:.1f}/5 average rating"],
        "High" if r.profit_margin >= margin_p90 else "Medium")

# ---- 2. Reduce preparation quantity of high-wastage dishes ----
wasteful = items[items["wastage_percent"] >= wastage_p85].sort_values("wastage_percent", ascending=False)
for _, r in wasteful.head(15).iterrows():
    add(r.item_id, r.item_name, f"Reduce preparation quantity of {r.item_name}",
        [f"{r.wastage_percent:.1%} of prepared units go to waste",
         f"model-predicted wastage risk score {r.predicted_wastage_risk:.3f}"],
        "Critical" if r.wastage_percent >= wastage_p95 else "High")

# ---- 3. Review pricing of discount-dependent Low Performers ----
struggling = items[(items["python_label"] == "Low Performer") & (items["avg_discount_pct"] > discount_med)]
for _, r in struggling.sort_values("avg_discount_pct", ascending=False).head(15).iterrows():
    add(r.item_id, r.item_name, f"Review pricing or positioning of {r.item_name}",
        [f"Low Performer on both volume and margin",
         f"already discounted {r.avg_discount_pct:.1f}% on average with no volume payoff to show for it"],
        "Medium")

# ---- 4. Remove or redesign persistent Low Performers (low rating too) ----
redesign = items[(items["python_label"] == "Low Performer") & (items["avg_rating"] < items["avg_rating"].median())]
for _, r in redesign.sort_values("avg_rating").head(10).iterrows():
    add(r.item_id, r.item_name, f"Consider removing or redesigning {r.item_name}",
        [f"Low Performer on volume and margin",
         f"{r.avg_rating:.1f}/5 average rating -- below the {items['avg_rating'].median():.1f} median, "
         f"so this isn't a hidden gem being underpriced, it's a dish people don't like"],
        "Medium")

# ---- 5. Bundle frequently purchased items (from basket analysis) ----
if len(basket):
    top_rules = basket.sort_values("lift", ascending=False).head(10)
    name_lookup = dict(zip(items.item_id, items.item_name))
    for _, r in top_rules.iterrows():
        ante = r.get("antecedent_names", r.get("antecedents", ""))
        cons = r.get("consequent_names", r.get("consequents", ""))
        add("BUNDLE", f"{ante} + {cons}", f"Bundle {ante} with {cons}",
            [f"lift {r.lift:.2f} (bought together {r.lift:.1f}x more often than chance would predict)",
             f"confidence {r.confidence:.1%}", f"support {r.support:.1%} of all multi-item orders"],
            "Medium")
else:
    print("No basket_rules.csv found -- skipping bundle recommendations (run basket_analysis.py first)")

# ---- 6. Increase stock ahead of rising-demand categories ----
if len(forecast):
    future = forecast[forecast["row_type"] == "forecast"]
    if len(future):
        trend = future.groupby("category_name")["forecast_quantity"].mean()
        history = forecast[forecast["row_type"] == "actual"].groupby("category_name")["actual_quantity"].mean()
        rising = (trend / history - 1).dropna().sort_values(ascending=False)
        for cat, pct in rising.head(5).items():
            if pct > 0.05:
                add("CATEGORY", cat, f"Increase stock/prep for {cat} ahead of forecast demand",
                    [f"forecast demand is {pct:+.0%} vs. this category's historical weekly average"],
                    "High" if pct > 0.20 else "Medium")
else:
    print("No demand_forecast.parquet found -- skipping stock-ahead recommendations (run build_forecast.py first)")

# ---- 7. Target customer segments (needs customer_segments.parquet) ----
seg_path = "data/models/customer_segments.parquet"
if os.path.exists(seg_path):
    segs = pd.read_parquet(seg_path)
    at_risk_n = (segs["segment"] == "At Risk").sum()
    loyal_n = (segs["segment"] == "Loyal High Spender").sum()
    add("SEGMENT", "At Risk customers", "Launch a win-back campaign for At Risk customers",
        [f"{at_risk_n:,} customers scored 'At Risk' -- ordered often before but haven't recently"],
        "High" if at_risk_n > 0.15 * len(segs) else "Medium")
    add("SEGMENT", "Loyal High Spenders", "Build a loyalty/rewards tier for Loyal High Spenders",
        [f"{loyal_n:,} customers ({loyal_n / len(segs):.1%} of the base) already score as loyal, high-value"],
        "Medium")

rec_df = pd.DataFrame(recs)
priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
rec_df["priority_rank"] = rec_df["priority"].map(priority_order)
rec_df = rec_df.sort_values("priority_rank").drop(columns="priority_rank")

print(f"\n{len(rec_df)} recommendations generated")
print(rec_df["priority"].value_counts())

os.makedirs("data/models", exist_ok=True)
rec_df.to_csv("data/models/recommendations.csv", index=False)
print("\nSaved data/models/recommendations.csv")

with open("RECOMMENDATIONS_NOTES.md", "w", encoding="utf-8") as f:
    f.write("# Recommendation Engine\n\n")
    f.write("Rule-based on purpose -- the SRS asks for evidence-based recommendations (Step 37), "
            "not a trained recommender model, and every row here has to justify itself with real "
            "numbers pulled from Pair B's output, never an unexplained suggestion (Step 38).\n\n")
    f.write(f"**{len(rec_df)} recommendations generated**, by priority:\n\n")
    f.write("| Priority | Count |\n|---|---|\n")
    for p, n in rec_df["priority"].value_counts().items():
        f.write(f"| {p} | {n} |\n")
    f.write("\n## Rule categories used\n\n")
    f.write("1. Promote high-margin Hidden Opportunities\n"
            "2. Reduce preparation quantity of high-wastage dishes\n"
            "3. Review pricing of discount-dependent Low Performers\n"
            "4. Remove or redesign persistent, poorly-rated Low Performers\n"
            "5. Bundle frequently purchased items (from market basket analysis)\n"
            "6. Increase stock ahead of categories with rising forecast demand\n"
            "7. Target At Risk and Loyal High Spender customer segments\n\n")
    f.write("If there's time to go further: promotion effectiveness review and anomalous-location "
            "flagging are both in the SRS's example list (Step 37) but need promotions.csv and "
            "location-level aggregation this first pass doesn't build -- worth adding if the demo "
            "has room for one more \"why\" behind a recommendation.\n")
print("Saved RECOMMENDATIONS_NOTES.md")
