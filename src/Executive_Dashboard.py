"""
Executive_Dashboard.py  --  Pair C, Step 3: Executive Dashboard (Home Page)

This is the file you run to launch the whole app -- every other dashboard
lives in pages/ and Streamlit wires them into the sidebar navigation
automatically, purely from the filenames in that folder.

Run from the REPO ROOT (not from inside src/) -- utils.py's paths
(MODELS_DIR, FEATURES_DIR, RAW_DIR) are relative to the repo root:
    streamlit run src/Executive_Dashboard.py
"""
import os

import plotly.express as px
import streamlit as st

from utils import (load_item_features, load_order_lines, load_restaurants,
                    load_recommendations, sidebar_filters, download_button, MODELS_DIR)

st.set_page_config(page_title="DineIQ Analytics", page_icon="\U0001F37D", layout="wide")

st.title("\U0001F37D DineIQ Analytics -- Executive Dashboard")
st.caption("Restaurant performance, at a glance. Use the sidebar to filter every number on this page.")

lines = load_order_lines()
restaurants = load_restaurants()
items = load_item_features()

filtered = sidebar_filters(lines, restaurants, key_prefix="exec")
completed = filtered[filtered["is_completed"] == 1]

# ---- KPI row (SRS Step 42) ----
total_revenue = completed["net_revenue"].sum()
total_profit = completed["line_profit"].sum()
total_orders = completed["order_id"].nunique()
avg_order_value = total_revenue / total_orders if total_orders else 0
active_customers = completed["customer_id"].nunique()
repeat_customers = (completed.groupby("customer_id")["order_id"].nunique() > 1).sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("\U0001F4B0 Total Revenue", f"₦{total_revenue:,.0f}")
col2.metric("\U0001F4C8 Total Profit", f"₦{total_profit:,.0f}")
col3.metric("\U0001F9FE Total Orders", f"{total_orders:,}")
col4.metric("\U0001F4B3 Avg Order Value", f"₦{avg_order_value:,.0f}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("\U0001F465 Active Customers", f"{active_customers:,}")
col6.metric("\U0001F501 Repeat Customers", f"{repeat_customers:,}")
cancelled_orders = filtered[filtered["status"] == "Cancelled"]["order_id"].nunique()
col7.metric("\U0000274C Cancelled Orders", f"{cancelled_orders:,}")
col8.metric("\U0001F374 Menu Items Live", f"{items['item_id'].nunique():,}")

st.divider()

# ---- Revenue trend ----
left, right = st.columns(2)
with left:
    st.subheader("\U0001F4C8 Revenue over time")
    daily = completed.groupby(completed["order_date"].dt.date)["net_revenue"].sum().reset_index()
    fig = px.line(daily, x="order_date", y="net_revenue", labels={"order_date": "Date", "net_revenue": "Revenue (₦)"})
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("\U0001F35B Revenue by category")
    by_cat = completed.groupby("category_name")["net_revenue"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(by_cat, x="category_name", y="net_revenue", labels={"category_name": "Category", "net_revenue": "Revenue (₦)"})
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---- Critical recommendations preview ----
# Checked directly with os.path.exists rather than try/except: load_recommendations()
# calls st.stop() internally on a missing file, and st.stop() raises a BaseException
# subclass on purpose so an ordinary `except Exception` can't accidentally swallow it --
# which means it wouldn't have hit an except block here anyway, just halted the page.
st.subheader("\U000026A0 Critical recommendations")
if os.path.exists(f"{MODELS_DIR}/recommendations.csv"):
    recs = load_recommendations()
    critical = recs[recs["priority"].isin(["Critical", "High"])].head(8)
    st.dataframe(critical[["item_name", "recommended_action", "reason", "priority"]], use_container_width=True, hide_index=True)
    st.page_link("pages/6_Recommendations.py", label="See all recommendations →")
else:
    st.info("Recommendations haven't been built yet -- run build_recommendations.py, then reload this page.")

st.divider()
download_button(completed, "filtered order lines", "executive_dashboard_export.csv")
