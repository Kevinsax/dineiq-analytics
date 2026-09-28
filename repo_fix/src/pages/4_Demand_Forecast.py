"""
4_Demand_Forecast.py  --  Pair C, Step 7: Forecast Dashboard (SRS Step 46)

Reads models/demand_forecast.parquet, which is NOT part of Pair B's
handoff -- it's built by python_pipeline/build_forecast.py. Run that
script first if this page errors out.
"""
import plotly.graph_objects as go
import streamlit as st

from utils import load_demand_forecast, load_forecast_metrics, download_button

st.set_page_config(page_title="Forecast -- DineIQ", layout="wide")
st.title("Forecast Dashboard")
st.caption("Historical vs. forecast demand, by menu category. Built directly from order history -- see FORECAST_NOTES.md for method and honest limitations.")

forecast = load_demand_forecast()
metrics = load_forecast_metrics()

category = st.selectbox("Category", sorted(forecast["category_name"].unique()))
cat_data = forecast[forecast["category_name"] == category].sort_values("week_start")

fig = go.Figure()
actual = cat_data[cat_data["row_type"].isin(["actual", "test"])]
fig.add_trace(go.Scatter(x=actual["week_start"], y=actual["actual_quantity"], mode="lines", name="Actual demand"))

test_pred = cat_data[cat_data["row_type"] == "test"]
fig.add_trace(go.Scatter(x=test_pred["week_start"], y=test_pred["forecast_quantity"], mode="lines", name="Model prediction (held-out test weeks)", line=dict(dash="dot")))

future = cat_data[cat_data["row_type"] == "forecast"]
fig.add_trace(go.Scatter(x=future["week_start"], y=future["forecast_quantity"], mode="lines+markers", name="Forecast (next 4 weeks)", line=dict(dash="dash", color="orange")))

fig.update_layout(xaxis_title="Week", yaxis_title="Units sold", legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True)

if metrics is not None:
    row = metrics[metrics["category_name"] == category]
    if len(row):
        r = row.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("MAE (baseline)", f"{r.mae_baseline:.1f}")
        col2.metric("MAE (model)", f"{r.mae_model:.1f}", delta=f"{r.mae_model - r.mae_baseline:+.1f}", delta_color="inverse")
        col3.metric("RMSE (model)", f"{r.rmse_model:.1f}")
        col4.metric("Beats baseline?", "Yes" if r.beats_baseline else "No")

    st.divider()
    st.subheader("All categories -- model vs. baseline")
    st.dataframe(metrics, use_container_width=True, hide_index=True)
    st.caption(f"The model beats the naive baseline on {int(metrics['beats_baseline'].sum())} of "
               f"{len(metrics)} categories by MAE -- said plainly rather than only showing the wins.")
else:
    st.info("demand_forecast_metrics.csv not found -- re-run build_forecast.py.")

st.divider()
download_button(forecast, "demand forecast", "demand_forecast_export.csv")
