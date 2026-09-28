# Customer Segmentation -- RFM

Segment definitions (score cutoffs used):

- **Loyal High Spender**: combined RFM score (r+f+m, each 1-5) is 12 or higher
- **At Risk**: recency score <= 2 (hasn't ordered recently) AND frequency score >= 3 (used to order regularly)
- **New Customer**: frequency score <= 2 AND recency score >= 4 (recent but few orders)
- **Regular**: everyone else

recency_days range in this dataset: 0 to 729

| Segment | Customers |
|---|---|
| Regular | 13,897 |
| Loyal High Spender | 8,700 |
| At Risk | 5,192 |
| New Customer | 3,253 |
