"""
common.py - shared settings and helpers for every DineIQ script.

Why this file exists:
  * ALL paths are built from this file's location, so you can run any script from any folder
    (the "Path does not exist ... data/features/data/features" mistake cannot happen any more).
  * Windows/Mac Spark setup lives in ONE place (get_spark).
  * Every dataset is saved as ONE parquet file with pyarrow (no hadoop.dll / winutils problems on write).
  * The column "contracts" below are the agreement between the Spark scripts and the pandas scripts.
"""
import contextlib
import json
import os
import shutil
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DINEIQ_DATA", ROOT / "data"))
RAW, CLEAN, QUAR = DATA / "raw", DATA / "clean", DATA / "quarantine"
FEAT, RES, PART = DATA / "features", DATA / "results", DATA / "parquet_partitioned"
REPORTS, MODELS, SAMPLES = ROOT / "reports", ROOT / "models", ROOT / "sample_data"
DB_PATH = ROOT / "database" / "dineiq_app.db"
TABLES = ["menu_categories", "menu_items", "restaurants", "customers", "pricing_history", "promotions",
          "orders", "order_items", "ratings", "inventory", "wastage"]
GENERATED_BY_PIPELINE_VERSION = "1.0"

# ----------------------------------------------------------------------------- analytics settings (documented in the report)
LABEL_CFG = dict(high_pct=0.50, waste_ok=0.12, qual_pd=0.40, qual_ho=0.55, min_units=20, min_history_days=60, neutral_rating=3.5)
RISK_THRESHOLD = 0.10          # a month is "high wastage risk" when wasted/prepared >= 10%
MIN_PREPARED_FOR_RISK = 8
CLASS_FEATURES = ["units", "net_revenue", "profit_margin", "n_orders", "avg_discount_pct", "promotion_dependency",
                  "weekend_share", "repeat_purchase_rate", "avg_rating", "n_ratings", "wastage_percent",
                  "sales_trend", "base_cost", "avg_unit_price"]
CLASSES = ["Profit Driver", "Volume Driver", "Hidden Opportunity", "Low Performer"]
SEGMENT_FEATURES = ["recency_days", "frequency", "monetary", "avg_order_value", "visits_per_month", "promo_order_share",
                    "tenure_days", "orders_last_90"]
RISK_FEATURES = ["lag1_rate", "lag2_rate", "avg3_rate", "lag1_consumed", "lag1_prepared", "promo_share", "month_sin", "month_cos",
                 "item_avg_rate_hist", "loc_avg_rate_hist", "prepared_qty_log"]
FORECAST_ENTITIES = {"item": ("item_id", "item_name"), "category": ("category_id", "category_name"),
                     "location": ("location_id", "restaurant_name")}
DEFAULT_HORIZONS = [2, 4, 8]

# ----------------------------------------------------------------------------- column contracts
CONTRACT = {
    "lines_featured": ["order_item_id", "order_id", "order_date", "order_month", "order_hour", "hour_band", "day_of_week",
                       "is_weekend", "is_peak_hour", "location_id", "restaurant_name", "city", "region", "channel",
                       "payment_method", "status", "is_completed", "promo_id", "is_promo_line", "customer_id", "is_guest",
                       "item_id", "item_name", "category_id", "category_name", "quantity", "unit_price", "discount_pct",
                       "gross_revenue", "discount_amount", "net_revenue", "unit_cost", "line_cost", "line_profit",
                       "basket_size", "line_rating"],
    "orders_featured": ["order_id", "customer_id", "is_guest", "location_id", "city", "region", "channel", "payment_method",
                        "status", "is_completed", "promo_id", "has_promo", "order_date", "order_datetime", "order_hour",
                        "hour_band", "day_of_week", "is_weekend", "n_lines", "units", "gross_revenue", "discount_amount",
                        "net_revenue", "line_cost", "profit"],
    "item_features": ["item_id", "item_name", "category_id", "category_name", "base_cost", "launch_price", "current_price",
                      "n_price_changes", "price_change_pct", "is_active", "introduced_date", "first_sale_date", "last_sale_date",
                      "days_on_menu", "active_days", "days_since_last_sale", "avg_gap_days", "n_orders", "total_quantity_sold",
                      "gross_revenue", "discount_amount", "net_revenue", "total_cost", "total_profit", "profit_margin",
                      "avg_discount_pct", "promotion_dependency", "weekend_share", "peak_hour_share", "units_last_90",
                      "units_prev_90", "sales_trend", "repeat_purchase_rate", "n_customers", "avg_rating", "n_ratings",
                      "rating_recent_avg", "rating_prior_avg", "rating_trend", "wasted_qty", "wastage_cost", "prepared_qty",
                      "consumed_qty", "wastage_percent", "is_new_item"],
    "item_location_features": ["item_id", "location_id", "item_name", "category_id", "units", "net_revenue", "total_profit",
                               "profit_margin", "n_orders", "avg_unit_price", "avg_discount_pct", "promotion_dependency",
                               "weekend_share", "repeat_purchase_rate", "avg_rating", "n_ratings", "wasted_qty", "prepared_qty",
                               "wastage_percent", "units_last_90", "units_prev_90", "sales_trend", "base_cost",
                               "first_sale_date", "history_days", "insufficient_history"],
    "customer_features": ["customer_id", "home_city", "age_bracket", "signup_date", "first_order_date", "last_order_date",
                          "recency_days", "frequency", "monetary", "avg_order_value", "tenure_days", "visits_per_month",
                          "avg_days_between_orders", "promo_order_share", "n_categories", "favorite_category",
                          "favorite_channel", "favorite_hour_band", "home_location_id", "orders_last_90", "orders_prev_90",
                          "spend_last_90", "spend_prev_90"],
    "weekly_item": ["entity_id", "entity_name", "week_start", "units", "net_revenue", "orders", "promo_units"],
    "weekly_category": ["entity_id", "entity_name", "week_start", "units", "net_revenue", "orders", "promo_units"],
    "weekly_location": ["entity_id", "entity_name", "week_start", "units", "net_revenue", "orders", "promo_units"],
    "wastage_monthly": ["item_id", "location_id", "month", "prepared_qty", "consumed_qty", "wasted_qty", "wastage_cost",
                        "waste_rate", "promo_share"],
    "daily_location": ["order_date", "location_id", "orders", "units", "net_revenue", "profit"],
    "daily_item": ["order_date", "item_id", "units", "net_revenue"],
}


