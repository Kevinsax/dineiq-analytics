#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DineIQ Dataset Generator  (SRS Step 1 - "Restaurant Dataset Creation")

Creates 11 related tables of a Nigerian restaurant chain, with the complexity the SRS asks for
(data-quality defects, seasonality, weekends, peak hours, multi-location differences, promotions,
churned/new customers, tricky dishes, rating/sales anomalies, price-sensitive items, misleading promos).

USAGE (run from the project folder):
    python dineiq_generator.py --scale dev  --seed 42     # small, ~1 minute, for testing
    python dineiq_generator.py --scale full --seed 42     # SRS-size dataset (1M+ order lines)
    python dineiq_generator.py --check                    # verify data/raw against the SRS minimums

IMPORTANT: dev and full BOTH write to data/raw by default. The last one you run wins.
`data/raw/_manifest.json` records which scale is currently in there. Every pipeline script prints it.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROFILES = {
    "dev":  dict(customers=2500,  orders=6500,   ratings=6500,   wastage=3000),
    "full": dict(customers=55000, orders=112000, ratings=115000, wastage=62000),
}
SRS_MINIMUMS = {"order_items": 1_000_000, "orders": 100_000, "customers": 50_000, "menu_items": 150,
                "menu_categories": 10, "restaurants": 20, "ratings": 100_000, "wastage": 50_000}

START, END = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")     # 24 months
DAYS = pd.date_range(START, END, freq="D")
ND = len(DAYS)
NW = (ND + 6) // 7                                                        # weeks (2024-07-01 is a Monday)
CHANNELS = ["Dine-in", "Takeaway", "Website/App", "Third-party Delivery"]
PAYMENTS = ["Card", "Cash", "Bank Transfer", "Wallet/USSD"]


def day_idx(s):
    return int((pd.Timestamp(s) - START).days)


CATS = ["Rice Dishes", "Soups & Swallows", "Grills & Suya", "Protein & Sides", "Stews & Sauces",
        "Snacks & Small Chops", "Pepper Soups", "Breakfast", "Desserts", "Soft Drinks & Juices",
        "Traditional Drinks", "Specials & Combos"]
CAT_POP = np.array([1.6, 1.3, 1.2, 1.5, .5, .9, .7, .8, .5, 1.7, .6, .5])
CAT_COST = np.array([.40, .44, .45, .35, .35, .37, .42, .36, .33, .55, .30, .50])
CAT_WASTE = np.array([.05, .07, .06, .05, .05, .08, .06, .05, .12, .02, .06, .09])
CAT_RATING = np.array([4.1, 4.1, 4.2, 3.9, 4.0, 3.9, 4.1, 3.9, 4.0, 3.9, 4.0, 4.1])
CAT_UNIT = ["portion", "portion", "portion", "portion", "portion", "piece", "portion", "portion",
            "slice", "bottle", "cup", "pack"]

# (dish, category 1-12, base price NGN, size variants: 3=S/R/L, 2=R/L, 1=single)
DISHES = [
    ("Jollof Rice", 1, 2500, 3), ("Fried Rice", 1, 2700, 3), ("Coconut Rice", 1, 2900, 3),
    ("White Rice & Stew", 1, 2200, 3), ("Native Jollof (Palm Oil)", 1, 2800, 3),
    ("Concoction Rice", 1, 3200, 3), ("Basmati Rice & Chicken Sauce", 1, 3600, 3),
    ("Yam Porridge (Asaro)", 1, 2400, 3), ("Party Jollof Rice", 1, 3200, 1),
    ("Ofada Rice & Ayamase", 1, 3800, 1), ("Smoky Jollof Bowl", 1, 3000, 1),
    ("Egusi Soup & Pounded Yam", 2, 3800, 3), ("Oha Soup & Pounded Yam", 2, 4200, 3),
    ("Efo Riro & Amala", 2, 3400, 3), ("Banga Soup & Starch", 2, 4500, 3),
    ("Afang Soup & Eba", 2, 4300, 3), ("Ogbono Soup & Eba", 2, 3600, 3),
    ("Edikang Ikong & Fufu", 2, 4400, 3), ("Okro Soup & Semo", 2, 3200, 3),
    ("Ewedu & Gbegiri Amala", 2, 3000, 3), ("Bitterleaf Soup & Pounded Yam", 2, 4000, 3),
    ("Vegetable Soup & Eba", 2, 3300, 3), ("Nsala Soup & Pounded Yam", 2, 4800, 3),
    ("Isi Ewu", 2, 6500, 1), ("Nkwobi", 2, 5500, 1),
    ("Beef Suya", 3, 2500, 2), ("Chicken Suya", 3, 2800, 2), ("Grilled Tilapia", 3, 5200, 2),
    ("Grilled Catfish", 3, 5800, 2), ("Asun (Peppered Goat)", 3, 4500, 2),
    ("Grilled Chicken", 3, 4800, 2), ("Roasted Turkey Wings", 3, 5000, 2),
    ("Grilled Titus Fish", 3, 4200, 2), ("Point & Kill Croaker Fish", 3, 7800, 1),
    ("Suya Platter", 3, 6500, 1), ("Kilishi Pack", 3, 3000, 1),
    ("Fried Plantain (Dodo)", 4, 1200, 1), ("Moi Moi", 4, 1000, 1), ("Extra Beef", 4, 1200, 1),
    ("Extra Chicken", 4, 1800, 1), ("Extra Fish", 4, 2000, 1), ("Coleslaw", 4, 900, 1),
    ("Boiled Yam & Egg Sauce", 4, 2200, 1), ("Fried Yam & Pepper Sauce", 4, 2400, 1),
    ("Akara (5 pcs)", 4, 900, 1), ("Gizdodo", 4, 2600, 1), ("Ponmo (Cow Skin)", 4, 1200, 1),
    ("Jollof Spaghetti", 4, 2000, 1),
    ("Ayamase Sauce", 5, 1500, 1), ("Ata Dindin", 5, 1500, 1), ("Turkey Stew", 5, 2500, 1),
    ("Fish Stew", 5, 2200, 1), ("Peppered Snail", 5, 4200, 1), ("Egg Sauce", 5, 1500, 1),
    ("Small Chops Platter", 6, 5500, 1), ("Puff Puff (10 pcs)", 6, 1500, 1),
    ("Spring Rolls (6 pcs)", 6, 1800, 1), ("Samosa (6 pcs)", 6, 1800, 1), ("Chin Chin (Bowl)", 6, 1200, 1),
    ("Meat Pie", 6, 1300, 1), ("Scotch Egg", 6, 1000, 1), ("Sausage Roll", 6, 1000, 1),
    ("Fish Roll", 6, 1000, 1), ("Shawarma Chicken", 6, 3500, 1),
    ("Goat Meat Pepper Soup", 7, 3800, 2), ("Chicken Pepper Soup", 7, 3200, 2),
    ("Assorted Pepper Soup", 7, 4500, 2), ("Catfish Pepper Soup", 7, 4800, 2),
    ("Akara & Pap", 8, 1800, 1), ("Yam & Egg", 8, 2200, 1), ("Bread & Egg Sauce", 8, 1800, 1),
    ("Indomie Special", 8, 2200, 1), ("Pancakes", 8, 2500, 1), ("Moi Moi & Custard", 8, 2000, 1),
    ("Tea & Bread", 8, 1500, 1), ("Oat Porridge", 8, 1800, 1),
    ("Ice Cream Sundae", 9, 2200, 1), ("Fruit Salad", 9, 1800, 1), ("Chocolate Cake Slice", 9, 2400, 1),
    ("Puff Puff & Ice Cream", 9, 2200, 1), ("Yogurt Parfait", 9, 2000, 1),
    ("Red Velvet Slice", 9, 2600, 1), ("Banana Bread Slice", 9, 1600, 1),
    ("Coke (50cl)", 10, 700, 1), ("Fanta (50cl)", 10, 700, 1), ("Sprite (50cl)", 10, 700, 1),
    ("Bottled Water", 10, 400, 1), ("Malt (Maltina)", 10, 900, 1), ("Fresh Orange Juice", 10, 1800, 1),
    ("Pineapple Smoothie", 10, 2200, 1), ("Chapman", 10, 2500, 1), ("Lemonade", 10, 1600, 1),
    ("Fresh Watermelon Juice", 10, 1800, 1),
    ("Zobo", 11, 1200, 1), ("Kunu", 11, 1000, 1), ("Palm Wine (Fresh)", 11, 2000, 1),
    ("Tigernut Drink", 11, 1500, 1), ("Ginger Shot", 11, 1200, 1), ("Fura da Nono", 11, 1300, 1),
    ("Party Pack", 12, 12500, 1), ("Family Combo", 12, 16500, 1), ("Lunch Box Combo", 12, 4500, 1),
    ("Christmas Special Rice", 12, 6500, 1), ("Iftar Pack", 12, 5500, 1),
    ("Weekend Brunch Combo", 12, 7500, 1), ("Couples Combo", 12, 9500, 1),
    ("Office Lunch Combo", 12, 5200, 1), ("Kids Meal", 12, 3200, 1), ("Breakfast Combo", 12, 4200, 1),
]
SIZES = {3: [("Small Portion", .70, .55), ("Regular Portion", 1.0, 1.0), ("Large Portion", 1.40, .55)],
         2: [("Regular Portion", 1.0, 1.0), ("Large Portion", 1.40, .45)], 1: [("", 1.0, 1.0)]}
