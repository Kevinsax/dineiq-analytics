"""
1_Menu_Intelligence.py  --  Pair C, Step 4: Menu Intelligence Dashboard (SRS Step 43)

Streamlit turns every file in pages/ into a sidebar navigation entry
automatically -- the leading number just controls the order they appear in.
"""
import plotly.express as px
import streamlit as st

from utils import load_python_classification, download_button

st.set_page_config(page_title="Menu Intelligence -- DineIQ", page_icon="\U0001F35B", layout="wide")
st.title("\U0001F35B Menu Intelligence Dashboard")
st.caption("Every dish, classified and ranked -- profit margin, volume, rating and wastage side by side.")

items = load_python_classification()  # item_features columns + python_label

label_filter = st.multiselect(
    "Filter by classification", sorted(items["python_label"].unique()),
    default=sorted(items["python_label"].unique()),
)
category_filter = st.multiselect(
    "Filter by category", sorted(items["category_name"].unique()),
    default=sorted(items["category_name"].unique()),
)
shown = items[items["python_label"].isin(label_filter) & items["category_name"].isin(category_filter)]

col1, col2, col3, col4 = st.columns(4)
col1.metric("\U0001F37D Dishes shown", f"{len(shown):,}")
col2.metric("\U0001F4C8 Avg margin", f"{shown['profit_margin'].mean():.1%}" if len(shown) else "--")
col3.metric("\U00002B50 Avg rating", f"{shown['avg_rating'].mean():.1f}" if len(shown) else "--")
col4.metric("\U0001F5D1 Avg wastage %", f"{shown['wastage_percent'].mean():.1%}" if len(shown) else "--")

st.divider()

st.subheader("\U0001F4CA Profit margin vs. sales volume")
fig = px.scatter(
    shown, x="total_quantity_sold", y="profit_margin", color="python_label",
    hover_name="item_name", size="net_revenue",
    labels={"total_quantity_sold": "Units sold", "profit_margin": "Profit margin", "python_label": "Classification"},
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Slow-moving items (bottom 10 by volume)")
slow = shown.sort_values("total_quantity_sold").head(10)
st.dataframe(
    slow[["item_id", "item_name", "category_name", "total_quantity_sold", "profit_margin", "avg_rating", "wastage_percent", "python_label"]],
    use_container_width=True, hide_index=True,
)

st.subheader("Full menu table")
st.dataframe(
    shown[["item_id", "item_name", "category_name", "profit_margin", "total_quantity_sold",
           "avg_rating", "avg_discount_pct", "wastage_percent", "python_label"]]
    .sort_values("profit_margin", ascending=False),
    use_container_width=True, hide_index=True,
)

download_button(shown, "menu intelligence", "menu_intelligence_export.csv")
