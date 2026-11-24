"""Dataset builder and feature engineering for extreme-event risk classification (Ticket R14).

Extracts leakage-free antecedent observations (past 7 days), seasonal harmonics, spatial
coordinates, climatology normals, and multi-model NWP forecast guidance for lead days h in {1, 2, 3}.

Enforces:
- Chronological train/embargo/test split (Rule S3):
  * Train: 2023-06-01 to 2024-04-23
  * Embargo: 2024-04-24 to 2024-04-30 (7 days)
  * Held-out Test: 2024-05-01 to 2024-10-31
- Zero temporal leakage: for target day d and lead day h, issue time is t = d - h.
  All antecedent features strictly use observations from date <= t.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.bias_correction.stations import STATIONS  # noqa: E402
from ml.extreme_event.eda import get_station_monthly_normals  # noqa: E402

DATA_DIR = ROOT / "ml" / "extreme_event" / "data"
PROCESSED_FILE = DATA_DIR / "processed_dataset.csv"
BIAS_DATASET_FILE = ROOT / "ml" / "bias_correction" / "data" / "processed_dataset.csv"

TRAIN_START = "2023-06-01"
TRAIN_END = "2024-04-23"
EMBARGO_START = "2024-04-24"
EMBARGO_END = "2024-04-30"
TEST_START = "2024-05-01"
TEST_END = "2024-10-31"

STAGE1_FEATURES = [
    "lead_day",
    "doy_sin",
    "doy_cos",
    "lat",
    "lon",
    "elev",
    "normal_tmax",
    "obs_tmax_lag1",
    "obs_tmax_lag2",
    "obs_tmax_lag3",
    "obs_dep_lag1",
    "obs_mean_7d",
    "persistence",
]

STAGE2_FEATURES = STAGE1_FEATURES + [
    "tmax_mmm",
    "tmax_gfs",
    "tmax_ecmwf",
    "tmax_icon",
    "recent_bias",
    "forecast_dep",
    "forecast_hw_rule",
]


def build_extreme_event_dataset(force: bool = False) -> pd.DataFrame:
    """Build the complete extreme event dataset with Stage 1 and Stage 2 features."""
    if not force and PROCESSED_FILE.exists():
        return pd.read_csv(PROCESSED_FILE)

    if not BIAS_DATASET_FILE.exists():
        raise FileNotFoundError(f"Underlying bias correction dataset missing: {BIAS_DATASET_FILE}")

    df_base = pd.read_csv(BIAS_DATASET_FILE)
    station_normals = get_station_monthly_normals()
    stations_map = {s["id"]: s for s in STATIONS}

    # First, build a lookup of daily station observations: (station_id, date) -> (observed_tmax, is_heatwave, normal_tmax)
    obs_lookup: dict[tuple[str, str], dict[str, float]] = {}

    unique_station_dates = df_base[["station_id", "date", "observed_tmax"]].drop_duplicates()
    for _, row in unique_station_dates.iterrows():
        st_id = row["station_id"]
        d_str = row["date"]
        obs_tmax = float(row["observed_tmax"])
        month = int(d_str.split("-")[1])
        norm = station_normals[st_id][month - 1]
        dep = obs_tmax - norm

        st = stations_map[st_id]
        is_coastal = st["zone"] in ["West Coast", "East Coast"]
        if is_coastal:
            is_hw = 1.0 if ((obs_tmax >= 37.0 and dep >= 4.5) or (obs_tmax >= 40.0)) else 0.0
        else:
            is_hw = 1.0 if ((obs_tmax >= 40.0 and dep >= 4.5) or (obs_tmax >= 45.0)) else 0.0

        obs_lookup[(st_id, d_str)] = {
            "obs_tmax": obs_tmax,
            "normal_tmax": norm,
            "dep_tmax": dep,
            "is_hw": is_hw,
        }

    # Now iterate through each sample and construct features at issue time t = d - lead_day
    rows: list[dict[str, Any]] = []

    for _, row in df_base.iterrows():
        st_id = row["station_id"]
        target_d_str = row["date"]
        lead = int(row["lead_day"])
        target_date = dt.date.fromisoformat(target_d_str)

        # Target label
        target_info = obs_lookup.get((st_id, target_d_str))
        if not target_info:
            continue
        is_hw = target_info["is_hw"]
        normal_tmax = target_info["normal_tmax"]

        # Issue date is t = target_date - lead days
        issue_date = target_date - dt.timedelta(days=lead)

        # Antecedent observations at issue date and prior (no leakage!)
        lag1_d = issue_date.isoformat()
        lag2_d = (issue_date - dt.timedelta(days=1)).isoformat()
        lag3_d = (issue_date - dt.timedelta(days=2)).isoformat()

        info1 = obs_lookup.get((st_id, lag1_d))
        info2 = obs_lookup.get((st_id, lag2_d))
        info3 = obs_lookup.get((st_id, lag3_d))

        # Fallbacks if slight data gaps in raw METAR
        obs_tmax_lag1 = info1["obs_tmax"] if info1 else normal_tmax
        obs_tmax_lag2 = info2["obs_tmax"] if info2 else obs_tmax_lag1
        obs_tmax_lag3 = info3["obs_tmax"] if info3 else obs_tmax_lag2

        obs_dep_lag1 = info1["dep_tmax"] if info1 else (obs_tmax_lag1 - normal_tmax)
        persistence = info1["is_hw"] if info1 else 0.0

        # Trailing 7 days up to issue date
        past_7_tmax = []
        for delta in range(7):
            d_prev = (issue_date - dt.timedelta(days=delta)).isoformat()
            if (st_id, d_prev) in obs_lookup:
                past_7_tmax.append(obs_lookup[(st_id, d_prev)]["obs_tmax"])
        obs_mean_7d = sum(past_7_tmax) / len(past_7_tmax) if past_7_tmax else obs_tmax_lag1

        # NWP forecast features for target date
        tmax_mmm = float(row["tmax_mmm"])
        tmax_gfs = float(row.get("tmax_gfs", tmax_mmm))
        tmax_ecmwf = float(row.get("tmax_ecmwf", tmax_mmm))
        tmax_icon = float(row.get("tmax_icon", tmax_mmm))
        recent_bias = float(row.get("recent_bias", 0.0))

        forecast_dep = tmax_mmm - normal_tmax
        st = stations_map[st_id]
        is_coastal = st["zone"] in ["West Coast", "East Coast"]
        if is_coastal:
            forecast_hw_rule = 1.0 if ((tmax_mmm >= 37.0 and forecast_dep >= 4.5) or (tmax_mmm >= 40.0)) else 0.0
        else:
            forecast_hw_rule = 1.0 if ((tmax_mmm >= 40.0 and forecast_dep >= 4.5) or (tmax_mmm >= 45.0)) else 0.0

        # Split assignment
        if TRAIN_START <= target_d_str <= TRAIN_END:
            split = "train"
        elif TEST_START <= target_d_str <= TEST_END:
            split = "test"
        else:
            split = "embargo"

        rows.append({
            "station_id": st_id,
            "date": target_d_str,
            "issue_date": issue_date.isoformat(),
            "lead_day": lead,
            "split": split,
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "elev": float(row["elev"]),
            "doy": int(row["doy"]),
            "doy_sin": float(row["doy_sin"]),
            "doy_cos": float(row["doy_cos"]),
            "normal_tmax": round(normal_tmax, 2),
            "obs_tmax_lag1": round(obs_tmax_lag1, 2),
            "obs_tmax_lag2": round(obs_tmax_lag2, 2),
            "obs_tmax_lag3": round(obs_tmax_lag3, 2),
            "obs_dep_lag1": round(obs_dep_lag1, 2),
            "obs_mean_7d": round(obs_mean_7d, 2),
            "persistence": float(persistence),
            "tmax_mmm": round(tmax_mmm, 2),
            "tmax_gfs": round(tmax_gfs, 2),
            "tmax_ecmwf": round(tmax_ecmwf, 2),
            "tmax_icon": round(tmax_icon, 2),
            "recent_bias": round(recent_bias, 2),
            "forecast_dep": round(forecast_dep, 2),
            "forecast_hw_rule": float(forecast_hw_rule),
            "observed_tmax": float(row["observed_tmax"]),
            "is_heatwave": int(is_hw),
        })

    out_df = pd.DataFrame(rows)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(PROCESSED_FILE, index=False)
    print(f"[OK] Extreme event dataset built: {len(out_df)} rows saved to {PROCESSED_FILE.relative_to(ROOT)}")
    return out_df


def load_extreme_event_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load train, embargo, and test data splits."""
    df = build_extreme_event_dataset()
    train_df = df[df["split"] == "train"].copy()
    embargo_df = df[df["split"] == "embargo"].copy()
    test_df = df[df["split"] == "test"].copy()
    return train_df, embargo_df, test_df


if __name__ == "__main__":
    df = build_extreme_event_dataset(force=True)
    print(df.groupby("split")["is_heatwave"].agg(["count", "sum", "mean"]))
