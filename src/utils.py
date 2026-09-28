"""
utils.py -- shared data loading, filtering and export helpers for every
dashboard page. Every page imports from here instead of re-reading parquet
files itself, so a column-name fix only has to happen in one place.

This file is not a page itself -- Streamlit ignores it, and
Executive_Dashboard.py / the pages/ scripts import from it with
`from utils import ...`.

Path note: these are relative to the REPO ROOT, not to src/. Streamlit
(both locally and on Streamlit Community Cloud) sets its working directory
to wherever `streamlit run` was invoked from -- run it from the repo root
with `streamlit run src/Executive_Dashboard.py`, not from inside src/, or
these paths won't resolve. See the root README.md's "Launching the
dashboard" section.
"""
import os
import pandas as pd
import streamlit as st

MODELS_DIR = "models"
FEATURES_DIR = "parquet_data"
RAW_DIR = "raw_data"


def _read_parquet(path):
    """pd.read_parquet works whether the file is a single-file parquet
    (pandas/pyarrow wrote it) or a Spark-style folder of part-files, as
    long as pyarrow is installed -- no special-casing needed here."""
    if not os.path.exists(path):
        st.error(f"Missing file: `{path}`. Re-check the handoff from Pair B -- "
                  f"see HANDOFF_TO_PAIR_C.md for the full list of expected files.")
        st.stop()
    return pd.read_parquet(path)


@st.cache_data
def load_item_features():
    return _read_parquet(f"{FEATURES_DIR}/item_features.parquet")


@st.cache_data
def load_customer_rfm():
    return _read_parquet(f"{FEATURES_DIR}/customer_rfm.parquet")


@st.cache_data
def load_order_lines():
    df = _read_parquet(f"{FEATURES_DIR}/order_lines_features.parquet")
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


@st.cache_data
def load_spark_classification():
    return _read_parquet(f"{MODELS_DIR}/item_classification_spark.parquet")


@st.cache_data
def load_python_classification():
    return _read_parquet(f"{MODELS_DIR}/item_classification_python.parquet")


@st.cache_data
def load_classification_comparison():
    path = f"{MODELS_DIR}/classification_comparison.csv"
    if not os.path.exists(path):
        st.error(f"Missing file: `{path}`. Run python_pipeline/compare_classifications.py first.")
        st.stop()
    return pd.read_csv(path)


@st.cache_data
def load_customer_segments():
    return _read_parquet(f"{MODELS_DIR}/customer_segments.parquet")


@st.cache_data
def load_basket_rules():
    path = f"{MODELS_DIR}/basket_rules.csv"
    if not os.path.exists(path):
        st.error(f"Missing file: `{path}`. Run python_pipeline/basket_analysis.py first.")
        st.stop()
    return pd.read_csv(path)


@st.cache_data
def load_wastage_risk():
    return _read_parquet(f"{MODELS_DIR}/item_wastage_risk.parquet")


@st.cache_data
def load_demand_forecast():
    path = f"{MODELS_DIR}/demand_forecast.parquet"
    if not os.path.exists(path):
        st.error(f"Missing file: `{path}`. Run build_forecast.py (Step 2 of this guide) first -- "
                  f"this table doesn't come from Pair B, it's built fresh in this folder.")
        st.stop()
    return pd.read_parquet(path)


@st.cache_data
def load_forecast_metrics():
    path = f"{MODELS_DIR}/demand_forecast_metrics.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


@st.cache_data
def load_recommendations():
    path = f"{MODELS_DIR}/recommendations.csv"
    if not os.path.exists(path):
        st.error(f"Missing file: `{path}`. Run build_recommendations.py (Step 8 of this guide) first.")
        st.stop()
    return pd.read_csv(path)


@st.cache_data
def load_restaurants():
    path = f"{RAW_DIR}/restaurants.csv"
    if not os.path.exists(path):
        return pd.DataFrame(columns=["location_id", "restaurant_name", "city", "area", "region"])
    df = pd.read_csv(path)
    return df.drop_duplicates(subset=["location_id"])


def sidebar_filters(lines_df, restaurants_df, key_prefix=""):
    """Draws the shared filter widgets (SRS Step 48: date range, location,
    category, channel) in the sidebar and returns lines_df filtered down
    to what the user picked. Every dashboard page calls this the same way
    so filters behave identically everywhere."""
    st.sidebar.header("Filters")

    min_date, max_date = lines_df["order_date"].min(), lines_df["order_date"].max()
    date_range = st.sidebar.date_input(
        "Date range", value=(min_date.date(), max_date.date()),
        min_value=min_date.date(), max_value=max_date.date(),
        key=f"{key_prefix}_date",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
    else:
        start, end = min_date.date(), max_date.date()

    loc_options = ["All"] + sorted(lines_df["location_id"].dropna().unique().tolist())
    loc_labels = {"All": "All"}
    for loc_id in loc_options[1:]:
        match = restaurants_df[restaurants_df.location_id == loc_id]
        name = match.restaurant_name.iloc[0] if len(match) else loc_id
        loc_labels[loc_id] = f"{loc_id} - {name}"
    location = st.sidebar.selectbox(
        "Location", loc_options, format_func=lambda x: loc_labels.get(x, x), key=f"{key_prefix}_loc"
    )

    cat_options = ["All"] + sorted(lines_df["category_name"].dropna().unique().tolist())
    category = st.sidebar.selectbox("Menu category", cat_options, key=f"{key_prefix}_cat")

    chan_options = ["All"] + sorted(lines_df["channel"].dropna().unique().tolist())
    channel = st.sidebar.selectbox("Ordering channel", chan_options, key=f"{key_prefix}_chan")

    filtered = lines_df[
        (lines_df["order_date"].dt.date >= start) & (lines_df["order_date"].dt.date <= end)
    ]
    if location != "All":
        filtered = filtered[filtered["location_id"] == location]
    if category != "All":
        filtered = filtered[filtered["category_name"] == category]
    if channel != "All":
        filtered = filtered[filtered["channel"] == channel]

    st.sidebar.caption(f"{len(filtered):,} of {len(lines_df):,} order lines match these filters")
    return filtered


def download_button(df, label, filename):
    """SRS Step 49/50: every dashboard needs a way to export what it's showing."""
    st.download_button(
        label=f"Download {label} (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )
