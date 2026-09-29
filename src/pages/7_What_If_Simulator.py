"""
7_What_If_Simulator.py  --  Pair C, Step 10: What-If Scenario Analysis (SRS Steps 40-41)
# UI reviewed and confirmed working end-to-end — Oyibo Nuhu
Honest scope note: nobody in this project (Pair A or Pair B) fitted a real
price-elasticity model from historical price changes -- that's a bigger data
job (pricing_history.parquet joined against demand over time) than there's
time for before the deadline. So this simulator uses a simple, clearly
labeled assumption: you pick how much demand is expected to shift per 1%
price change (the "elasticity" slider), and it recalculates revenue/profit
from there. SRS Step 41 explicitly requires simulated output to be labeled
as an estimate, not an actual result -- this page does that up front rather
than pretending the number is more rigorous than it is.
"""
import streamlit as st

from utils import load_item_features

st.set_page_config(page_title="What-If Simulator -- DineIQ", page_icon="\U0001F52E", layout="wide")
st.title("\U0001F52E What-If Scenario Simulator")
st.caption(
    "Every number below is an **estimate** driven by an elasticity assumption you set with the "
    "sliders, not a fitted model -- move a slider and watch the numbers respond."
)
with st.expander("Why an assumption instead of a fitted model?"):
    st.write(
        "A real price-elasticity model would need pricing_history joined against demand over time -- "
        "a bigger data job than the deadline allowed. This simulator uses a linear elasticity "
        "assumption instead, set by you below, which is why it's labeled an estimate throughout."
    )

items = load_item_features()
item_name = st.selectbox("\U0001F37D Choose a dish", sorted(items["item_name"].unique()))
row = items[items["item_name"] == item_name].iloc[0]

st.subheader(f"Current performance -- {item_name}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Units sold", f"{row.total_quantity_sold:,.0f}")
col2.metric("Net revenue", f"₦{row.net_revenue:,.0f}")
col3.metric("Profit margin", f"{row.profit_margin:.1%}")
col4.metric("Base cost/unit", f"₦{row.base_cost:,.0f}")

st.divider()
st.subheader("Scenario")

scenario = st.radio("What do you want to simulate?", ["Change price", "Change discount %", "Change prep quantity"], horizontal=True)

if scenario == "Change price":
    price_change_pct = st.slider("Price change (%)", -30, 30, 10, step=5)
    elasticity = st.slider(
        "Assumed demand elasticity", 0.0, 3.0, 1.0, step=0.1,
        help="1.0 = a 10% price rise costs 10% of unit sales. Your assumption, not a fitted number.",
    )
    avg_price = row.net_revenue / row.total_quantity_sold if row.total_quantity_sold else 0
    new_price = avg_price * (1 + price_change_pct / 100)
    demand_change_pct = -elasticity * price_change_pct
    new_quantity = max(0, row.total_quantity_sold * (1 + demand_change_pct / 100))
    new_revenue = new_price * new_quantity
    new_cost = row.base_cost * new_quantity
    new_profit = new_revenue - new_cost
    new_margin = new_profit / new_revenue if new_revenue else 0

elif scenario == "Change discount %":
    discount_change = st.slider("Discount change (percentage points)", -20, 20, 5, step=5)
    elasticity = st.slider(
        "Assumed demand lift per 1pp discount", 0.0, 5.0, 1.5, step=0.5,
        help="How much extra volume 1 extra point of discount is assumed to buy. Your assumption.",
    )
    demand_change_pct = elasticity * discount_change
    new_quantity = max(0, row.total_quantity_sold * (1 + demand_change_pct / 100))
    avg_price = row.net_revenue / row.total_quantity_sold if row.total_quantity_sold else 0
    effective_discount_shift = discount_change / 100
    new_price = avg_price * (1 - effective_discount_shift)
    new_revenue = new_price * new_quantity
    new_cost = row.base_cost * new_quantity
    new_profit = new_revenue - new_cost
    new_margin = new_profit / new_revenue if new_revenue else 0

else:  # Change prep quantity
    prep_change_pct = st.slider("Prep quantity change (%)", -50, 50, -20, step=5)
    st.caption("Estimates the wastage-cost effect of preparing more or less, assuming sales stay flat.")
    new_quantity = row.total_quantity_sold  # sales assumed unchanged
    current_waste_units = row.total_quantity_sold * row.wastage_percent / (1 - row.wastage_percent) if row.wastage_percent < 1 else 0
    new_waste_units = max(0, current_waste_units * (1 + prep_change_pct / 100))
    waste_cost_before = current_waste_units * row.base_cost
    waste_cost_after = new_waste_units * row.base_cost
    new_revenue = row.net_revenue
    new_profit = row.total_profit - (waste_cost_after - waste_cost_before)
    new_margin = new_profit / new_revenue if new_revenue else 0

st.divider()
st.subheader("\U0001F4CA Estimated impact")
c1, c2, c3 = st.columns(3)
c1.metric("Revenue", f"₦{new_revenue:,.0f}", delta=f"{new_revenue - row.net_revenue:+,.0f}")
c2.metric("Profit", f"₦{new_profit:,.0f}", delta=f"{new_profit - row.total_profit:+,.0f}")
c3.metric("Margin", f"{new_margin:.1%}", delta=f"{new_margin - row.profit_margin:+.1%}")
