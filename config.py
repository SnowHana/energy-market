from datetime import date, timedelta

ZONE = "DE_LU"
EIC = "10Y1001A1001A82H"
TIMEZONE = "Europe/Berlin"

END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=2 * 365)

PEAK_HOURS = list(range(8, 20))
PEAK_WEEKDAYS = list(range(0, 5))

TEST_WEEKS = 10
RANDOM_SEED = 40

LGBM_PARAMS = {
    "objective": "regression",
    "metric": "mae",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 63,
    "random_state": RANDOM_SEED,
    "verbose": -1,
}

DATA_DIR = "data"
OUTPUTS_DIR = "outputs"
CLEAN_PARQUET = "data/clean.parquet"

LOCAL_CSV = {
    "prices": "data/raw/da_prices.csv",
    "load_fc": "data/raw/load_forecast.csv",
    "wind_fc": "data/raw/wind_forecast.csv",
    "solar_fc": "data/raw/solar_forecast.csv",
    "actual_load": "data/raw/actual_load.csv",
    "actual_gen": "data/raw/actual_generation.csv",
}
