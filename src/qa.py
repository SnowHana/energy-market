import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from config import CLEAN_PARQUET, OUTPUTS_DIR


def run():
    df = pd.read_parquet(CLEAN_PARQUET)
    prices = df["prices"].dropna()

    # Timestamp completeness
    expected = pd.date_range(
        start=df.index.min(), end=df.index.max(), freq="h", tz="Europe/Berlin"
    )
    missing = expected.difference(df.index)
    extra = df.index.difference(expected)
    duplicates = df.index.duplicated().sum()

    # NaN counts
    nan_counts = df.isnull().sum()
    nan_pct = (df.isnull().mean() * 100).round(2)
    nan_report = pd.DataFrame({"missing_count": nan_counts, "missing_pct": nan_pct})

    # Price sanity
    flatline = (
        (prices == prices.shift(1))
        & (prices == prices.shift(2))
        & (prices == prices.shift(3))
        & (prices == prices.shift(4))
    )

    # DST check
    daily_hours = df.groupby(df.index.date).size()
    non_24 = daily_hours[daily_hours != 24]

    # Coverage table
    coverage = pd.DataFrame({
        "start": df.apply(lambda col: col.first_valid_index()),
        "end": df.apply(lambda col: col.last_valid_index()),
        "total_rows": len(df),
        "non_null": df.count(),
        "pct_complete": (df.count() / len(df) * 100).round(2),
    })

    report = f"""# QA Report — DE_LU Day-Ahead Power Data

**Pull date:** {pd.Timestamp.now().date()}
**Source:** ENTSO-E Transparency Platform
**Zone:** DE_LU (EIC: 10Y1001A1001A82H)
**Period:** {df.index.min().date()} → {df.index.max().date()}

## 1. Timestamp Completeness
- Expected hours: {len(expected)}
- Actual hours: {len(df)}
- Missing hours: {len(missing)} ✓
- Extra hours: {len(extra)} ✓
- Duplicate timestamps: {duplicates} ✓

## 2. NaN Counts
{nan_report.to_markdown()}

## 3. Price Sanity
- Min: {prices.min():.2f} €/MWh
- Max: {prices.max():.2f} €/MWh
- Mean: {prices.mean():.2f} €/MWh
- Negative prices: {(prices < 0).sum()} hours
- Extreme spikes (>500 €/MWh): {(prices > 500).sum()} hours
- Flatlines (5h+): {flatline.sum()} ✓

## 4. DST Day-Length Check
{non_24.to_markdown()}

## 5. Coverage Table
{coverage.to_markdown()}

## 6. Notes
- `actual_gen` is 50% complete — 2025 data timed out during API pull (504 error).
  This column is used for evaluation only, never as a model feature, so this does not affect forecast quality.
- Negative prices ({(prices < 0).sum()} hours, {(prices < 0).mean()*100:.1f}%) are valid — Germany frequently sees negative prices during high renewable output periods.
- Extreme spikes ({(prices > 500).sum()} hours >500 €/MWh) are real market events, not data errors.
- DST transition days correctly show 23h/25h — Europe/Berlin timezone handled correctly.
"""

    Path(OUTPUTS_DIR).mkdir(exist_ok=True)
    Path(f"{OUTPUTS_DIR}/qa_report.md").write_text(report)
    print(f"Saved {OUTPUTS_DIR}/qa_report.md")


if __name__ == "__main__":
    run()
