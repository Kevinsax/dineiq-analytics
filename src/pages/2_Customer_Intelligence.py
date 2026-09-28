"""
2_Customer_Intelligence.py  --  Pair C, Step 5: Customer Intelligence Dashboard (SRS Step 44)
"""
import plotly.express as px
import streamlit as st

from utils import load_customer_segments, download_button

st.set_page_config(page_title="Customer Intelligence -- DineIQ", layout="wide")
st.title("Customer Intelligence Dashboard")
st.caption("RFM segments -- who's loyal, who's slipping away, and who's brand new.")

segments = load_customer_segments()

seg_filter = st.multiselect(
    "Filter by segment", sorted(segments["segment"].unique()), default=sorted(segments["segment"].unique())
)
shown = segments[segments["segment"].isin(seg_filter)]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Customers shown", f"{len(shown):,}")
col2.metric("Loyal High Spenders", f"{(segments['segment'] == 'Loyal High Spender').sum():,}")
col3.metric("At Risk", f"{(segments['segment'] == 'At Risk').sum():,}")
col4.metric("New Customers", f"{(segments['segment'] == 'New Customer').sum():,}")

st.divider()

left, right = st.columns(2)
with left:
    st.subheader("Segment distribution")
    counts = segments["segment"].value_counts().reset_index()
    counts.columns = ["segment", "customers"]
    fig = px.pie(counts, names="segment", values="customers", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("RFM score distribution")
    fig = px.histogram(shown, x="rfm_score", nbins=15, labels={"rfm_score": "Combined RFM score (3-15)"})
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Recency vs. monetary value, by segment")
fig = px.scatter(
    shown.sample(min(5000, len(shown)), random_state=42), x="recency_days", y="monetary", color="segment",
    labels={"recency_days": "Days since last order", "monetary": "Lifetime spend (₦)"},
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Customer table")
st.dataframe(
    shown[["customer_id", "recency_days", "frequency", "monetary", "rfm_score", "segment"]].sort_values("monetary", ascending=False),
    use_container_width=True, hide_index=True,
)

download_button(shown, "customer segments", "customer_intelligence_export.csv")