COST_OVR = {"Party Jollof Rice": 1.25, "Ofada Rice & Ayamase": .90, "Point & Kill Croaker Fish": .27,
            "Suya Platter": .42, "Indomie Special": .42, "Chapman": .30, "Weekend Brunch Combo": .33,
            "Kilishi Pack": .30}
POP_OVR = {"Party Jollof Rice": 6.0, "Suya Platter": 4.0, "Indomie Special": 6.5,
           "Point & Kill Croaker Fish": .12, "Kilishi Pack": .30, "Ofada Rice & Ayamase": 1.3,
           "Chapman": 12.0, "Christmas Special Rice": 2.0, "Smoky Jollof Bowl": 2.5}
WASTE_OVR = {"Suya Platter": .24, "Fruit Salad": .19}
RATING_OVR = {"Ofada Rice & Ayamase": 4.8, "Indomie Special": 2.7, "Party Jollof Rice": 4.1,
              "Point & Kill Croaker Fish": 4.7, "Suya Platter": 4.2, "Chapman": 4.0}
REG_RULES = [(("Suya", "Kilishi", "Asun", "Shawarma"), {"N": 2.3, "SW": 1.1}, .85),
             (("Isi Ewu", "Nkwobi", "Oha", "Nsala"), {"SE": 3.4}, .35),
             (("Banga", "Afang", "Edikang"), {"SS": 3.0, "SE": 1.2}, .45),
             (("Amala", "Ewedu", "Efo Riro", "Ofada", "Asaro", "Moi Moi"), {"SW": 2.2}, .6),
             (("Kunu", "Fura", "Tigernut"), {"N": 2.6}, .7),
             (("Palm Wine",), {"SE": 2.2, "SS": 2.0}, .5)]

LOCS = [("DineIQ Lekki Phase 1", "Lagos", "Lekki", "SW", 1.5), ("DineIQ Victoria Island", "Lagos", "Victoria Island", "SW", 1.6),
        ("DineIQ Ikeja City Mall", "Lagos", "Ikeja", "SW", 1.7), ("DineIQ Surulere", "Lagos", "Surulere", "SW", 1.1),
        ("DineIQ Yaba", "Lagos", "Yaba", "SW", 1.2), ("DineIQ Ajah", "Lagos", "Ajah", "SW", 1.0),
        ("DineIQ Maryland", "Lagos", "Maryland", "SW", 1.0), ("DineIQ Ikoyi", "Lagos", "Ikoyi", "SW", 1.3),
        ("DineIQ Wuse II", "Abuja", "Wuse II", "N", 1.9), ("DineIQ Garki", "Abuja", "Garki", "N", 1.2),
        ("DineIQ Maitama", "Abuja", "Maitama", "N", 1.4), ("DineIQ GRA Phase 2", "Port Harcourt", "GRA Phase 2", "SS", 1.3),
        ("DineIQ Rumuola", "Port Harcourt", "Rumuola", "SS", 1.0), ("DineIQ Bodija", "Ibadan", "Bodija", "SW", 1.0),
        ("DineIQ Jericho", "Ibadan", "Jericho", "SW", .9), ("DineIQ Independence Layout", "Enugu", "Independence Layout", "SE", 1.1),
        ("DineIQ GRA Benin", "Benin City", "GRA", "SS", .9), ("DineIQ Nassarawa GRA", "Kano", "Nassarawa GRA", "N", .9),
        ("DineIQ Wetheral Road", "Owerri", "Wetheral Road", "SE", .9), ("DineIQ Ikot Ekpene Road", "Uyo", "Ikot Ekpene Road", "SS", .8)]
L_TOP, L_WASTE, L_DROP = 8, 14, 18          # Wuse II (top), Jericho (extreme wastage, poor ratings), Owerri (sales collapse)

# hour-of-day profiles (weights) by channel; weekends shift later
HOUR_W = {0: [0, 0, 0, 0, 0, 1, 2, 3, 3, 2, 2, 5, 9, 10, 7, 4, 4, 6, 9, 10, 8, 5, 2, 1],
          1: [0, 0, 0, 0, 0, 1, 3, 5, 4, 3, 3, 6, 10, 9, 5, 4, 6, 8, 6, 4, 3, 2, 1, 0],
          2: [0, 0, 0, 0, 0, 0, 1, 2, 3, 3, 3, 5, 8, 8, 5, 4, 5, 7, 9, 10, 9, 7, 4, 1],
          3: [0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 3, 6, 9, 9, 5, 4, 5, 7, 10, 11, 10, 8, 4, 1]}
BANDS = np.array([3] * 5 + [0] * 6 + [1] * 5 + [2] * 7 + [3])        # hour -> 0 morning,1 lunch,2 evening,3 night
HB = np.ones((4, 12))                                                # hour band x category
HB[:, 7] = [10, .1, .03, .01]; HB[:, 0] = [.25, 1.3, 1.2, .5]; HB[:, 1] = [.25, 1.3, 1.2, .5]
HB[:, 2] = [.15, .9, 1.5, 1.6]; HB[:, 6] = [.2, .7, 1.6, 2.5]; HB[:, 8] = [.4, .9, 1.4, 1.0]
HB[:, 11] = [.6, 1.4, 1.0, .3]; HB[:, 5] = [.9, 1.0, 1.0, .6]
CH = np.ones((4, 12))                                                # channel x category
CH[0, [8, 9, 6]] = 1.3; CH[3, 9] = .7; CH[3, 11] = 1.5; CH[2, 11] = 1.3; CH[1, 5] = 1.2; CH[3, 8] = .7
CH_LINES = np.array([1.0, .8, 1.1, 1.25])


