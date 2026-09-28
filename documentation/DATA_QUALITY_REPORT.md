# DineIQ Data Quality Report

Produced by data_quality_report.py (Spark). Nothing is changed in this step.

## menu_categories
- Rows: 12
- Exact duplicate rows: 0
- No missing values

## menu_items
- Rows: 161
- Exact duplicate rows: 0
- No missing values

## restaurants
- Rows: 20
- Exact duplicate rows: 0
- No missing values

## customers
- Rows: 55,110
- Exact duplicate rows: 110
- Missing signup_date: 276 (0.50%)

## pricing_history
- Rows: 509
- Exact duplicate rows: 0
- Missing effective_to: 161 (31.63%)

## promotions
- Rows: 43
- Exact duplicate rows: 0
- Missing applicable_items: 8 (18.60%)
- Missing category_id: 39 (90.70%)

## orders
- Rows: 113,297
- Exact duplicate rows: 899
- Missing customer_id: 1,137 (1.00%)
- Missing channel: 339 (0.30%)
- Missing promo_id: 95,383 (84.19%)
- order_date cannot be parsed as a date: 57
- order_date is in the future: 168
- order_date is implausibly old (before 2015): 117
- invalid location_id (not a real branch): 169
- channel needs standardising (case/spacing): 22,860
- status needs standardising (case/spacing): 1,359

## order_items
- Rows: 1,123,780
- Exact duplicate rows: 6,702
- Missing item_id: 2,240 (0.20%)
- quantity is zero or negative: 3,371
- unit_price is zero or negative: 2,250
- discount_pct outside 0-100: 1,123
- item_id not found in menu_items (unknown dish): 1,127
- order_id not found in orders (orphan line): 0

## ratings
- Rows: 116,414
- Exact duplicate rows: 348
- Missing customer_id: 580 (0.50%)
- rating_value outside 1-5: 1,163
- order_id not found in orders (orphan rating): 585

## inventory
- Rows: 245,861
- Exact duplicate rows: 0
- No missing values
- closing_stock is negative: 245
- unit is not lower-case: 19,668

## wastage
- Rows: 61,994
- Exact duplicate rows: 123
- Missing item_id: 61 (0.10%)
- quantity_wasted is impossible (<=0 or >1000): 183
