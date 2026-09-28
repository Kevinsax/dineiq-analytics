"""
compare_classifications.py  --  Document 4, Step 4: Compare the Two Classifications (do this together)

The actual dual-pipeline deliverable. Loads both label sets, joins on
item_id, reports the overall agreement rate and the full disagreement
table, and specifically checks the tricky-case dishes this dataset was
built to contain (a popular dish that's secretly losing money, a rarely
ordered dish that's secretly very profitable, and so on).

Run from your project root, after BOTH classify_spark.py and
classify_python.py have finished:
    python pair_b_models/compare_classifications.py
"""
import json
import os

import pandas as pd

spark_labels = pd.read_parquet("data/models/item_classification_spark.parquet")[["item_id", "item_name", "spark_label"]]
python_labels = pd.read_parquet("data/models/item_classification_python.parquet")[["item_id", "python_label"]]

compare = spark_labels.merge(python_labels, on="item_id")
compare["agree"] = compare.spark_label == compare.python_label

agreement_rate = compare.agree.mean()
print(f"Agreement rate: {agreement_rate:.1%} ({compare.agree.sum():,} of {len(compare):,} dishes)")

disagreements = compare[~compare.agree].sort_values("item_name")
print(f"\n{len(disagreements)} disagreements:")
print(disagreements[["item_id", "item_name", "spark_label", "python_label"]].to_string(index=False))

# --- tricky-case check ---
# This dataset plants specific known-tricky dishes on purpose (see
# data/_truth/tricky_cases.json, written by dineiq_generator.py). Reading
# the file here means this check is always correct for whatever seed was
# used to generate the data, instead of hard-coding dish names that might
# not exist in this run.
truth_path = "data/_truth/tricky_cases.json"
tricky_lines = []
if os.path.exists(truth_path):
    truth = json.load(open(truth_path, encoding="utf-8"))
    dish_names = truth.get("dish_names", {})
    expectations = {
        "loss_making_popular": "should show a LOW/negative margin despite selling a lot -- the classic dish a restaurant thinks is a star but isn't",
        "hidden_high_margin": "should show HIGH margin despite low sales volume -- easy to overlook on a simple sales-ranked list",
        "popular_high_wastage": "sells well, but a lot of it is thrown away -- margin alone won't catch this, only wastage_percent will",
        "highly_rated_low_margin": "customers love it, but it barely makes money -- a favorite that's quietly a drag on profit",
        "low_rated_high_sales": "sells well despite a poor rating -- likely propped up by something other than quality (price, habit, lack of alternatives)",
        "promo_dependent": "barely sells at full price -- almost all its volume comes from promotional periods",
    }
    for key, item_id in truth.items():
        if key not in expectations:
            continue
        name = dish_names.get(item_id, item_id)
        row = compare[compare.item_id == item_id]
        if row.empty:
            tricky_lines.append(f"- **{name}** ({item_id}): not found in item_features -- check it had completed sales.")
            continue
        r = row.iloc[0]
        tricky_lines.append(
            f"- **{name}** ({item_id}) -- {expectations[key]}\n"
            f"  - Spark labeled it: **{r.spark_label}**\n"
            f"  - Python labeled it: **{r.python_label}**\n"
            f"  - {'Both pipelines agree.' if r.spark_label == r.python_label else 'The two pipelines DISAGREE on this one -- worth explaining out loud.'}"
        )
    print(f"\nTricky-case check ({len(tricky_lines)} dishes):")
    for line in tricky_lines:
        print(line)
else:
    print(f"\n{truth_path} not found -- skipping the tricky-case check. "
          "This file only exists if dineiq_generator.py wrote it in this project; "
          "the comparison above still stands on its own without it.")

os.makedirs("data/models", exist_ok=True)
compare.to_csv("data/models/classification_comparison.csv", index=False)

with open("COMPARISON_REPORT.md", "w", encoding="utf-8") as f:
    f.write("# Classification Comparison Report\n\n")
    f.write(f"**Agreement rate: {agreement_rate:.1%}** ({compare.agree.sum():,} of {len(compare):,} dishes)\n\n")
    f.write("Built independently: Partner 1 in Spark SQL (classify_spark.py), Partner 2 in plain "
            "pandas (classify_python.py), each computing their own median thresholds from the same "
            "source table without seeing the other's code or numbers first.\n\n")
    f.write("## Disagreements\n\n")
    if len(disagreements):
        f.write("| item_id | item_name | Spark label | Python label |\n|---|---|---|---|\n")
        for _, r in disagreements.iterrows():
            f.write(f"| {r.item_id} | {r.item_name} | {r.spark_label} | {r.python_label} |\n")
    else:
        f.write("None -- the two pipelines agreed on every dish.\n")
    f.write("\n## Tricky-case check\n\n")
    if tricky_lines:
        f.write("\n".join(tricky_lines) + "\n")
    else:
        f.write("data/_truth/tricky_cases.json was not available when this report was generated.\n")

print("\nSaved data/models/classification_comparison.csv and COMPARISON_REPORT.md")