def build_menu(rng):
    rows = []
    for dish, cat, price, sz in DISHES:
        for label, pf, popf in SIZES[sz]:
            name = f"{dish} - {label}" if label else dish
            p = int(round(price * pf / 50.0) * 50)
            cr = COST_OVR.get(dish, CAT_COST[cat - 1] + rng.normal(0, .03))
            pop = CAT_POP[cat - 1] * rng.lognormal(0, .55) * popf * POP_OVR.get(dish, 1.0)
            rows.append(dict(dish=dish, item_name=name, cat=cat, price=p, cost=round(p * cr / 10) * 10,
                             popw=pop, waste=WASTE_OVR.get(dish, CAT_WASTE[cat - 1] * rng.uniform(.7, 1.4)),
                             rating=RATING_OVR.get(dish, float(np.clip(rng.normal(CAT_RATING[cat - 1], .3), 3.2, 4.6)))))
    m = pd.DataFrame(rows)
    m["item_id"] = [f"M{i + 1:03d}" for i in range(len(m))]
    m["elasticity"] = rng.lognormal(np.log(.5), .35, len(m))
    m["intro"] = 0
    m["disc"] = ND                                                     # day index the dish is removed (ND = never)
    return m


def region_boost(name, region):
    for kws, mult, default in REG_RULES:
        if any(k in name for k in kws):
            return mult.get(region, default)
    return 1.0


def make_promos(items, rng):
    def ids(*dishes):
        return "|".join(items.loc[items.dish.isin(dishes), "item_id"])
    name2 = dict(zip(items.item_name, items.item_id))
    P = []

    def add(name, ptype, disc, s, e, scope, appl="", cat="", loc="ALL", lift=1.0, trap=""):
        P.append(dict(promo_name=name, promo_type=ptype, discount_pct=disc, start_date=s, end_date=e,
                      scope=scope, applicable_items=appl, category_id=cat, location_id=loc, lift=lift, trap=trap))
    for s, e in [("2024-09-16", "2024-09-29"), ("2025-03-10", "2025-03-23"), ("2026-02-09", "2026-02-22")]:
        add("Party Jollof Fest 30% Off", "Percentage Off", 30, s, e, "ITEM", ids("Party Jollof Rice"), lift=2.3, trap="sales_up_profit_down")
    for s, e in [("2025-04-07", "2025-04-20"), ("2026-04-06", "2026-04-19")]:
        add("Fried Rice Fiesta 30% Off", "Percentage Off", 30, s, e, "ITEM", ids("Fried Rice"), lift=2.4, trap="cannibalises_coconut_rice")
    for s, e in [("2024-11-04", "2024-11-17"), ("2025-10-06", "2025-10-19")]:
        add("Suya Night 25% Off", "Percentage Off", 25, s, e, "ITEM", ids("Beef Suya", "Chicken Suya", "Suya Platter"), lift=2.0, trap="increases_wastage")
    ch_starts = pd.date_range("2024-08-05", "2026-05-31", freq="38D")
    for s in ch_starts:
        add("Chapman Happy Hour 40% Off", "Happy Hour", 40, s.strftime("%Y-%m-%d"), (s + pd.Timedelta(days=4)).strftime("%Y-%m-%d"),
            "ITEM", ids("Chapman"), lift=9.0, trap="only_sells_when_discounted")
    for s, e in [("2025-06-06", "2025-06-22"), ("2026-05-01", "2026-05-17")]:
        add("Weekend Warriors 20% Off Everything", "Weekend", 20, s, e, "ALL", lift=1.4, trap="traffic_up_margin_collapse")
    add("Weekend Brunch Launch 10% Off", "Launch", 10, "2025-01-10", "2025-02-09", "ITEM", ids("Weekend Brunch Combo"), lift=2.0, trap="good_promo")
    add("Zobo & Kunu 15% Off", "Percentage Off", 15, "2025-08-11", "2025-08-24", "CATEGORY", cat="CAT11", lift=1.6)
    add("Dessert Duo 20% Off", "Percentage Off", 20, "2025-02-03", "2025-02-16", "CATEGORY", cat="CAT09", lift=2.0, trap="increases_wastage")
    for s, e in [("2024-12-26", "2025-01-08"), ("2025-12-26", "2026-01-08")]:
        add("New Year Combos 10% Off", "Seasonal", 10, s, e, "CATEGORY", cat="CAT12", lift=1.5)
    for s, e in [("2025-03-01", "2025-03-30"), ("2026-02-18", "2026-03-19")]:
        add("Ramadan Iftar Pack 15% Off", "Seasonal", 15, s, e, "ITEM", ids("Iftar Pack"), lift=2.0)
    add("Lunch Box Combo 12% Off", "Combo Deal", 12, "2024-10-01", "2024-10-31", "ITEM", ids("Lunch Box Combo"), lift=1.8, trap="good_promo")
    add("Lekki Grand Opening 15% Off", "Launch", 15, "2024-07-15", "2024-08-14", "ALL", loc="L01", lift=1.3)
    add("Wuse Loyalty Week 10% Off", "Percentage Off", 10, "2025-09-01", "2025-09-14", "ALL", loc="L09", lift=1.2)
    cand = items[(items.popw > items.popw.median()) & (~items.dish.isin(["Party Jollof Rice", "Chapman", "Fried Rice"]))]
    for k in range(6):
        it = cand.sample(1, random_state=int(rng.integers(1e6))).iloc[0]
        s = START + pd.Timedelta(days=int(rng.integers(40, 660)))
        add(f"{it.dish} {int(rng.choice([10, 15, 20]))}% Off", "Percentage Off", int(rng.choice([10, 15, 20])),
            s.strftime("%Y-%m-%d"), (s + pd.Timedelta(days=13)).strftime("%Y-%m-%d"), "ITEM", it.item_id, lift=float(rng.uniform(1.4, 2.0)))
    P = pd.DataFrame(P)
    P.insert(0, "promo_id", [f"P{i + 1:03d}" for i in range(len(P))])
    return P


