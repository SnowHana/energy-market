from datetime import datetime, timedelta

END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3)
ZONE = "DE_LU"
TIME_ZONE = "Europe/Berlin"
CLEAN_CSV = "data/clean.csv"
CLEAN_PARQUET = "data/clean.parquet"
DATA_DIR = "data"
