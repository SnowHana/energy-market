import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from config import END_DATE, START_DATE, ZONE, TIME_ZONE, CLEAN_CSV, DATA_DIR
from entsoe import EntsoePandasClient
import pandas as pd

load_dotenv()


# try:
def get_client():
    token = os.getenv("ENTSOE_API_TOKEN")
    if not token:
        raise EnvironmentError("ENTSOE_API_TOKEN not set in .env")
    return EntsoePandasClient(api_key=token)


def fetch_data():
    client = get_client()
    start_date = pd.Timestamp(START_DATE, tz=TIME_ZONE)
    end_date = pd.Timestamp(END_DATE, tz=TIME_ZONE)

    day_ahead_prices = client.query_day_ahead_prices(
        country_code=ZONE, start=start_date, end=end_date
    )

    net_position = client.query_net_position(
        country_code=ZONE, start=start_date, end=end_date, dayahead=True
    )

    load = client.query_load_forecast(country_code=ZONE, start=start_date, end=end_date)

    wind_forecast = client.query_wind_and_solar_forecast(
        country_code=ZONE, start=start_date, end=end_date, psr_type="B19"
    )

    solar_forecast = client.query_wind_and_solar_forecast(
        country_code=ZONE, start=start_date, end=end_date, psr_type="B16"
    )

    # Single-column DataFrame into a pandas series
    df = pd.DataFrame(
        {
            "day_ahead_prices": day_ahead_prices,
            "net_position": net_position,
            "load_forecast": load.squeeze(),
            "solar_forecast": solar_forecast.squeeze(),
            "wind_forecast": wind_forecast.squeeze(),
        }
    )

    df = df.resample("h").mean()

    df["residual_load_forecast"] = (
        df["load_forecast"] - df["wind_forecast"] - df["solar_forecast"]
    )

    return df


def save_clean(df):
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_CSV)


def run():
    df = fetch_data()
    save_clean(df)
    return df


if __name__ == "__main__":
    run()
