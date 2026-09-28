"""
test_feature_tables.py -- smoke tests over the Parquet feature tables Pair A
hands to everyone downstream. These are deliberately simple: they check that
the shape and key columns of each table are what every dashboard and model
script assumes, so a future change to feature_engineering.py that silently
breaks a downstream page fails here first, in a few seconds, instead of
showing up as a confusing error inside Streamlit.

Run from the project root (after generating and processing the dataset, or
against the included parquet_data/ sample tables):

    pip install pytest pandas pyarrow
    pytest tests/ -v
"""
import os
import pandas as pd
import pytest

FEATURES_DIR = "parquet_data"
MODELS_DIR = "models"


def _path(*parts):
    return os.path.join(*parts)


@pytest.fixture(scope="module")
def item_features():
    path = _path(FEATURES_DIR, "item_features.parquet")
    if not os.path.exists(path):
        pytest.skip(f"{path} not found -- run the Spark pipeline or use the included sample first")
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def customer_rfm():
    path = _path(FEATURES_DIR, "customer_rfm.parquet")
    if not os.path.exists(path):
        pytest.skip(f"{path} not found -- run the Spark pipeline or use the included sample first")
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def order_lines_features():
    path = _path(FEATURES_DIR, "order_lines_features.parquet")
    if not os.path.exists(path):
        pytest.skip(f"{path} not found -- run the Spark pipeline or use the included sample first")
    return pd.read_parquet(path)


# ---------------------------------------------------------------------
# item_features.parquet -- one row per menu item
# ---------------------------------------------------------------------
def test_item_features_has_one_row_per_item(item_features):
    assert item_features["item_id"].is_unique, "item_features must have exactly one row per item_id"


def test_item_features_required_columns_present(item_features):
    required = {"item_id", "item_name", "category_name", "profit_margin",
                "total_quantity_sold", "avg_rating", "wastage_percent"}
    missing = required - set(item_features.columns)
    assert not missing, f"item_features is missing expected columns: {missing}"


def test_profit_margin_is_a_fraction(item_features):
    # profit_margin = total_profit / net_revenue -- should read as a fraction,
    # not a raw currency amount or a 0-100 percentage
    valid = item_features["profit_margin"].dropna()
    assert valid.between(-2, 2).all(), (
        "profit_margin looks out of range for a fraction -- check it wasn't "
        "accidentally saved as a percentage or a currency amount"
    )


# ---------------------------------------------------------------------
# customer_rfm.parquet -- one row per customer with >=1 completed order
# ---------------------------------------------------------------------
def test_customer_rfm_has_one_row_per_customer(customer_rfm):
    assert customer_rfm["customer_id"].is_unique, "customer_rfm must have exactly one row per customer_id"


def test_recency_days_is_non_negative(customer_rfm):
    assert (customer_rfm["recency_days"] >= 0).all(), "recency_days cannot be negative"


def test_frequency_is_at_least_one(customer_rfm):
    # every customer in this table has >=1 completed order by definition
    assert (customer_rfm["frequency"] >= 1).all(), (
        "every row in customer_rfm should represent a customer with at least "
        "one completed order"
    )


# ---------------------------------------------------------------------
# order_lines_features.parquet -- one row per order_id + item_id
# ---------------------------------------------------------------------
def test_order_lines_is_completed_is_binary(order_lines_features):
    assert set(order_lines_features["is_completed"].unique()).issubset({0, 1}), (
        "is_completed should only ever be 0 or 1"
    )


def test_net_revenue_is_non_negative_for_completed_lines(order_lines_features):
    completed = order_lines_features[order_lines_features["is_completed"] == 1]
    assert (completed["net_revenue"] >= 0).all(), (
        "a completed order line should never have negative net_revenue"
    )


def test_no_duplicate_order_item_lines(order_lines_features):
    dupes = order_lines_features.duplicated(subset=["order_id", "item_id"]).sum()
    assert dupes == 0, f"found {dupes} duplicate (order_id, item_id) rows -- the join key should be unique"
