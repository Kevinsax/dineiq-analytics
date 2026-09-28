# Data Model: joined order lines

One row per order line, starting from order_items. Every join is a left join, so the row count should stay the same after each step.

| # | Table | Joined on | Why | Rows before | Rows after | Unmatched | Result |
|---|---|---|---|---|---|---|---|
| 1 | orders | order_id | Adds customer, location, channel, payment and status | 1,091,111 | 1,091,111 | 0 | ok |
| 2 | menu_items | item_id | Adds dish name, category_id and unit cost | 1,091,111 | 1,091,111 | 0 | ok |
| 3 | menu_categories | category_id | Adds the category name | 1,091,111 | 1,091,111 | 0 | ok |
| 4 | customers | customer_id | Adds customer city, age bracket and signup date | 1,091,111 | 1,091,111 | 0 | ok |
| 5 | restaurants | location_id | Adds branch name, city and area | 1,091,111 | 1,091,111 | 0 | ok |
| 6 | pricing | item_id | Adds current price, launch price and number of price changes | 1,091,111 | 1,091,111 | 0 | ok |
| 7 | ratings | order_id, item_id | Adds average rating. Only some lines were rated, so gaps are normal | 1,091,111 | 1,091,111 | 979,433 | ok |

Final table: 1,091,111 rows, 31 columns, saved to data/joined/order_lines_joined
