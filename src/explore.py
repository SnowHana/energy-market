from dotenv import load_dotenv
import pandas as pd
from entsoe import EntsoePandasClient
import os

load_dotenv()
client = EntsoePandasClient(api_key=os.getenv("ENTSOE_API_TOKEN"))

start = pd.Timestamp("2024-01-01", tz="Europe/Berlin")
end = pd.Timestamp("2024-01-03", tz="Europe/Berlin")

prices = client.query_day_ahead_prices("10Y1001A1001A82H", start=start, end=end)
print(type(prices))
print(prices.head(10))
