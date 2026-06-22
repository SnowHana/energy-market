from datetime import datetime, timedelta

END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3)
ZONE = "DE_LU"
TIME_ZONE = "Europe/Berlin"
HOUR_PER_DAY = 24
SECONDS_PER_HOUR = 3600
PEAK_HOURS = list(range(8, 20))
PEAK_DAYS = list(range(0, 5))

CLEAN_CSV = "data/clean.csv"
CLEAN_PARQUET = "data/clean.parquet"
DATA_DIR = "data"
EUROPEAN_MARKET_FLOOR_LIMIT = -500
EUROPEAN_MARKET_CAP_LIMIT = 4000
