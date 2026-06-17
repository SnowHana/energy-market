import os
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from entsoe import EntsoePandasClient
from dotenv import load_dotenv

from backups.config import EIC, TIMEZONE, START_DATE, END_DATE, CLEAN_PARQUET, DATA_DIR

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def get_client():
    token = os.getenv("ENTSOE_API_TOKEN")
    if not token:
        raise EnvironmentError("ENTSOE_API_TOKEN not set in .env")
    return EntsoePandasClient(api_key=token)


def fetch_data():
    client = get_client()
    start = pd.Timestamp(START_DATE, tz=TIMEZONE)
    end = pd.Timestamp(END_DATE, tz=TIMEZONE)

    log.info(f"Pulling DE_LU data: {start.date()} -> {end.date()}")

    log.info("Fetching day-ahead prices...")
    prices = client.query_day_ahead_prices(EIC, start=start, end=end)

    log.info("Fetching load forecast...")
    load_fc = client.query_load_forecast(EIC, start=start, end=end)

    log.info("Fetching wind forecast...")
    wind_fc = client.query_wind_and_solar_forecast(
        EIC, start=start, end=end, psr_type="B19"
    )

    log.info("Fetching solar forecast...")
    solar_fc = client.query_wind_and_solar_forecast(
        EIC, start=start, end=end, psr_type="B16"
    )

    log.info("Fetching actual load...")
    actual_load = client.query_load(EIC, start=start, end=end)

    # Actual Generation to evaluate model
    log.info("Fetching actual generation (year by year)...")
    gen_chunks = []
    for year in range(start.year, end.year + 1):
        y_start = max(start, pd.Timestamp(f"{year}-01-01", tz=TIMEZONE))
        y_end = min(end, pd.Timestamp(f"{year}-12-31 23:59", tz=TIMEZONE))
        try:
            chunk = client.query_generation(EIC, start=y_start, end=y_end)
            if isinstance(chunk, pd.DataFrame):
                chunk = chunk.sum(axis=1)
            gen_chunks.append(chunk)
            log.info(f"  actual_gen {year} ok")
        except Exception as e:
            log.warning(f"  actual_gen {year} failed ({e}) — skipping")
    actual_gen = pd.concat(gen_chunks) if gen_chunks else None

    def to_series(x):
        if isinstance(x, pd.DataFrame):
            if x.shape[1] == 1:
                return x.iloc[:, 0]
            return x.sum(axis=1)
        return x

    prices = to_series(prices)
    load_fc = to_series(load_fc)
    wind_fc = to_series(wind_fc)
    solar_fc = to_series(solar_fc)
    actual_load = to_series(actual_load)

    df = pd.DataFrame(
        {
            "prices": prices,
            "load_fc": load_fc,
            "wind_fc": wind_fc,
            "solar_fc": solar_fc,
            "actual_load": actual_load,
        }
    )

    if actual_gen is not None:
        df["actual_gen"] = actual_gen
    # Data is given in every 15min, resample hourly
    df = df.resample("h").mean()
    # load created by non-renewables
    df["residual_load_fc"] = df["load_fc"] - df["wind_fc"] - df["solar_fc"]

    return df


def save_clean(df):
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    df.to_parquet(CLEAN_PARQUET)
    log.info(f"Saved {CLEAN_PARQUET}  shape={df.shape}")


def run():
    df = fetch_data()
    save_clean(df)
    return df


if __name__ == "__main__":
    run()
