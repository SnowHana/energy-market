import os
import sys

sys.path.insert(0, "/Users/nautilus/cobblestone_study")

import pandas as pd
import holidays
import numpy as np
from config import DATA_DIR, CLEAN_PARQUET, PEAK_HOURS, PEAK_DAYS

FEATURE_COLS = [
    "load_fc",
    "wind_fc",
    "solar_fc",
    "residual_load_fc",
    "price_lag_24",
    "price_lag_168",
    "price_roll_mean_24",
    "price_roll_std_24",
    "price_roll_mean_168",
    "price_roll_std_168",
    "is_holiday",
    "is_peak",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "renewable_penetration_ratio",
    "residual_ramp_stress",
]


def build_design_matrix(df):

    df["hour"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month

    df["price_lag_24"] = df.shift(24)["prices"]
    df["price_lag_168"] = df.shift(168)["prices"]

    df["price_roll_mean_24"] = df["prices"].shift(1).rolling(window=24).mean()
    df["price_roll_std_24"] = df["prices"].shift(1).rolling(window=24).std()
    df["price_roll_mean_168"] = df["prices"].shift(1).rolling(window=24 * 7).mean()
    df["price_roll_std_168"] = df["prices"].shift(1).rolling(window=24 * 7).std()

    df["is_peak"] = df.index.hour.isin(PEAK_HOURS) & df.index.dayofweek.isin(PEAK_DAYS)
    de_holidays = holidays.Germany()
    df["is_holiday"] = (
        pd.Series(df.index.date, index=df.index)
        .map(lambda d: d in de_holidays)
        .astype(int)
    )

    # Turn date time into cts object so that
    # 23:00 PM and 0:00 AM are detected to be cts, instead of separate

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["day_of_week_sin"] = np.sin(2 * np.pi * df["day_of_week"] / (7))
    df["day_of_week_cos"] = np.cos(2 * np.pi * df["day_of_week"] / (7))

    df["residual_load_fc"] = df["load_fc"] - df["wind_fc"] - df["solar_fc"]
    # renewable penetration ratio : (renewable) / (total)
    df["renewable_penetration_ratio"] = (df["wind_fc"] + df["solar_fc"]) / df["load_fc"]
    # residual ramp stress: How much residual load spikes
    df["residual_ramp_stress"] = df["residual_load_fc"].diff()

    df = df.dropna(subset=FEATURE_COLS + ["prices"])
    return df


# df = pd.read_parquet("/Users/nautilus/cobblestone_study/data/clean.parquet")


def run():
    df = pd.read_parquet(CLEAN_PARQUET)
    design_df = build_design_matrix(df)
    print(design_df)
    return design_df


if __name__ == "__main__":
    run()
