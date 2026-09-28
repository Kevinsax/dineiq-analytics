"""
basket_analysis.py  --  Document 4, Step 6: Market Basket Analysis

Finds which dishes tend to get ordered together, to power
"customers who ordered X also ordered Y." Only COMPLETED orders count --
a cancelled order never actually happened, so it can't tell you anything
about what people really buy together.

Run from your project root, after Pair A has produced data/features/:
    python pair_b_models/basket_analysis.py

If mlxtend is missing: pip install mlxtend
"""
import os

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

lines = pd.read_parquet("data/features/order_lines_features.parquet")
lines = lines[lines.is_completed == 1]
print(f"Loaded {len(lines):,} completed order lines")

baskets = lines.groupby("order_id")["item_id"].apply(list)
n_single = (baskets.apply(len) == 1).sum()
baskets = baskets[baskets.apply(len) > 1]  # drop single-item orders, they add nothing here
print(f"{len(baskets):,} multi-item orders used ({n_single:,} single-item orders dropped)")

# sparse=True matters once you're past dev scale -- a dense one-hot matrix
# over ~150 items x 100k+ orders is enormous and will genuinely stall a laptop.
te = TransactionEncoder()
te_array = te.fit(baskets).transform(baskets, sparse=True)
basket_df = pd.DataFrame.sparse.from_spmatrix(te_array, columns=te.columns_)

MIN_SUPPORT = 0.01
frequent = apriori(basket_df, min_support=MIN_SUPPORT, use_colnames=True)
if len(frequent) == 0:
    # a smaller dataset naturally has fewer patterns clearing a fixed support bar --
    # this isn't a sign the analysis is broken, just that the bar was too high
    print(f"No itemsets cleared min_support={MIN_SUPPORT}, retrying at 0.005")
    MIN_SUPPORT = 0.005
    frequent = apriori(basket_df, min_support=MIN_SUPPORT, use_colnames=True)

rules = association_rules(frequent, metric="lift", min_threshold=1.2)
rules = rules.sort_values("lift", ascending=False)
print(f"\n{len(rules):,} rules found at min_support={MIN_SUPPORT}, min_lift=1.2")

# swap item_id -> item_name so the file is readable without a lookup table
menu = pd.read_parquet("data/features/item_features.parquet")[["item_id", "item_name"]]
id_to_name = dict(zip(menu.item_id, menu.item_name))


def name_set(frozenset_of_ids):
    return ", ".join(id_to_name.get(i, i) for i in frozenset_of_ids)


rules_named = rules.copy()
rules_named["antecedent_names"] = rules_named.antecedents.apply(name_set)
rules_named["consequent_names"] = rules_named.consequents.apply(name_set)

print("\nTop 10 rules by lift:")
print(rules_named[["antecedent_names", "consequent_names", "support", "confidence", "lift"]].head(10).to_string(index=False))

os.makedirs("data/models", exist_ok=True)
rules_named.to_csv("data/models/basket_rules.csv", index=False)
print("\nSaved data/models/basket_rules.csv")

with open("BASKET_ANALYSIS_NOTES.md", "w", encoding="utf-8") as f:
    f.write("# Market Basket Analysis\n\n")
    f.write(f"- min_support used: {MIN_SUPPORT}\n")
    f.write("- min_lift used: 1.2\n")
    f.write(f"- {len(baskets):,} multi-item completed orders analysed ({n_single:,} single-item orders excluded)\n")
    f.write(f"- {len(rules):,} rules found\n\n")
    f.write("Sorted by **lift**, not confidence -- lift tells you the pairing happens more than "
            "chance would predict; confidence alone gets inflated by dishes that are just popular "
            "on their own.\n\n")
    f.write("## Top 10 rules\n\n")
    f.write("| If ordered | Also ordered | Support | Confidence | Lift |\n|---|---|---|---|---|\n")
    for _, r in rules_named.head(10).iterrows():
        f.write(f"| {r.antecedent_names} | {r.consequent_names} | {r.support:.4f} | {r.confidence:.3f} | {r.lift:.2f} |\n")
print("Saved BASKET_ANALYSIS_NOTES.md")
