# Recommendation Engine

Rule-based on purpose -- the SRS asks for evidence-based recommendations (Step 37), not a trained recommender model, and every row here has to justify itself with real numbers pulled from Pair B's output, never an unexplained suggestion (Step 38).

**72 recommendations generated**, by priority:

| Priority | Count |
|---|---|
| Medium | 36 |
| High | 27 |
| Critical | 9 |

## Rule categories used

1. Promote high-margin Hidden Opportunities
2. Reduce preparation quantity of high-wastage dishes
3. Review pricing of discount-dependent Low Performers
4. Remove or redesign persistent, poorly-rated Low Performers
5. Bundle frequently purchased items (from market basket analysis)
6. Increase stock ahead of categories with rising forecast demand
7. Target At Risk and Loyal High Spender customer segments

If there's time to go further: promotion effectiveness review and anomalous-location flagging are both in the SRS's example list (Step 37) but need promotions.csv and location-level aggregation this first pass doesn't build -- worth adding if the demo has room for one more "why" behind a recommendation.
