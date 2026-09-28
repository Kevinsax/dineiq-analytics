# Feature Dictionary

Three tables live in `data/features/`. Pair B (Document 4) reads all three directly.

| File | Grain (one row per) | Feature | Formula | What it means |
|---|---|---|---|---|
| item_features.parquet | item_id | profit_margin | total_profit / net_revenue | Share of revenue kept as profit. 0.34 means 34%. |
| item_features.parquet | item_id | total_quantity_sold | sum(quantity), completed orders only | How many portions of the dish were sold. |
| item_features.parquet | item_id | wastage_percent | sum(quantity_wasted) / sum(prepared_qty), all branches combined | Share of prepared food that was thrown away. Null means no wastage/inventory record exists for that dish. |
| item_features.parquet | item_id | avg_rating | average rating across all completed order lines for the dish | 1 to 5. Null if the dish was never rated. |
| item_features.parquet | item_id | category_name | from menu_categories via category_id | One of the 12 menu categories -- used as a categorical feature in wastage prediction. |
| customer_rfm.parquet | customer_id | recency_days | days between the customer's last completed order and the newest completed order in the whole dataset | Lower means more recently active. |
| customer_rfm.parquet | customer_id | frequency | count of distinct completed orders | How often the customer orders. |
| customer_rfm.parquet | customer_id | monetary | sum of net_revenue across completed orders | How much the customer has spent in total. |
| order_lines_features.parquet | order_id + item_id | is_completed | 1 if status == 'Completed', else 0 | Cancelled lines are kept but flagged, not dropped -- filter on this before summing revenue. |
| order_lines_features.parquet | order_id + item_id | net_revenue | unit_price * quantity * (1 - discount_pct/100) | Money actually charged for this line, after discount. |

## Row counts from this run

- item_features.parquet: 161 rows (of 161 menu items)
- customer_rfm.parquet: 31,042 rows (of 55,000 customers)
- order_lines_features.parquet: 1,091,111 rows (one per order line, cancelled lines included)
- RFM reference date: 2026-06-30
