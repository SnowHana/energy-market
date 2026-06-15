import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import holidays

from config import CLEAN_PARQUET, PEAK_HOURS, PEAK_WEEKDAYS

FEATURE_COLS = [
    "load_fc",
    "wind_fc",
    "solar_fc",
    "residual_load_fc",
    "hour",
    "dayofweek",
    "month",
    "is_holiday",
    "is_peak",
    "price_lag_24",
    "price_lag_168",
    "price_roll_mean_24",
    "price_roll_std_24",
    "price_roll_mean_168",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    de_holidays = holidays.Germany()

    # Calendar features
    df["hour"] = df.index.hour
    df["dayofweek"] = df.index.dayofweek
    df["month"] = df.index.month
    df["is_holiday"] = (
        pd.Series(df.index.date, index=df.index)
        .map(lambda d: d in de_holidays)
        .astype(int)
    )
    df["is_peak"] = (
        df["hour"].isin(PEAK_HOURS) & df["dayofweek"].isin(PEAK_WEEKDAYS)
    ).astype(int)

    # Lagged prices
    df["price_lag_24"] = df["prices"].shift(24)
    df["price_lag_168"] = df["prices"].shift(168)

    # Rolling stats
    df["price_roll_mean_24"] = df["prices"].shift(1).rolling(24).mean()
    df["price_roll_std_24"] = df["prices"].shift(1).rolling(24).std()
    df["price_roll_mean_168"] = df["prices"].shift(1).rolling(168).mean()
    # IMPORTANT: shift(1) needed to prevent look-ahead bias
    # Since without this, it includes its own value
    # hour 1 include hour 1's own price! but we don't know yet at prediction time
    # Drop rows where any feature or target is NaN
    df = df.dropna(subset=FEATURE_COLS + ["prices"])

    return df


def run():
    df = pd.read_parquet(CLEAN_PARQUET)
    df = build_features(df)
    print(f"Features built — shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    return df


if __name__ == "__main__":
    run()
