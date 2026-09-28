#!/usr/bin/env python3
"""
Dataset validator: MEASURES whether each pattern the SRS asks for is really present in data/raw.
Pure pandas (no Spark), works on the raw CSVs including their planted defects.
    python validate_dataset.py                 # checks data/raw
    python validate_dataset.py --raw path/to/raw
Writes DATASET_VALIDATION.md (attach it to your report as evidence of dataset complexity).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--raw", default=str(Path(__file__).resolve().parent / "data" / "raw"))
a = ap.parse_args()
raw = Path(a.raw)
truth = json.loads((raw.parent / "_truth" / "tricky_cases.json").read_text())
mf = json.loads((raw / "_manifest.json").read_text())

orders = pd.read_csv(raw / "orders.csv", dtype=str)
lines = pd.concat([pd.read_csv(f) for f in sorted((raw / "order_items").glob("*.csv"))], ignore_index=True)
items = pd.read_csv(raw / "menu_items.csv")
rest = pd.read_csv(raw / "restaurants.csv")
ratings = pd.read_csv(raw / "ratings.csv")
waste = pd.read_csv(raw / "wastage.csv")
inv = pd.read_csv(raw / "inventory.csv")
promos = pd.read_csv(raw / "promotions.csv")

# minimal cleaning just for measuring
orders = orders.drop_duplicates()
orders["status"] = orders.status.str.strip().str.title()
orders["d"] = pd.to_datetime(orders.order_date, errors="coerce")
orders = orders[(orders.d >= "2024-07-01") & (orders.d <= "2026-06-30") & orders.location_id.isin(rest.location_id)]
lines = lines.drop_duplicates()
lines = lines[(lines.quantity > 0) & (lines.unit_price > 0) & lines.item_id.isin(items.item_id) & lines.order_id.isin(orders.order_id)]
L = lines.merge(orders[["order_id", "d", "location_id", "status", "channel", "promo_id", "order_datetime", "customer_id"]], on="order_id") \
         .merge(items[["item_id", "item_name", "base_cost", "category_id"]], on="item_id")
L = L[L.status == "Completed"].copy()
L["net"] = L.quantity * L.unit_price * (1 - L.discount_pct.clip(0, 100) / 100)
L["cost"] = L.quantity * L.base_cost
L["profit"] = L.net - L.cost
L["hour"] = pd.to_datetime(L.order_datetime, errors="coerce").dt.hour
L["wk"] = L.d.dt.dayofweek >= 5
it = L.groupby("item_id").agg(units=("quantity", "sum"), net=("net", "sum"), profit=("profit", "sum")).join(items.set_index("item_id")[["item_name"]])
it["margin"] = it.profit / it.net
ids = truth
out = []
res = []


def rec(name, passed, detail):
    res.append((name, passed, detail))
    print(("PASS  " if passed else "FAIL  ") + name + " -> " + detail)


nm = lambda i: it.item_name.get(i, i)
rank = it.units.rank(ascending=False)
r = it.loc[ids["loss_making_popular"]]
rec("High-selling but LOSS-MAKING dish", r.margin < 0 and rank[ids["loss_making_popular"]] <= 10,
    f"{nm(ids['loss_making_popular'])}: sales rank #{int(rank[ids['loss_making_popular']])}, net margin {r.margin:.1%}")
r = it.loc[ids["hidden_high_margin"]]
rec("Highly profitable but RARELY bought dish", r.margin > .55 and rank[ids["hidden_high_margin"]] > len(it) * .5,
    f"{nm(ids['hidden_high_margin'])}: margin {r.margin:.1%}, sales rank #{int(rank[ids['hidden_high_margin']])} of {len(it)}")
waste = waste[waste.quantity_wasted.between(1, 1000) & waste.location_id.isin(rest.location_id) & waste.item_id.isin(items.item_id)]
inv = inv[inv.location_id.isin(rest.location_id)]
w_units = waste.groupby("item_id").quantity_wasted.sum()
p_units = inv.groupby("item_id").prepared_qty.sum()
wr = (w_units / p_units).dropna()
rec("Popular dish with EXCESSIVE WASTAGE", wr.get(ids["popular_high_wastage"], 0) > wr.quantile(.95) and rank[ids["popular_high_wastage"]] <= 15,
    f"{nm(ids['popular_high_wastage'])}: wastage {wr.get(ids['popular_high_wastage'], 0):.1%} (chain median {wr.median():.1%}), sales rank #{int(rank[ids['popular_high_wastage']])}")
rt = ratings[ratings.rating_value.between(1, 5)].groupby("item_id").rating_value.mean()
r = it.loc[ids["highly_rated_low_margin"]]
rec("Highly RATED dish with POOR profitability", rt.get(ids["highly_rated_low_margin"], 0) >= 4.5 and r.margin < .2,
    f"{nm(ids['highly_rated_low_margin'])}: rating {rt.get(ids['highly_rated_low_margin'], 0):.2f}, margin {r.margin:.1%}")
rec("Low-RATED dish with HIGH SALES", rt.get(ids["low_rated_high_sales"], 5) < 3.2 and rank[ids["low_rated_high_sales"]] <= 10,
    f"{nm(ids['low_rated_high_sales'])}: rating {rt.get(ids['low_rated_high_sales'], 0):.2f}, sales rank #{int(rank[ids['low_rated_high_sales']])}")
c = L[L.item_id == ids["promo_dependent"]]
share = (c.promo_id.fillna("") != "").mean()
rec("PROMOTION-DEPENDENT dish", share > .6, f"{nm(ids['promo_dependent'])}: {share:.0%} of its lines are sold on a promotion order")
wo = ids["weekend_only"][0]
ww = L[L.item_id == wo].wk.mean()
rec("Dish that sells only at WEEKENDS", ww > .7, f"{nm(wo)}: {ww:.0%} of units on Sat/Sun (2 of 7 days = 29% if no pattern)")
xm = [i for i in ids["seasonal"] if "Christmas" in it.item_name.get(i, "")]
cx = L[L.item_id == xm[0]]
rec("SEASONAL dish", (cx.d.dt.month == 12).mean() > .6, f"{nm(xm[0])}: {(cx.d.dt.month == 12).mean():.0%} of units sold in December")
ni = ids["new_item"]
fs = L[L.item_id == ni].d.min()
rec("NEW item with little history", fs > pd.Timestamp("2026-05-01"), f"{nm(ni)}: first sale {fs.date() if pd.notna(fs) else 'never'}, {int(it.units.get(ni, 0))} units so far")
si = ids["location_specific"][0]
reg = rest.set_index("location_id").region
x = L[L.item_id == si].assign(reg=lambda d: d.location_id.map(reg))
tot = L.assign(reg=lambda d: d.location_id.map(reg))
sh = x.groupby("reg").quantity.sum() / tot.groupby("reg").quantity.sum()
rec("Dish performing DIFFERENTLY across locations", sh.max() > 2.5 * sh.median(), f"{nm(si)} share of units by region: " + ", ".join(f"{k}={v:.2%}" for k, v in sh.items()))
lo = L.groupby("location_id").net.sum().sort_values(ascending=False)
rec("MULTI-LOCATION differences", lo.iloc[0] > 2 * lo.iloc[-1], f"revenue ranges NGN {lo.iloc[-1] / 1e6:.1f}m ({lo.index[-1]}) to {lo.iloc[0] / 1e6:.1f}m ({lo.index[0]})")
hl = L.groupby("hour").quantity.sum()
rec("PEAK-HOUR pattern", hl.loc[12:14].sum() + hl.loc[18:21].sum() > .45 * hl.sum(), f"12-14h + 18-21h = {(hl.loc[12:14].sum() + hl.loc[18:21].sum()) / hl.sum():.0%} of units")
od = orders[orders.status == "Completed"]
dm = od.groupby(od.d.dt.month).size(); dm = dm / dm.mean()
rec("SEASONAL demand (December)", dm.get(12, 0) > 1.2, f"December orders are {dm.get(12, 0):.2f}x an average month")
wk = od.groupby(od.d.dt.dayofweek).size()
rec("WEEKEND pattern", (wk.loc[5] + wk.loc[6]) / 2 > 1.3 * wk.loc[0:3].mean(), f"Sat/Sun average {(wk.loc[5] + wk.loc[6]) / 2:.0f} orders vs Mon-Thu {wk.loc[0:3].mean():.0f}")
# price-sensitive
ps = ids["price_sensitive"]
ph = pd.read_csv(raw / "pricing_history.csv"); ph = ph[ph.price > 0]
drops = []
for i in ps:
    p = ph[ph.item_id == i].sort_values("effective_from")
    pc = p.price.pct_change()
    for _, row in p[pc > .12].iterrows():
        t = pd.Timestamp(row.effective_from)
        b = L[(L.item_id == i) & (L.d >= t - pd.Timedelta(days=42)) & (L.d < t)].quantity.sum()
        af = L[(L.item_id == i) & (L.d >= t) & (L.d < t + pd.Timedelta(days=42))].quantity.sum()
        if b > 30:
            drops.append(af / b - 1)
rec("PRICE-SENSITIVE items", len(drops) > 0 and np.median(drops) < -.15, f"median demand change 6 weeks after a >12% price rise: {np.median(drops):+.0%} over {len(drops)} events" if drops else "no events measurable")
# promo traps
trap_ids = [k for k, v in ids["promo_traps"].items() if v == "sales_up_profit_down"]
pj = L[L.item_id == ids["loss_making_popular"]]
on = pj[pj.promo_id.isin(trap_ids)]
rec("MISLEADING promotion (sales up, profit down)", len(on) > 0 and on.profit.sum() < pj[~pj.promo_id.isin(trap_ids)].profit.mean() * 0 + 0, f"{nm(ids['loss_making_popular'])} on promo: {int(on.quantity.sum())} units, profit NGN {on.profit.sum():,.0f}")
# churn & new
last = od.groupby("customer_id").d.max(); first = od.groupby("customer_id").d.min(); n = od.groupby("customer_id").size()
churn = ((last < "2026-01-01") & (n >= 3)).sum(); newc = (first > "2026-04-30").sum()
rec("CHURNED and NEW customers", churn > 0 and newc > 0, f"{churn} customers with 3+ orders who stopped before 2026; {newc} first ordered in the last 2 months")
# anomalies
ow = od[od.location_id == truth["anomalous_locations"]["sales_collapse"]]
inw = ow[(ow.d >= "2025-11-03") & (ow.d <= "2025-11-23")].shape[0] / 21
ref = ow[(ow.d >= "2025-10-06") & (ow.d <= "2025-10-26")].shape[0] / 21
rec("SALES anomaly (location collapse)", inw < .6 * ref, f"{truth['anomalous_locations']['sales_collapse']}: {inw:.1f} orders/day in the window vs {ref:.1f} before")
er = ratings[ratings.item_id.isin(items[items.item_name.str.startswith("Efo Riro & Amala")].item_id)]
er = er[er.rating_value.between(1, 5)]
a1 = er[(er.rating_date >= "2025-08-04") & (er.rating_date <= "2025-08-17")].rating_value.mean(); a0 = er.rating_value.mean()
rec("RATING anomaly (sudden drop)", a1 < a0 - 1, f"Efo Riro & Amala ratings {a1:.2f} in window vs {a0:.2f} normally")
bw = ratings[ratings.item_id.isin(items[items.item_name == "Bottled Water"].item_id)]
b1 = ((bw.rating_date >= "2026-05-11") & (bw.rating_date <= "2026-05-16")).sum(); b0 = len(bw) / (730 / 6)
rec("RATING anomaly (5-star burst)", b1 > 4 * b0, f"Bottled Water: {b1} ratings in 6 days vs ~{b0:.0f} typical")
# wastage
lw = waste.groupby("location_id").quantity_wasted.sum() / inv.groupby("location_id").prepared_qty.sum()
rec("EXTREME wastage location", lw.idxmax() == truth["anomalous_locations"]["extreme_wastage_and_low_ratings"] and lw.max() > 1.8 * lw.median(),
    f"{lw.idxmax()} wastes {lw.max():.1%} vs median {lw.median():.1%}")
big = orders.merge(lines.groupby("order_id").size().rename("n"), on="order_id")
rec("Very large / bulk orders", (big.n > 30).sum() > 0, f"{(big.n > 30).sum()} orders with 30+ lines (max {big.n.max()})")
rec("UNUSUAL discounts outside promotions", ((lines.discount_pct >= 50) & (lines.discount_pct <= 70)).sum() > 0,
    f"{((lines.discount_pct >= 50) & (lines.discount_pct <= 70)).sum()} lines with 50-70% discount")
raw_orders = pd.read_csv(raw / "orders.csv", dtype=str); raw_lines = pd.concat([pd.read_csv(f) for f in sorted((raw / "order_items").glob("*.csv"))])
dq = {"duplicate orders": raw_orders.duplicated().sum(), "missing customer_id": raw_orders.customer_id.isna().sum(),
      "invalid location_id": (~raw_orders.location_id.isin(rest.location_id)).sum(), "negative/zero quantity": (raw_lines.quantity <= 0).sum(),
      "price <= 0": (raw_lines.unit_price <= 0).sum(), "missing item_id": raw_lines.item_id.isna().sum(),
      "invalid discount": ((raw_lines.discount_pct < 0) | (raw_lines.discount_pct > 100)).sum(),
      "ratings outside 1-5": (~ratings.rating_value.between(1, 5)).sum(), "impossible wastage qty": ((pd.read_csv(raw / "wastage.csv").quantity_wasted < 0) | (pd.read_csv(raw / "wastage.csv").quantity_wasted > 1000)).sum(),
      "cancelled orders": (raw_orders.status.str.strip().str.lower() == "cancelled").sum()}
rec("DATA-QUALITY defects planted", all(v > 0 for v in dq.values()), ", ".join(f"{k}={v}" for k, v in dq.items()))

md = [f"# Dataset validation ({mf['scale']} scale, seed {mf['seed']})", "",
      "Each row measures a pattern the SRS asks the dataset to contain.", "", "| Result | Pattern | Measured evidence |", "|---|---|---|"]
md += [f"| {'PASS' if p else 'FAIL'} | {n} | {d} |" for n, p, d in res]
md += ["", f"Passed {sum(p for _, p, _ in res)} of {len(res)} checks.", "", "## Row counts", "", "| Table | Rows |", "|---|---|"]
md += [f"| {k} | {v:,} |" for k, v in mf["row_counts"].items()]
(raw.parent.parent / "DATASET_VALIDATION.md").write_text("\n".join(md), encoding="utf-8")
print(f"\n{sum(p for _, p, _ in res)}/{len(res)} checks passed. Wrote DATASET_VALIDATION.md")