def generate(scale, seed, out, quiet=False):
    t0 = time.time()
    prof = PROFILES[scale]
    rng = np.random.default_rng(seed)
    log = (lambda *a: None) if quiet else (lambda *a: print(f"[{time.time() - t0:6.1f}s]", *a, flush=True))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    truth_dir = out.parent / "_truth"
    truth_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ menu
    items = build_menu(rng)
    NI = len(items)
    cat_of = items.cat.values - 1
    name_to_idx = {n: i for i, n in enumerate(items.item_name)}
    dish_idx = lambda d: np.where(items.dish.values == d)[0]
    tricky = {"loss_making_popular": items.item_id[dish_idx("Party Jollof Rice")[0]],
              "hidden_high_margin": items.item_id[dish_idx("Point & Kill Croaker Fish")[0]],
              "popular_high_wastage": items.item_id[dish_idx("Suya Platter")[0]],
              "highly_rated_low_margin": items.item_id[dish_idx("Ofada Rice & Ayamase")[0]],
              "low_rated_high_sales": items.item_id[dish_idx("Indomie Special")[0]],
              "promo_dependent": items.item_id[dish_idx("Chapman")[0]]}
    # weekend-only, seasonal, new item, discontinued
    wk_only = np.concatenate([dish_idx("Weekend Brunch Combo"), dish_idx("Nkwobi")])
    wk_lean = np.concatenate([dish_idx("Catfish Pepper Soup"), dish_idx("Palm Wine (Fresh)"), dish_idx("Asun (Peppered Goat)")])
    xmas, iftar, icecream = dish_idx("Christmas Special Rice"), dish_idx("Iftar Pack"), dish_idx("Ice Cream Sundae")
    new_item = dish_idx("Smoky Jollof Bowl")[0]
    items.loc[new_item, "intro"] = day_idx("2026-05-15")
    late = rng.choice([i for i in range(NI) if i not in (new_item,) and items.popw[i] < items.popw.median()], 12, replace=False)
    items.loc[late, "intro"] = rng.integers(60, 420, len(late))
    disc_pool = [i for i in range(NI) if cat_of[i] in (3, 4, 5, 8) and items.popw[i] < items.popw.quantile(.35) and items.intro[i] == 0]
    disc = rng.choice(disc_pool, 5, replace=False)
    items.loc[disc, "disc"] = rng.integers(430, 620, len(disc))
    excl = set(dish_idx("Party Jollof Rice")) | set(dish_idx("Chapman")) | set(dish_idx("Suya Platter")) | set(dish_idx("Indomie Special"))
    pool = [i for i in range(NI) if cat_of[i] in (0, 1, 3, 5, 9, 10) and i not in excl and items.intro[i] == 0 and items.disc[i] == ND]
    sens = rng.choice(pool, 8, replace=False)
    mod = rng.choice([i for i in pool if i not in sens], 10, replace=False)
    items.loc[sens, "elasticity"] = rng.uniform(2.5, 3.5, len(sens))
    items.loc[mod, "elasticity"] = rng.uniform(1.1, 1.5, len(mod))
    tricky.update(weekend_only=list(items.item_id[wk_only]), seasonal=list(items.item_id[np.concatenate([xmas, iftar, icecream])]),
                  new_item=items.item_id[new_item], price_sensitive=list(items.item_id[sens]),
                  discontinued=list(items.item_id[disc]))

    # ------------------------------------------------------------------ locations
    NL = len(LOCS)
    loc_w = np.array([l[4] for l in LOCS]) * rng.lognormal(0, .12, NL)
    loc_w[L_TOP] *= 1.25
    regions = [l[3] for l in LOCS]
    LA = np.array([[region_boost(items.item_name[i], regions[l]) for i in range(NI)] for l in range(NL)]) * rng.lognormal(0, .35, (NL, NI))
    loc_rating = rng.normal(0, .12, NL); loc_rating[L_WASTE] = -.45
    loc_waste = rng.lognormal(0, .18, NL); loc_waste[L_WASTE] = 2.5
    loc_deliv = np.clip(rng.normal(.20, .05, NL) + np.where(np.array([l[1] for l in LOCS]) == "Lagos", .07, 0), .08, .4)
    chan_base = np.stack([.42 - loc_deliv / 2, np.full(NL, .20), .18 - loc_deliv / 2 + .10, loc_deliv - .0], 1)
    chan_base = chan_base / chan_base.sum(1, keepdims=True)
    tricky["location_specific"] = [items.item_id[dish_idx(d)[0]] for d in ("Isi Ewu", "Nkwobi", "Beef Suya")]
    tricky["anomalous_locations"] = {"extreme_wastage_and_low_ratings": f"L{L_WASTE + 1:02d}", "sales_collapse": f"L{L_DROP + 1:02d}",
                                     "top_performer": f"L{L_TOP + 1:02d}"}

    # ------------------------------------------------------------------ calendar, promos, prices
    promos = make_promos(items, rng)
    NP = len(promos)
    p_lo = np.array([day_idx(s) for s in promos.start_date]); p_hi = np.array([day_idx(e) for e in promos.end_date])
    p_loc = np.array([-1 if l == "ALL" else int(l[1:]) - 1 for l in promos.location_id])
    p_disc = promos.discount_pct.values.astype(float)
    PL = np.ones((NP, NI), np.float32)                     # promo-order item lift
    p_items = np.zeros((NP, NI), bool)                     # which items the discount applies to
    p_waste = np.ones((NP, NI), np.float32)
    for k, r in promos.iterrows():
        if r.scope == "ITEM":
            ix = [items.index[items.item_id == x][0] for x in r.applicable_items.split("|")]
        elif r.scope == "CATEGORY":
            ix = list(np.where(cat_of == int(r.category_id[3:]) - 1)[0])
        else:
            ix = list(range(NI))
        p_items[k, ix] = True
        PL[k, ix] = r.lift
        if r.trap == "cannibalises_coconut_rice":
            PL[k, [i for i in range(NI) if items.dish[i] == "Coconut Rice"]] = .45
        if r.trap == "increases_wastage":
            p_waste[k, ix] = 1.9

    dow, month = DAYS.dayofweek.values, DAYS.month.values
    is_wknd = dow >= 5
    w = (1 + .30 * np.arange(ND) / ND) * np.select([dow == 4, dow == 5, dow == 6], [1.15, 1.40, 1.25], .9)
    w *= np.array([0, .88, .97, 1, 1, 1, .95, .95, .97, 1, 1.05, 1.05, 1.45])[month]

    def bump(a, b, f):
        w[day_idx(a):day_idx(b) + 1] *= f
    for a, b, f in [("2024-12-24", "2024-12-26", 1.6), ("2025-12-24", "2025-12-26", 1.6), ("2024-12-31", "2024-12-31", 1.5),
                    ("2025-12-31", "2025-12-31", 1.5), ("2025-02-14", "2025-02-14", 1.5), ("2026-02-14", "2026-02-14", 1.5),
                    ("2025-04-18", "2025-04-21", 1.35), ("2026-04-03", "2026-04-06", 1.35), ("2025-03-30", "2025-04-01", 1.3),
                    ("2025-06-06", "2025-06-08", 1.3), ("2026-03-20", "2026-03-22", 1.3), ("2026-05-27", "2026-05-29", 1.3),
                    ("2025-03-08", "2025-03-08", 2.6), ("2025-09-20", "2025-09-20", 2.3), ("2026-04-18", "2026-04-18", 2.2),
                    ("2025-02-12", "2025-02-14", .30), ("2026-01-27", "2026-01-27", .25)]:
        bump(a, b, f)
    for k in range(NP):
        if p_loc[k] == -1 and promos.scope[k] == "ALL":
            w[p_lo[k]:p_hi[k] + 1] *= promos.lift[k]
            if promos.trap[k] == "traffic_up_margin_collapse":
                w[p_hi[k] + 1:p_hi[k] + 11] *= .88
    promo_days = np.zeros(ND, bool)
    for k in range(NP):
        promo_days[p_lo[k]:p_hi[k] + 1] = True
    decay = np.ones(ND); decay[300:] = np.linspace(1, .12, ND - 300)
    cdfs = []
    for arr in (w, w * (1 + 6 * promo_days), w * decay):
        c = np.concatenate([[0], np.cumsum(arr)]); cdfs.append(c / c[-1])
    LD = np.ones((NL, ND)); LD[L_DROP, day_idx("2025-11-03"):day_idx("2025-11-24")] = .35

    # price matrix
    Pm = np.tile(items.price.values.astype(float), (ND, 1))
    ph = []
    for i in range(NI):
        base = float(items.price[i]); cur = base
        ev = [(int(items.intro[i]), base)]
        for yr, dstart in enumerate((day_idx("2025-01-01"), day_idx("2026-01-01"))):
            cur = round(cur * (1 + rng.uniform(.05, .09)) / 50) * 50
            ev.append((int(np.clip(dstart + rng.integers(-15, 20), 1, ND - 1)), cur))
        if i in sens:
            for lo, hi, f in ((day_idx("2025-03-01"), day_idx("2025-06-15"), 1.18), (day_idx("2025-10-01"), day_idx("2026-01-31"), 1.15)):
                cur = round(cur * f / 50) * 50; ev.append((int(rng.integers(lo, hi)), cur))
        elif i in mod:
            cur = round(cur * 1.10 / 50) * 50; ev.append((int(rng.integers(150, 500)), cur))
        ev = sorted(ev)
        for j, (d, pr) in enumerate(ev):
            nd_ = ev[j + 1][0] if j + 1 < len(ev) else ND
            Pm[d:nd_, i] = pr
            ph.append((items.item_id[i], pr, DAYS[d].strftime("%Y-%m-%d"),
                       (DAYS[nd_ - 1].strftime("%Y-%m-%d") if j + 1 < len(ev) else "")))
    pricing = pd.DataFrame(ph, columns=["item_id", "price", "effective_from", "effective_to"])
    pricing.insert(0, "price_id", [f"PR{i + 1:05d}" for i in range(len(pricing))])
    Pref = items.price.values[None, :] * (1.07 ** (np.arange(ND) / 365.0))[:, None]
    price_eff = np.clip((Pm / Pref) ** (-items.elasticity.values[None, :]), .2, 3.0)

    # item x day factors
    D = price_eff.astype(np.float32)
    D[:, wk_only] *= np.where(is_wknd, 3.5, .15)[:, None]
    D[:, wk_lean] *= np.where(is_wknd, 1.6, .85)[:, None]
    D[:, xmas] *= np.where((month == 12) & (DAYS.day.values >= 12), 12.0, .03)[:, None]
    ift = np.zeros(ND, bool)
    for a, b in (("2025-03-01", "2025-03-30"), ("2026-02-18", "2026-03-19")):
        ift[day_idx(a):day_idx(b) + 1] = True
    D[:, iftar] *= np.where(ift, 10.0, .02)[:, None]
    D[:, icecream] *= np.select([np.isin(month, [2, 3, 4]), np.isin(month, [6, 7, 8, 9])], [1.8, .55], 1.0)[:, None]
    hot = np.isin(month, [1, 2, 3, 4, 10, 11, 12])
    D[:, cat_of == 10] *= np.where(hot, 1.3, .9)[:, None]
    D[:, cat_of == 6] *= np.where(np.isin(month, [6, 7, 8, 9]), 1.25, 1.0)[:, None]
    dd = np.arange(ND)[:, None]
    D *= ((dd >= items.intro.values[None, :]) & (dd < items.disc.values[None, :])).astype(np.float32)
    D[:, new_item] *= (1 - np.exp(-np.maximum(0, np.arange(ND) - items.intro[new_item]) / 14.0)).astype(np.float32)
    ch_i = dish_idx("Chapman")
    cw = np.zeros(ND, bool)
    for k in range(NP):
        if promos.trap[k] == "only_sells_when_discounted":
            cw[p_lo[k]:p_hi[k] + 1] = True
    D[:, ch_i] *= np.where(cw, .05, .003)[:, None]
    bk = dish_idx("Weekend Brunch Combo"); D[day_idx("2025-02-10"):, bk] *= 1.5
    zob = dish_idx("Zobo"); D[day_idx("2025-09-20"):day_idx("2025-09-25"), zob] *= 6.0
    oj = dish_idx("Fresh Orange Juice"); D[day_idx("2026-03-10"):day_idx("2026-03-19"), oj] *= .05
    tricky["planted_sales_events"] = {"Zobo viral spike": ["2025-09-20", "2025-09-24"], "Fresh Orange Juice stock-out": ["2026-03-10", "2026-03-18"],
                                      "system outage (all locations)": ["2025-02-12", "2025-02-14"], "grid failure": ["2026-01-27", "2026-01-27"],
                                      "Owerri sales collapse": ["2025-11-03", "2025-11-23"], "Women's Day corporate spike": ["2025-03-08", "2025-03-08"]}

    # ------------------------------------------------------------------ customers
    NC = prof["customers"]
    tnames = ["loyal", "frequent", "declining", "promo", "occasional", "churned", "new"]
    tshare = np.array([.08, .15, .05, .18, .42, .07, .05])
    ctype = rng.choice(7, NC, p=tshare)
    tw = np.array([10, 3.5, 3.5, 1.2, .5, 3.0, 12.0])
    sg_lo = {0: (-300, 150), 1: (-300, 250), 2: (-300, 100), 3: (-300, 600), 4: (-300, 690), 5: (-300, 120)}
    signup = np.zeros(NC, int); hi = np.full(NC, ND - 1)
    for t in range(6):
        m = ctype == t; signup[m] = rng.integers(sg_lo[t][0], sg_lo[t][1], m.sum())
    m = ctype == 6; signup[m] = rng.integers(ND - 60, ND - 5, m.sum())
    m = ctype == 5; hi[m] = rng.integers(200, 560, m.sum())
    lo = np.clip(signup, 0, None); hi = np.maximum(hi, lo + 30); hi = np.minimum(hi, ND - 1); lo = np.minimum(lo, hi)
    active = (hi - lo + 1) / ND
    home = rng.choice(NL, NC, p=loc_w / loc_w.sum())
    exp_o = tw[ctype] * active
    exp_o = exp_o / exp_o.sum() * prof["orders"]
    cnt = rng.poisson(exp_o)
    fav_ch = rng.choice(4, NC, p=[.45, .15, .2, .2])
    catpref = rng.dirichlet(CAT_POP * 2.0 + 0.4, NC).astype(np.float32)
    ctype_lines = np.array([1.1, 1.0, 1.0, .95, .9, 1.0, .95])
    cust_ids = np.array([f"C{i + 1:06d}" for i in range(NC)])
    cities = np.array([LOCS[h][1] for h in home])
    age = rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], NC, p=[.16, .38, .24, .14, .08])
    customers = pd.DataFrame(dict(customer_id=cust_ids, home_city=cities, age_bracket=age,
                                  signup_date=(START + pd.to_timedelta(signup, "D")).strftime("%Y-%m-%d")))
    tricky["customer_type_counts"] = {n: int((ctype == i).sum()) for i, n in enumerate(tnames)}
    log(f"menu={NI} items, {NL} locations, {NP} promos, {NC} customers")

    # ------------------------------------------------------------------ orders
    oc = np.repeat(np.arange(NC), cnt)
    NO = len(oc)
    grp = np.where(ctype[oc] == 3, 1, np.where(ctype[oc] == 2, 2, 0))
    oday = np.zeros(NO, int)
    for g in range(3):
        m = grp == g
        c = cdfs[g]; u = c[lo[oc[m]]] + rng.random(m.sum()) * (c[hi[oc[m]] + 1] - c[lo[oc[m]]])
        oday[m] = np.clip(np.searchsorted(c, u, side="right") - 1, lo[oc[m]], hi[oc[m]])
    lw = loc_w[None, :] * LD.T[oday]                                   # NO x NL
    lw[np.arange(NO), home[oc]] *= 6.0
    cl = np.cumsum(lw, 1); cl /= cl[:, -1:]
    oloc = (rng.random((NO, 1)) > cl).sum(1).clip(0, NL - 1)
    pc = chan_base[oloc] * .4; pc[np.arange(NO), fav_ch[oc]] += .6
    cc = np.cumsum(pc, 1); cc /= cc[:, -1:]
    ochan = (rng.random((NO, 1)) > cc).sum(1).clip(0, 3)
    ohour = np.zeros(NO, int)
    for ch in range(4):
        for wk in (False, True):
            m = (ochan == ch) & (is_wknd[oday] == wk)
            if m.any():
                hw = np.array(HOUR_W[ch], float)
                if wk:
                    hw = np.roll(hw, 1) + np.array([0] * 10 + [4, 3] + [0] * 12)
                ohour[m] = rng.choice(24, m.sum(), p=hw / hw.sum())
    osec = ohour * 3600 + rng.integers(0, 3600, NO)
    # promotions: which order uses which promo
    act = (oday[:, None] >= p_lo[None, :]) & (oday[:, None] <= p_hi[None, :]) & ((p_loc[None, :] == -1) | (p_loc[None, :] == oloc[:, None]))
    prio = np.where(act, rng.random((NO, NP)), -1)
    pick = prio.argmax(1); has = prio.max(1) > 0
    use_p = np.where(ctype[oc] == 3, .55, .25)
    opromo = np.where(has & (rng.random(NO) < use_p), pick, -1)
    ostatus = np.where(rng.random(NO) < np.where(ochan == 3, .08, .045), "Cancelled", "Completed")
    opay = rng.choice(4, NO, p=[.34, .22, .28, .16])
    log(f"{NO} orders drawn")

    # ------------------------------------------------------------------ order lines
    lam = 9.3 * CH_LINES[ochan] * np.where(is_wknd[oday], 1.15, 1.0) * ctype_lines[ctype[oc]]
    k = np.clip(1 + rng.poisson(lam), 1, 24)
    bulk = rng.random(NO) < .0005
    k[bulk] = rng.integers(50, 90, bulk.sum())
    base_w = items.popw.values.astype(np.float32)
    L_o, L_i, L_q = [], [], []
    B = 3000
    for s in range(0, NO, B):
        e = min(NO, s + B); sl = slice(s, e)
        band = BANDS[ohour[sl]]
        W = (base_w[None, :] * LA[oloc[sl]].astype(np.float32) * catpref[oc[sl]][:, cat_of]
             * D[oday[sl]] * HB[band][:, cat_of].astype(np.float32) * CH[ochan[sl]][:, cat_of].astype(np.float32))
        pm = opromo[sl]
        W *= np.vstack([np.ones((1, NI), np.float32), PL])[pm + 1]
        W += 1e-9
        C = np.cumsum(W, 1); C /= C[:, -1:]
        kk = k[sl]; km = int(kk.max())
        u = rng.random((e - s, km)).astype(np.float32)
        idx = np.zeros((e - s, km), np.int32)
        for j in range(0, km, 8):
            idx[:, j:j + 8] = (u[:, j:j + 8, None] > C[:, None, :]).sum(2)
        idx = np.minimum(idx, NI - 1)
        valid = np.arange(km)[None, :] < kk[:, None]
        r, c_ = np.where(valid)
        L_o.append(r + s); L_i.append(idx[r, c_])
    lo_ = np.concatenate(L_o); li_ = np.concatenate(L_i)
    qty = 1 + rng.poisson(np.where(cat_of[li_] == 9, .8, .3))
    ln = pd.DataFrame({"o": lo_, "i": li_, "q": np.minimum(qty, 8)}).groupby(["o", "i"], as_index=False).q.sum()
    lo_, li_, lq_ = ln.o.values, ln.i.values, ln.q.values
    log(f"{len(ln)} order lines ({len(ln) / NO:.1f} per order)")

    # ------------------------------------------------------------------ assemble orders / lines (clean version)
    order_dt = START + pd.to_timedelta(oday, "D") + pd.to_timedelta(osec, "s")
    ordr = np.argsort(order_dt.values, kind="stable")
    rank = np.empty(NO, int); rank[ordr] = np.arange(NO)
    oid = np.array([f"ORD{r + 1:07d}" for r in rank])
    orders = pd.DataFrame(dict(order_id=oid, customer_id=cust_ids[oc], location_id=[f"L{x + 1:02d}" for x in oloc],
                               order_datetime=order_dt.strftime("%Y-%m-%d %H:%M:%S"), order_date=order_dt.strftime("%Y-%m-%d"),
                               channel=np.array(CHANNELS)[ochan], payment_method=np.array(PAYMENTS)[opay], status=ostatus,
                               promo_id=np.where(opromo >= 0, promos.promo_id.values[np.maximum(opromo, 0)], "")))
    unit_price = Pm[oday[lo_], li_]
    on_promo = (opromo[lo_] >= 0)
    disc_l = np.where(on_promo & p_items[np.maximum(opromo[lo_], 0), li_], p_disc[np.maximum(opromo[lo_], 0)], 0.0)
    odd = rng.random(len(lo_)) < .002
    disc_l = np.where(odd & (disc_l == 0), rng.choice([50, 60, 70], len(lo_)), disc_l)      # planted "unusual discounts"
    lines = pd.DataFrame(dict(order_id=oid[lo_], item_id=items.item_id.values[li_], quantity=lq_, unit_price=unit_price,
                              discount_pct=disc_l.astype(float)))
    lines["line_total"] = (lines.quantity * lines.unit_price * (1 - lines.discount_pct / 100)).round(2)
    lines["_m"] = order_dt.strftime("%Y_%m").values[lo_]
    lines = lines.sort_values("order_id", kind="stable").reset_index(drop=True)
    lines.insert(0, "order_item_id", [f"OI{i + 1:08d}" for i in range(len(lines))])
    # near-duplicate transactions (same customer, place and basket, a couple of minutes later)
    nd = rng.choice(NO, max(3, int(NO * .0015)), replace=False)
    dup_o = orders.iloc[nd].copy(); dup_map = {}
    for j, (ix, r) in enumerate(dup_o.iterrows()):
        dup_map[r.order_id] = f"ORD{NO + j + 1:07d}"
    dup_o["order_id"] = dup_o.order_id.map(dup_map)
    t2 = pd.to_datetime(dup_o.order_datetime) + pd.Timedelta(minutes=3)
    dup_o["order_datetime"] = t2.dt.strftime("%Y-%m-%d %H:%M:%S"); dup_o["order_date"] = t2.dt.strftime("%Y-%m-%d")
    dl = lines[lines.order_id.isin(dup_map)].copy(); dl["order_id"] = dl.order_id.map(dup_map)
    dl["order_item_id"] = [f"OI{len(lines) + i + 1:08d}" for i in range(len(dl))]
    orders = pd.concat([orders, dup_o], ignore_index=True); lines = pd.concat([lines, dl], ignore_index=True)
    tricky["near_duplicate_order_ids"] = list(dup_map.values())[:25]
    log("orders/lines assembled")

    # ------------------------------------------------------------------ consumption matrices, wastage, inventory
    comp = (ostatus == "Completed")
    lw_ = (oday[lo_] // 7); ll_ = oloc[lo_]
    m = comp[lo_]
    Cm = np.zeros((NW, NL, NI))
    np.add.at(Cm, (lw_[m], ll_[m], li_[m]), lq_[m])
    promo_wk = np.ones((NW, NI))
    for kx in range(NP):
        if (p_waste[kx] > 1).any():
            promo_wk[p_lo[kx] // 7:p_hi[kx] // 7 + 1] *= p_waste[kx][None, :]
    lam_w = Cm * items.waste.values[None, None, :] * loc_waste[None, :, None] * promo_wk[:, None, :] * rng.lognormal(0, .25, Cm.shape)
    lam_w = lam_w / 1.6
    lam_w *= prof["wastage"] / max(lam_w.sum(), 1e-9)
    ev = rng.poisson(lam_w)
    wi = np.argwhere(ev > 0)
    reps = ev[ev > 0]
    wi = np.repeat(wi, reps, axis=0)
    wday = wi[:, 0] * 7 + rng.choice(7, len(wi), p=[.11, .11, .12, .13, .16, .21, .16])
    wday = np.minimum(wday, ND - 1)
    wq = 1 + rng.poisson(.6, len(wi))
    cost = items.cost.values[wi[:, 2]]
    rs = np.array(["Overproduction", "Spoilage", "Expired", "Preparation error", "Customer return"])
    wastage = pd.DataFrame(dict(item_id=items.item_id.values[wi[:, 2]], location_id=[f"L{x + 1:02d}" for x in wi[:, 1]],
                                waste_date=DAYS[wday].strftime("%Y-%m-%d"), quantity_wasted=wq, unit_cost=cost,
                                wastage_cost=(wq * cost).astype(float),
                                reason=np.where(cat_of[wi[:, 2]] == 8, rng.choice(rs, len(wi), p=[.25, .5, .15, .05, .05]),
                                                rng.choice(rs, len(wi), p=[.4, .25, .15, .1, .1]))))
    wastage = wastage.sort_values("waste_date", kind="stable").reset_index(drop=True)
    wastage.insert(0, "wastage_id", [f"W{i + 1:07d}" for i in range(len(wastage))])
    Wm = np.zeros((NW, NL, NI)); np.add.at(Wm, (wi[:, 0], wi[:, 1], wi[:, 2]), wq)
    Pq = Cm + Wm + rng.poisson(.3, Cm.shape) * (Cm > 0)
    rows = np.argwhere(Pq > 0)
    prep = Pq[Pq > 0]
    wkk, llk, iik = rows[:, 0], rows[:, 1], rows[:, 2]
    repl = np.maximum(0, prep + np.round(rng.normal(0, 1.5, len(prep)))).astype(int)
    inv = pd.DataFrame(dict(item_id=items.item_id.values[iik], location_id=[f"L{x + 1:02d}" for x in llk], _w=wkk,
                            replenished_qty=repl, prepared_qty=prep.astype(int), consumed_qty=Cm[Pq > 0].astype(int),
                            unit=np.array(CAT_UNIT)[cat_of[iik]]))
    inv = inv.sort_values(["location_id", "item_id", "_w"], kind="stable").reset_index(drop=True)
    g = inv.groupby(["location_id", "item_id"], sort=False)
    delta = (inv.replenished_qty - inv.prepared_qty)
    inv["closing_stock"] = (30 + delta.groupby([inv.location_id, inv.item_id]).cumsum()).clip(lower=0).astype(int)
    inv["opening_stock"] = g.closing_stock.shift(1).fillna(30).astype(int)
    inv["week_start"] = (START + pd.to_timedelta(inv._w * 7, "D")).dt.strftime("%Y-%m-%d")
    inv = inv.sort_values(["week_start", "location_id", "item_id"], kind="stable").reset_index(drop=True)
    inv.insert(0, "inventory_id", [f"INV{i + 1:07d}" for i in range(len(inv))])
    inv = inv[["inventory_id", "item_id", "location_id", "week_start", "opening_stock", "replenished_qty", "prepared_qty",
               "consumed_qty", "closing_stock", "unit"]]
    log(f"{len(wastage)} wastage records, {len(inv)} inventory rows")

    # ------------------------------------------------------------------ ratings
    ln_ok = comp[lo_]
    cand = np.where(ln_ok)[0]
    rate = prof["ratings"] / len(cand)
    pr = np.full(len(cand), rate)
    c_item, c_loc, c_day = li_[cand], ll_[cand], oday[lo_[cand]]
    bw = dish_idx("Bottled Water")
    burst = np.isin(c_item, bw) & (c_day >= day_idx("2026-05-11")) & (c_day <= day_idx("2026-05-13"))
    ident = (c_loc == 4) & (c_day >= day_idx("2025-06-16")) & (c_day <= day_idx("2025-06-25"))
    pr[burst | ident] = .92
    mu = items.rating.values[c_item] + loc_rating[c_loc]
    drop_i = dish_idx("Efo Riro & Amala")
    dropw = np.isin(c_item, drop_i) & (c_day >= day_idx("2025-08-04")) & (c_day <= day_idx("2025-08-17"))
    mu = np.where(dropw, mu - 2.2, mu)
    val = np.clip(np.rint(rng.normal(mu, .8)), 1, 5).astype(int)
    val[burst | ident] = 5
    keep = rng.random(len(cand)) < pr
    ci = cand[keep]
    rdate = np.minimum(oday[lo_[ci]] + rng.integers(0, 4, len(ci)), ND - 1)
    ratings = pd.DataFrame(dict(order_id=oid[lo_[ci]], item_id=items.item_id.values[li_[ci]], customer_id=cust_ids[oc[lo_[ci]]],
                                rating_date=DAYS[rdate].strftime("%Y-%m-%d"), rating_value=val[keep]))
    ratings = ratings.sort_values("rating_date", kind="stable").reset_index(drop=True)
    ratings.insert(0, "rating_id", [f"R{i + 1:07d}" for i in range(len(ratings))])
    tricky["planted_rating_events"] = {"rating drop (Efo Riro & Amala)": ["2025-08-04", "2025-08-17"],
                                       "5-star burst (Bottled Water)": ["2026-05-11", "2026-05-13"],
                                       "identical 5-star ratings at L05 (Yaba)": ["2025-06-16", "2025-06-25"]}
    log(f"{len(ratings)} ratings")

    # ------------------------------------------------------------------ other tables
    cats_df = pd.DataFrame(dict(category_id=[f"CAT{i + 1:02d}" for i in range(12)], category_name=CATS))
    menu = pd.DataFrame(dict(item_id=items.item_id, item_name=items.item_name, category_id=[f"CAT{c:02d}" for c in items.cat],
                             base_price=items.price, base_cost=items.cost, unit=[CAT_UNIT[c - 1] for c in items.cat],
                             description=[f"{d} - house recipe" for d in items.dish],
                             is_active=(items.disc.values >= ND), introduced_date=(START + pd.to_timedelta(items.intro, "D")).dt.strftime("%Y-%m-%d")))
    rest = pd.DataFrame(dict(location_id=[f"L{i + 1:02d}" for i in range(NL)], restaurant_name=[l[0] for l in LOCS],
                             city=[l[1] for l in LOCS], area=[l[2] for l in LOCS], region=regions,
                             seats=(loc_w * 55).astype(int) + 20, opened_date=[f"20{rng.integers(15, 24)}-{rng.integers(1, 13):02d}-01" for _ in range(NL)]))
    promo_out = promos[["promo_id", "promo_name", "promo_type", "discount_pct", "start_date", "end_date", "scope",
                        "applicable_items", "category_id", "location_id"]]

    # ------------------------------------------------------------------ data-quality defects (documented, planted on purpose)
    def pick_rows(n_rows, frac):
        return rng.choice(n_rows, max(1, int(n_rows * frac)), replace=False)
    defects = {}
    o = orders.copy()
    o.loc[pick_rows(len(o), .010), "customer_id"] = np.nan
    o.loc[pick_rows(len(o), .0015), "location_id"] = "L99"
    ix = pick_rows(len(o), .0015); o.loc[ix, ["order_date", "order_datetime"]] = ["2027-03-15", "2027-03-15 12:00:00"]
    ix = pick_rows(len(o), .001); o.loc[ix, ["order_date", "order_datetime"]] = ["1970-01-01", "1970-01-01 00:00:00"]
    ix = pick_rows(len(o), .0005); o.loc[ix, ["order_date", "order_datetime"]] = ["2025-13-45", "2025-13-45 10:00:00"]
    o.loc[pick_rows(len(o), .003), "channel"] = np.nan
    ix = pick_rows(len(o), .015); o.loc[ix, "channel"] = o.loc[ix, "channel"].astype(str).str.lower().str.replace("nan", "")
    ix = pick_rows(len(o), .012); o.loc[ix, "status"] = o.loc[ix, "status"].str.upper() + " "
    o = pd.concat([o, o.iloc[pick_rows(len(o), .008)]], ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)
    l = lines.copy()
    l.loc[pick_rows(len(l), .002), "item_id"] = np.nan
    l.loc[pick_rows(len(l), .001), "item_id"] = "M999"
    l.loc[pick_rows(len(l), .003), "quantity"] = rng.choice([0, -1, -2], 1)[0]
    ix = pick_rows(len(l), .002); l.loc[ix, "unit_price"] = rng.choice([0.0, -500.0], len(ix))
    ix = pick_rows(len(l), .001); l.loc[ix, "discount_pct"] = rng.choice([150.0, -20.0], len(ix))
    l = pd.concat([l, l.iloc[pick_rows(len(l), .006)]], ignore_index=True).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    r = ratings.copy()
    ix = pick_rows(len(r), .01); r.loc[ix, "rating_value"] = rng.choice([0, 6, -1, 9], len(ix))
    r.loc[pick_rows(len(r), .005), "customer_id"] = np.nan
    ix = pick_rows(len(r), .005); r.loc[ix, "order_id"] = "ORD9999999"
    r = pd.concat([r, r.iloc[pick_rows(len(r), .003)]], ignore_index=True)
    c = customers.copy()
    c.loc[pick_rows(len(c), .005), "signup_date"] = np.nan
    ix = pick_rows(len(c), .02); c.loc[ix, "home_city"] = c.loc[ix, "home_city"].str.upper()
    c = pd.concat([c, c.iloc[pick_rows(len(c), .002)]], ignore_index=True)
    wq_ = wastage.copy()
    wq_.loc[pick_rows(len(wq_), .002), "quantity_wasted"] = -3
    wq_.loc[pick_rows(len(wq_), .001), "quantity_wasted"] = 5000
    wq_.loc[pick_rows(len(wq_), .001), "location_id"] = "L98"
    wq_.loc[pick_rows(len(wq_), .001), "item_id"] = np.nan
    wq_ = pd.concat([wq_, wq_.iloc[pick_rows(len(wq_), .002)]], ignore_index=True)
    iv = inv.copy()
    iv.loc[pick_rows(len(iv), .001), "closing_stock"] = -12
    iv.loc[pick_rows(len(iv), .0005), "location_id"] = "L97"
    ix = pick_rows(len(iv), .08); iv.loc[ix, "unit"] = iv.loc[ix, "unit"].str.upper()
    mn = menu.copy()
    ix = pick_rows(len(mn), .12); mn.loc[ix, "unit"] = mn.loc[ix, "unit"].replace({"portion": "plate", "bottle": "btl", "piece": "pc"}).str.title()
    ph_ = pricing.copy(); ph_.loc[pick_rows(len(ph_), .005), "price"] = 0
    defects = {"orders": "1% missing customer_id, 0.15% invalid location, 0.15% future dates, 0.1% 1970 dates, unparseable dates, missing/messy channel & status, 0.8% duplicate rows",
               "order_items": "0.2% missing item_id, 0.1% unknown item, 0.3% qty<=0, 0.2% price<=0, 0.1% invalid discount, 0.6% duplicate rows",
               "ratings": "1% out-of-range, 0.5% missing customer, 0.5% orphan order, 0.3% duplicates",
               "wastage": "negative and impossible quantities, invalid location, missing item, duplicates",
               "inventory": "negative closing stock, invalid location, inconsistent unit casing",
               "menu_items": "inconsistent units", "customers": "missing signup_date, city casing, duplicates", "pricing_history": "zero prices"}

    # ------------------------------------------------------------------ write
    for old in list(out.glob("*.csv")) + list((out / "order_items").glob("*.csv") if (out / "order_items").exists() else []):
        old.unlink()
    (out / "order_items").mkdir(exist_ok=True)
    cats_df.to_csv(out / "menu_categories.csv", index=False); mn.to_csv(out / "menu_items.csv", index=False)
    rest.to_csv(out / "restaurants.csv", index=False); c.to_csv(out / "customers.csv", index=False)
    ph_.to_csv(out / "pricing_history.csv", index=False); promo_out.to_csv(out / "promotions.csv", index=False)
    o.to_csv(out / "orders.csv", index=False); r.to_csv(out / "ratings.csv", index=False)
    iv.to_csv(out / "inventory.csv", index=False); wq_.to_csv(out / "wastage.csv", index=False)
    for mth, part in l.groupby("_m"):
        part.drop(columns="_m").to_csv(out / "order_items" / f"order_items_{mth}.csv", index=False)
    counts = dict(menu_categories=len(cats_df), menu_items=len(mn), restaurants=len(rest), customers=len(c), pricing_history=len(ph_),
                  promotions=len(promo_out), orders=len(o), order_items=len(l), ratings=len(r), inventory=len(iv), wastage=len(wq_))
    manifest = dict(scale=scale, seed=seed, generated_at=time.strftime("%Y-%m-%d %H:%M:%S"), period=[str(START.date()), str(END.date())],
                    row_counts=counts, planted_defects=defects)
    (out / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    tricky["dish_names"] = {v: n for n, v in zip(items.item_name, items.item_id) if v in
                            [tricky[k] for k in ("loss_making_popular", "hidden_high_margin", "popular_high_wastage",
                                                 "highly_rated_low_margin", "low_rated_high_sales", "promo_dependent")] + [tricky["new_item"]]}
    tricky["promo_traps"] = {p.promo_id: p.trap for p in promos.itertuples() if p.trap}
    (truth_dir / "tricky_cases.json").write_text(json.dumps(tricky, indent=2, default=str))
    log("written to", out)
    check(out)
    return counts


def check(raw):
    raw = Path(raw)
    mf = json.loads((raw / "_manifest.json").read_text()) if (raw / "_manifest.json").exists() else {}
    rc = mf.get("row_counts", {})
    print(f"\n=== SRS minimum check for {raw} (scale = {mf.get('scale', 'unknown')}) ===")
    ok = True
    for t, mn in SRS_MINIMUMS.items():
        n = rc.get(t, 0); good = n >= mn; ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {t:16s} {n:>10,}   (SRS minimum {mn:,})")
    if mf.get("scale") == "dev":
        print("\n  NOTE: this is the DEV dataset. It is meant for testing only. Run  --scale full  before final submission.")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", choices=list(PROFILES), default="dev")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "data" / "raw"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check(a.out) else 1)
    generate(a.scale, a.seed, a.out)
