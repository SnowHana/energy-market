import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    CLEAN_PARQUET,
    HOUR_PER_DAY,
    SECONDS_PER_HOUR,
    EUROPEAN_MARKET_CAP_LIMIT,
    EUROPEAN_MARKET_FLOOR_LIMIT,
)
import pandas as pd


def time_qa(df) -> str:
    time_interval = (
        df.index[-1].tz_convert("UTC") - df.index[0].tz_convert("UTC")
    ).total_seconds() / SECONDS_PER_HOUR
    expected_hours = time_interval + 1

    is_unique = df.index.is_unique
    status_symbol = "✅" if (df.shape[0] == expected_hours and is_unique) else "❌"

    is_price_same = df["prices"].diff() == 0
    flatline_rows = df[is_price_same.rolling(window=4).sum() == 4].index

    return f"""### {status_symbol} Temporal Structure QA
* **Recorded Rows:** {df.shape[0]}
* **Expected Rows:** {expected_hours:.0f}
* **Index Uniqueness:** {is_unique}
* **Stale/Flatline Data:** {len(flatline_rows)} consecutive 5-hour price freezes detected.
"""


def solar_qa(df) -> str:
    is_night = (df.index.hour > 22) | (df.index.hour <= 4)
    night_solar_df = df[is_night & (df["solar_fc"] > 0)]

    avg_load_contrib = 0.0
    if not night_solar_df.empty:
        avg_load_contrib = 100 * (
            (night_solar_df["solar_fc"] / night_solar_df["load_fc"]).mean()
        )

    status_symbol = "✅" if avg_load_contrib < 0.1 else "⚠️"

    return f"""### {status_symbol} Solar Boundary QA
* **Nighttime Irradiance Signatures:** {night_solar_df.shape[0]} occurrences out of {df[is_night].shape[0]} night hours.
* **Mean System Load Contribution:** {avg_load_contrib:.4f}%
* *Note: Minor single-digit MW values during peak summer hours reflect expected model/twilight noise.*
"""


def price_qa(df) -> str:
    # Drop columns that are legally allowed to be negative for the non-negativity boundary check
    physical_cols = df.drop(columns=["prices", "net_position"], errors="ignore")
    negative_count = (physical_cols < 0).sum()
    columns_with_negatives = negative_count[negative_count > 0]

    neg_report = (
        "None" if columns_with_negatives.empty else columns_with_negatives.to_dict()
    )

    off_limits = df[
        (df["prices"] < EUROPEAN_MARKET_FLOOR_LIMIT)
        | (df["prices"] > EUROPEAN_MARKET_CAP_LIMIT)
    ].shape[0]
    status_symbol = "✅" if (columns_with_negatives.empty and off_limits == 0) else "❌"

    return f"""### {status_symbol} Price & Bound Sanity QA
* **Unexpected Physical Negative Values:** `{neg_report}`
* **Regulatory Pricing Violations:** {off_limits} breaches detected (Limits: €{EUROPEAN_MARKET_FLOOR_LIMIT} to €{EUROPEAN_MARKET_CAP_LIMIT}).
"""


def nan_qa(df) -> str:
    total_nan_cells = df.isnull().sum().sum()

    block_report = []
    for col in df.columns:
        consecutive_nans = df[df[col].isnull().rolling(window=4).sum() == 4].shape[0]
        if consecutive_nans > 0:
            block_report.append(
                f"  * `{col}`: {consecutive_nans} hours trapped in a 4+ hr gap"
            )

    nan_blocks_str = (
        "\n".join(block_report)
        if block_report
        else "  * No multi-hour dead zones detected."
    )
    status_symbol = "✅" if total_nan_cells == 0 else "⚠️"

    return f"""### {status_symbol} Missing Value (NaN) Audit
* **Total Isolated Missing Cells:** {total_nan_cells}
* **Consecutive Missing Blocks (4+ Hours):**
{nan_blocks_str}
"""


def run():
    df = pd.read_parquet(CLEAN_PARQUET)
    df = df.resample("h").mean()

    # Generate Report Sections
    report_header = f"# Data Quality Assurance Report\n**Target Source:** `{CLEAN_PARQUET}`\n\n---\n"
    t_sec = time_qa(df)
    s_sec = solar_qa(df)
    p_sec = price_qa(df)
    n_sec = nan_qa(df)

    # Combine into a single comprehensive Markdown string
    full_report = "\n".join([report_header, t_sec, s_sec, p_sec, n_sec])

    # Print directly to stdout for immediate review
    print(full_report)

    # Optional: Write it cleanly to an Obsidian-ready markdown file in your study repo
    report_path = Path(__file__).parent.parent / "reports" / "qa_validation_report.md"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(full_report)


if __name__ == "__main__":
    run()
