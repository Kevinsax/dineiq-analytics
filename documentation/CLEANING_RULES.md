# Cleaning Rules
All cleaning rules above were re-run and confirmed against the full-scale dataset

| Table | Problem | Why we handled it this way | Rows removed |
|---|---|---|---|
| menu_items | exact duplicate rows | Same record loaded twice, so one copy is kept. | 0 |
| restaurants | exact duplicate rows | Same record loaded twice, so one copy is kept. | 0 |
| orders | exact duplicate rows | Same record loaded twice, so one copy is kept. | 899 |
| orders | missing customer_id | An order with no customer can't feed segmentation or repeat-order features. | 1,123 |
| orders | invalid location_id (not a real branch) | A location code that doesn't match any of the 20 real branches -- a data entry error, dropped rather than guessed. | 167 |
| orders | order_date cannot be parsed | Not a valid calendar date at all (e.g. month 13). Can't be fixed, so the row is dropped. | 55 |
| orders | order_date implausible (before 2015 or after today) | Dates like 1970-01-01 or next year are clearly wrong, not real orders. Dropped. | 276 |
| order_items | exact duplicate rows | Same record loaded twice, so one copy is kept. | 6,702 |
| order_items | missing item_id | Can't join the line to a dish, so it can't be classified or costed. | 2,231 |
| order_items | unknown item_id (not in menu_items) | References a dish that doesn't exist on the menu -- a data entry error, dropped. | 1,117 |
| order_items | quantity is zero or negative | A negative or zero quantity is a data entry error. Dropped rather than guessed. | 3,345 |
| order_items | unit_price is zero or negative | Nothing on the menu is free or negative, so the price is unusable. | 2,216 |
| order_items | discount_pct outside 0-100 | A discount can't be negative or over 100%. Dropped, since we can't know what was meant. | 1,113 |
| order_items | orphan lines (order was dropped or never existed) | The parent order was dropped above, so the line has nothing to attach to. | 15,945 |
| ratings | exact duplicate rows | Same record loaded twice, so one copy is kept. | 348 |
| ratings | rating_value outside 1-5 | The scale is 1 to 5. Dropped rather than capped, since we can't know what the customer meant. | 1,160 |
| ratings | orphan rating (order was dropped or never existed) | The order this rating belongs to was dropped, so the rating can't be trusted either. | 2,268 |
| customers | exact duplicate rows | Same record loaded twice, so one copy is kept. | 110 |
| wastage | exact duplicate rows | Same record loaded twice, so one copy is kept. | 123 |
| wastage | impossible quantity_wasted (<=0 or >1000) | Zero or negative waste isn't waste, and over 1000 units in one record is a data entry error, not a real kitchen event. | 183 |
| wastage | invalid location_id | A location code that doesn't match any of the 20 real branches. Dropped. | 60 |
| wastage | missing item_id | Can't join the line to a dish, so it can't be classified or costed. | 61 |
| wastage | unknown item_id (not in menu_items) | References a dish that doesn't exist on the menu -- a data entry error, dropped. | 0 |
| inventory | exact duplicate rows | Same record loaded twice, so one copy is kept. | 0 |
| inventory | negative closing_stock | Stock can't be negative -- a counting error, dropped. | 245 |
| inventory | invalid location_id | A location code that doesn't match any of the 20 real branches. Dropped. | 122 |
| menu_categories | exact duplicate rows | Same record loaded twice, so one copy is kept. | 0 |
| pricing_history | exact duplicate rows | Same record loaded twice, so one copy is kept. | 0 |
| promotions | exact duplicate rows | Same record loaded twice, so one copy is kept. | 0 |


Notes

- Cancelled orders are kept. Filter `status == "Completed"` when calculating revenue.
- Missing `signup_date` on a customer is left as null, not guessed.
- Missing `customer_id` on a rating is left as null; the rating still counts toward the dish average.
- `channel` and `status` on orders, `home_city` on customers, and `unit` on inventory are standardised to one consistent casing (e.g. "dine-in" and "DINE-IN " both become "Dine-in").
"Verified against the actual join keys in spark_jobs/join_data.py — Nmesoma.
