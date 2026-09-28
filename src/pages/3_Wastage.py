"""
3_Wastage.py  --  Pair C, Step 6: Wastage Dashboard (SRS Step 45)
"""
import plotly.express as px
import streamlit as st

from utils import load_wastage_risk, download_button

st.set_page_config(page_title="Wastage -- DineIQ", page_icon="\U0001F5D1", layout="wide")
st.title("\U0001F5D1 Wastage Dashboard")
st.caption("What's being thrown away, and which dish is likely to be next.")

items = load_wastage_risk()  # item_features columns + predicted_wastage_risk

col1, col2, col3 = st.columns(3)
col1.metric("\U0001F5D1 Avg wastage % across menu", f"{items['wastage_percent'].mean():.1%}")
highest_wastage_item = items.sort_values("wastage_percent", ascending=False).iloc[0]["item_name"]
col2.metric("\U0001F6AE Highest wastage item", highest_wastage_item)
highest_predicted_risk_item = (
    items.nlargest(1, "predicted_wastage_risk")["item_name"].iloc[0]
)
col3.metric("\U0001F52E Highest predicted risk item", highest_predicted_risk_item)

st.divider()

left, right = st.columns(2)
with left:
    st.subheader("Top 10 by actual wastage %")
    top_actual = items.sort_values("wastage_percent", ascending=False).head(10)
    fig = px.bar(top_actual, x="item_name", y="wastage_percent", labels={"item_name": "Dish", "wastage_percent": "Wastage %"})
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top 10 by predicted wastage risk")
    top_pred = items.sort_values("predicted_wastage_risk", ascending=False).head(10)
    fig = px.bar(top_pred, x="item_name", y="predicted_wastage_risk", labels={"item_name": "Dish", "predicted_wastage_risk": "Predicted risk score"})
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Wastage by category")
by_cat = items.groupby("category_name")["wastage_percent"].mean().sort_values(ascending=False).reset_index()
fig = px.bar(by_cat, x="category_name", y="wastage_percent", labels={"category_name": "Category", "wastage_percent": "Avg wastage %"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Full wastage table")
st.dataframe(
    items[["item_id", "item_name", "category_name", "wastage_percent", "predicted_wastage_risk", "total_quantity_sold", "avg_rating"]]
    .sort_values("wastage_percent", ascending=False),
    use_container_width=True, hide_index=True,
)

st.caption("Note: wastage_percent here is a whole-period total per dish, not a week-by-week trend -- "
           "see WASTAGE_PREDICTION_NOTES.md (from Pair B) for what a trend version would need.")
download_button(items, "wastage", "wastage_export.csv")