# ----------------------------------------------------------------------------- housekeeping
def ensure_dirs():
    for p in (RAW, CLEAN, QUAR, FEAT, RES, PART, REPORTS, MODELS, SAMPLES, DB_PATH.parent):
        p.mkdir(parents=True, exist_ok=True)


def manifest():
    f = RAW / "_manifest.json"
    return json.loads(f.read_text()) if f.exists() else {}


def banner(script):
    mf = manifest()
    print("=" * 78)
    print(f"{script}   | data folder: {DATA}")
    if mf:
        rc = mf.get("row_counts", {})
        print(f"raw dataset: scale={mf.get('scale')} seed={mf.get('seed')}  order_items={rc.get('order_items', 0):,}  orders={rc.get('orders', 0):,}")
        if mf.get("scale") == "dev":
            print("!! This is the DEV dataset (for testing). Regenerate with --scale full for the final run.")
    print("=" * 78)


@contextlib.contextmanager
def job(name):
    """Logs every pipeline step (name, status, duration) to reports/job_log.jsonl - shown on the app's Admin page (SRS: Spark job monitoring)."""
    ensure_dirs()
    t0, status = time.time(), "success"
    print(f"\n>>> {name} ...")
    try:
        yield
    except BaseException as e:
        status = f"failed: {type(e).__name__}: {str(e)[:160]}"
        raise
    finally:
        rec = dict(job=name, status=status, seconds=round(time.time() - t0, 1), finished=time.strftime("%Y-%m-%d %H:%M:%S"),
                   scale=manifest().get("scale", "?"))
        with open(REPORTS / "job_log.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"<<< {name}: {status} in {rec['seconds']}s")


def model_version(name):
    return f"{name}-v{GENERATED_BY_PIPELINE_VERSION}-{time.strftime('%Y%m%d')}"


def register_model(name, version, metrics, extra=None):
    ensure_dirs()
    f = RES / "model_registry.json"
    reg = json.loads(f.read_text()) if f.exists() else []
    reg = [r for r in reg if r["name"] != name]
    reg.append(dict(name=name, version=version, trained_at=time.strftime("%Y-%m-%d %H:%M:%S"), metrics=metrics, **(extra or {})))
    f.write_text(json.dumps(reg, indent=2, default=str))


def dev_log(text):
    """Append to DEVELOPMENT_LOG.md (SRS 1.8: teams must keep a development log)."""
    with open(ROOT / "DEVELOPMENT_LOG.md", "a", encoding="utf-8") as fh:
        fh.write(f"- {time.strftime('%Y-%m-%d %H:%M')} - {text}\n")


# ----------------------------------------------------------------------------- Spark
def get_spark(app="DineIQ", shuffle_partitions=16):
    if os.name == "nt":                                   # Windows only; Mac/Linux never need this
        hh = os.environ.get("HADOOP_HOME") or r"C:\hadoop"
        if Path(hh).exists():
            os.environ["HADOOP_HOME"] = hh
            os.environ["PATH"] = str(Path(hh) / "bin") + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    from pyspark.sql import SparkSession
    spark = (SparkSession.builder.appName(app).master("local[*]")
             .config("spark.driver.memory", os.environ.get("DINEIQ_SPARK_MEM", "4g"))
             .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
             .config("spark.sql.ansi.enabled", "false")            # invalid casts become NULL instead of crashing (Spark 4 default is strict)
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.ui.showConsoleProgress", "false")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def spark_schemas():
    """Explicit schemas (SRS Step 3). Dates stay STRINGS on purpose: the cleaning step validates and converts them."""
    from pyspark.sql.types import (StructType, StructField, StringType, IntegerType, DoubleType)
    S, I, D = StringType(), IntegerType(), DoubleType()

    def st(*cols):
        return StructType([StructField(n, t, True) for n, t in cols])
    return {
        "menu_categories": st(("category_id", S), ("category_name", S)),
        "menu_items": st(("item_id", S), ("item_name", S), ("category_id", S), ("base_price", D), ("base_cost", D), ("unit", S),
                         ("description", S), ("is_active", S), ("introduced_date", S)),
        "restaurants": st(("location_id", S), ("restaurant_name", S), ("city", S), ("area", S), ("region", S), ("seats", I), ("opened_date", S)),
        "customers": st(("customer_id", S), ("home_city", S), ("age_bracket", S), ("signup_date", S)),
        "pricing_history": st(("price_id", S), ("item_id", S), ("price", D), ("effective_from", S), ("effective_to", S)),
        "promotions": st(("promo_id", S), ("promo_name", S), ("promo_type", S), ("discount_pct", D), ("start_date", S), ("end_date", S),
                         ("scope", S), ("applicable_items", S), ("category_id", S), ("location_id", S)),
        "orders": st(("order_id", S), ("customer_id", S), ("location_id", S), ("order_datetime", S), ("order_date", S), ("channel", S),
                     ("payment_method", S), ("status", S), ("promo_id", S)),
        "order_items": st(("order_item_id", S), ("order_id", S), ("item_id", S), ("quantity", I), ("unit_price", D),
                          ("discount_pct", D), ("line_total", D)),
        "ratings": st(("rating_id", S), ("order_id", S), ("item_id", S), ("customer_id", S), ("rating_date", S), ("rating_value", I)),
        "inventory": st(("inventory_id", S), ("item_id", S), ("location_id", S), ("week_start", S), ("opening_stock", I),
                        ("replenished_qty", I), ("prepared_qty", I), ("consumed_qty", I), ("closing_stock", I), ("unit", S)),
        "wastage": st(("wastage_id", S), ("item_id", S), ("location_id", S), ("waste_date", S), ("quantity_wasted", I),
                      ("unit_cost", D), ("wastage_cost", D), ("reason", S)),
    }


def raw_path(table):
    """order_items is delivered as many monthly part files (multiple-file ingestion); every other table is one CSV."""
    return str(RAW / "order_items" / "*.csv") if table == "order_items" else str(RAW / f"{table}.csv")


# ----------------------------------------------------------------------------- parquet IO (single-file, pyarrow)
def _pickle_mode():
    return os.environ.get("DINEIQ_IO") == "pickle"          # only used by automated sandbox tests


def save_parquet(df, path):
    """Save a Spark OR pandas DataFrame as ONE parquet file. Returns the row count."""
    import pandas as pd
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir():
        shutil.rmtree(path)
    if isinstance(df, pd.DataFrame):
        if _pickle_mode():
            df.to_pickle(path); return len(df)
        import pyarrow as pa, pyarrow.parquet as pq
        table = pa.Table.from_pandas(df, preserve_index=False)
    else:
        if _pickle_mode():
            df.toPandas().to_pickle(path); return -1
        import pyarrow as pa, pyarrow.parquet as pq
        try:
            table = df.toArrow()                                  # PySpark 4.x
        except AttributeError:
            table = pa.Table.from_pandas(df.toPandas(), preserve_index=False)
    pq.write_table(table, path)
    return table.num_rows


def read_pandas(path, columns=None):
    """Read one parquet file OR a Spark-written parquet folder into pandas. date columns come back as datetime64."""
    import pandas as pd
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. Run the earlier pipeline steps first (see README run order).")
    if _pickle_mode():
        df = pd.read_pickle(path)
        return df[columns] if columns else df
    import pyarrow.parquet as pq
    return pq.read_table(path, columns=columns).to_pandas(date_as_object=False)


def read_spark(spark, path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. Run the earlier pipeline steps first (see README run order).")
    return spark.read.parquet(str(path))


def check_contract(name, cols):
    missing = [c for c in CONTRACT[name] if c not in cols]
    if missing:
        raise ValueError(f"'{name}' is missing contract columns {missing}")


# ----------------------------------------------------------------------------- shared analytics definitions
def split_bucket(item_id, location_id):
    """Deterministic 0-99 bucket so Spark and Python pipelines use IDENTICAL train/validation/test records."""
    return zlib.crc32(f"{item_id}|{location_id}".encode("utf-8")) % 100


def split_name(bucket):
    return "train" if bucket < 60 else ("validation" if bucket < 80 else "test")


def rule_label(df):
    """Business rule that DEFINES the four menu classes (SRS Step 10). Uses several indicators, never one field.
    Returns a Series of labels. Rows with insufficient history get 'Insufficient History'."""
    import numpy as np
    import pandas as pd
    c = LABEL_CFG
    ok = ~df["insufficient_history"].astype(bool)
    d = df[ok].copy()
    n = max(len(d) - 1, 1)
    pr = lambda s: (s.rank(method="min") - 1) / n
    rating = d["avg_rating"].fillna(c["neutral_rating"])
    rep = d["repeat_purchase_rate"].fillna(0)
    waste = d["wastage_percent"].fillna(0)
    vol, mar = pr(d["units"]), pr(d["profit_margin"])
    qual = .5 * pr(rating) + .25 * pr(rep) + .25 * (1 - pr(waste))
    hi_v, hi_m = vol >= c["high_pct"], mar >= c["high_pct"]
    lab = np.select([hi_v & hi_m & (waste <= c["waste_ok"]) & (qual >= c["qual_pd"]),
                     hi_v & (~hi_m | (waste > c["waste_ok"])),
                     ~hi_v & hi_m & (qual >= c["qual_ho"])],
                    ["Profit Driver", "Volume Driver", "Hidden Opportunity"], "Low Performer")
    out = pd.Series("Insufficient History", index=df.index, dtype=object)
    out[ok] = lab
    return out


def classification_metrics(y_true, y_pred, labels=None):
    """accuracy, weighted-F1, macro-F1 and confusion matrix, with no external library."""
    labels = labels or sorted(set(y_true) | set(y_pred))
    n = len(y_true)
    cm = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    f1s, sup = [], []
    for l in labels:
        tp = cm[l][l]; fp = sum(cm[a][l] for a in labels) - tp; fn = sum(cm[l].values()) - tp
        pr_ = tp / (tp + fp) if tp + fp else 0.0; rc = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * pr_ * rc / (pr_ + rc) if pr_ + rc else 0.0); sup.append(tp + fn)
    acc = sum(cm[l][l] for l in labels) / n if n else 0.0
    return dict(accuracy=round(acc, 4), macro_f1=round(sum(f1s) / len(f1s), 4),
                weighted_f1=round(sum(f * s for f, s in zip(f1s, sup)) / max(sum(sup), 1), 4), n=n, confusion=cm)


def regression_metrics(y, p):
    import numpy as np
    y, p = np.asarray(y, float), np.asarray(p, float)
    mae = float(np.mean(np.abs(y - p))); rmse = float(np.sqrt(np.mean((y - p) ** 2)))
    m = y >= 5
    mape = float(np.mean(np.abs(y[m] - p[m]) / y[m]) * 100) if m.any() else float("nan")
    ss = float(np.sum((y - y.mean()) ** 2)); r2 = 1 - float(np.sum((y - p) ** 2)) / ss if ss > 0 else float("nan")
    return dict(MAE=round(mae, 3), RMSE=round(rmse, 3), MAPE=round(mape, 2), R2=round(r2, 4), n=int(len(y)))


def name_segment(row, q):
    """Turns a customer (or a cluster centre) into a business segment name. q = dict of population percentiles."""
    if row["monetary"] >= q["monetary_75"] and row["frequency"] >= q["frequency_75"] and row["recency_days"] <= q["recency_50"]:
        return "High-Value Loyal"
    if row["tenure_days"] <= q["tenure_20"]:
        return "New Customers"
    if row["recency_days"] >= q["recency_66"] and (row["frequency"] >= q["frequency_50"] or row["monetary"] >= q["monetary_50"]):
        return "At-Risk"
    if row["promo_order_share"] >= .5:
        return "Promotion-Driven"
    if row["frequency"] >= q["frequency_66"]:
        return "Frequent"
    return "Occasional"


def segment_quantiles(df):
    return dict(monetary_75=df.monetary.quantile(.75), monetary_50=df.monetary.quantile(.5), frequency_75=df.frequency.quantile(.75),
                frequency_66=df.frequency.quantile(.66), frequency_50=df.frequency.quantile(.5), recency_50=df.recency_days.quantile(.5),
                recency_66=df.recency_days.quantile(.66), tenure_20=df.tenure_days.quantile(.2))
