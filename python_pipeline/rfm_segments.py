"""
rfm_segments.py  --  Document 4, Step 5: Customer Segmentation (RFM)

Scores every customer into RFM quintiles and names four business
segments. This is scoring and labeling, not machine learning -- no
training, nothing to fit.

Only pandas is used here -- customer_rfm.parquet is one row per customer,
small enough that Spark would only add setup time.

Run from your project root, after Pair A has produced data/features/:
    python pair_b_models/rfm_segments.py
"""
import os

import pandas as pd

rfm = pd.read_parquet("data/features/customer_rfm.parquet")
print(f"Loaded customer_rfm.parquet: {len(rfm):,} customers with at least one completed order")

# recency_days counts back from the DATASET's own latest completed order,
# not today's real calendar date -- Pair A already built it that way in
# feature_engineering.py. Check the actual spread before trusting a fixed
# "at risk" cutoff:
print(f"\nrecency_days range: {rfm.recency_days.min()} to {rfm.recency_days.max()} "
      f"(median {rfm.recency_days.median():.0f})")

rfm["r_score"] = pd.qcut(rfm.recency_days, 5, labels=[5, 4, 3, 2, 1]).astype(int)
# .rank(method="first") on frequency and monetary avoids a crash from duplicate
# bin edges -- a lot of customers share the same order count or spend total,
# and qcut fails outright without it.
rfm["f_score"] = pd.qcut(rfm.frequency.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["m_score"] = pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["rfm_score"] = rfm.r_score + rfm.f_score + rfm.m_score


def segment(row):
    if row.rfm_score >= 12:
        return "Loyal High Spender"
    if row.r_score <= 2 and row.f_score >= 3:
        return "At Risk"
    if row.f_score <= 2 and row.r_score >= 4:
        return "New Customer"
    return "Regular"


rfm["segment"] = rfm.apply(segment, axis=1)

print("\nSegment counts:")
print(rfm["segment"].value_counts())

os.makedirs("data/models", exist_ok=True)
rfm.to_parquet("data/models/customer_segments.parquet")
print("\nSaved data/models/customer_segments.parquet")

with open("SEGMENTATION_NOTES.md", "w", encoding="utf-8") as f:
    f.write("# Customer Segmentation -- RFM\n\n")
    f.write("Segment definitions (score cutoffs used):\n\n")
    f.write("- **Loyal High Spender**: combined RFM score (r+f+m, each 1-5) is 12 or higher\n")
    f.write("- **At Risk**: recency score <= 2 (hasn't ordered recently) AND frequency score >= 3 "
            "(used to order regularly)\n")
    f.write("- **New Customer**: frequency score <= 2 AND recency score >= 4 (recent but few orders)\n")
    f.write("- **Regular**: everyone else\n\n")
    f.write(f"recency_days range in this dataset: {rfm.recency_days.min()} to {rfm.recency_days.max()}\n\n")
    f.write("| Segment | Customers |\n|---|---|\n")
    for seg, n in rfm["segment"].value_counts().items():
        f.write(f"| {seg} | {n:,} |\n")
print("Saved SEGMENTATION_NOTES.md")
