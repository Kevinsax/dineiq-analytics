# Market Basket Analysis

- min_support used: 0.01
- min_lift used: 1.2
- 104,851 multi-item completed orders analysed (20 single-item orders excluded)
- 1,124 rules found

Sorted by **lift**, not confidence -- lift tells you the pairing happens more than chance would predict; confidence alone gets inflated by dishes that are just popular on their own.

## Top 10 rules

| If ordered | Also ordered | Support | Confidence | Lift |
|---|---|---|---|---|
| Tea & Bread | Yam & Egg, Indomie Special | 0.0139 | 0.402 | 8.09 |
| Yam & Egg, Indomie Special | Tea & Bread | 0.0139 | 0.279 | 8.09 |
| Yam & Egg, Moi Moi & Custard | Bread & Egg Sauce | 0.0104 | 0.330 | 7.96 |
| Bread & Egg Sauce | Yam & Egg, Moi Moi & Custard | 0.0104 | 0.252 | 7.96 |
| Pancakes | Yam & Egg, Indomie Special | 0.0116 | 0.394 | 7.92 |
| Yam & Egg, Indomie Special | Pancakes | 0.0116 | 0.234 | 7.92 |
| Yam & Egg | Tea & Bread, Indomie Special | 0.0139 | 0.217 | 7.88 |
| Tea & Bread, Indomie Special | Yam & Egg | 0.0139 | 0.503 | 7.88 |
| Bread & Egg Sauce | Yam & Egg, Indomie Special | 0.0161 | 0.388 | 7.80 |
| Yam & Egg, Indomie Special | Bread & Egg Sauce | 0.0161 | 0.323 | 7.80 |
