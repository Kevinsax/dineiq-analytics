"""
config/paths.py -- single source of truth for the folder layout, so every
script and dashboard page points at the same locations instead of repeating
relative-path strings. Import from here instead of hard-coding paths.

    from config.paths import RAW_DIR, FEATURES_DIR, MODELS_DIR

Run everything from the project root -- every path below is relative to it.
"""
RAW_DIR = "raw_data"
PROCESSED_DIR = "processed_data"
FEATURES_DIR = "parquet_data"
MODELS_DIR = "models"
REPORTS_DIR = "reports"
