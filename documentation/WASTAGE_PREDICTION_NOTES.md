# Wastage Prediction

First-pass ranking model: RandomForestRegressor predicting `wastage_percent` from `total_quantity_sold`, `avg_rating` and `category_name` (one-hot encoded). This is a snapshot model -- item_features.parquet has one wastage_percent per dish, not a week-over-week series, so this ranks dishes by risk rather than forecasting a trend.

## Feature importances

| Feature | Importance |
|---|---|
| total_quantity_sold | 0.307 |
| category_name_Desserts | 0.196 |
| category_name_Soft Drinks & Juices | 0.170 |
| avg_rating | 0.114 |
| category_name_Specials & Combos | 0.111 |
| category_name_Snacks & Small Chops | 0.052 |
| category_name_Soups & Swallows | 0.035 |
| category_name_Traditional Drinks | 0.004 |
| category_name_Rice Dishes | 0.004 |
| category_name_Grills & Suya | 0.003 |

## Top 10 dishes by predicted wastage risk

| item_id | item_name | actual wastage_percent | predicted_wastage_risk |
|---|---|---|---|
| M083 | Suya Platter | 0.1740 | 0.1295 |
| M130 | Fruit Salad | 0.1352 | 0.1208 |
| M133 | Yogurt Parfait | 0.1300 | 0.1116 |
| M135 | Banana Bread Slice | 0.1061 | 0.1002 |
| M132 | Puff Puff & Ice Cream | 0.0958 | 0.0891 |
| M112 | Shawarma Chicken | 0.0943 | 0.0844 |
| M153 | Family Combo | 0.0855 | 0.0837 |
| M129 | Ice Cream Sundae | 0.0599 | 0.0818 |
| M154 | Lunch Box Combo | 0.0817 | 0.0817 |
| M160 | Kids Meal | 0.0815 | 0.0817 |

If there's time to go further: a real trend model needs more than one row per item -- join data/clean/wastage against data/clean/inventory on item_id, aggregated by week instead of collapsed into a single total. That weekly table isn't in data/features/ yet; flag it to Pair A early if it turns out to matter.
