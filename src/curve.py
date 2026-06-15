import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import pandas as pd

from config import CLEAN_PARQUET, OUTPUTS_DIR, PEAK_HOURS, PEAK_WEEKDAYS
from src.features import build_features, FEATURE_COLS
from src.models import train_lgbm, predict_lgbm

# Prompt period = front-week (7 days). Reference proxy = trailing 4 weeks.
PROMPT_HOURS = 7 * 24
REFERENCE_WEEKS = 4


def baseload_peak(prices: pd.Series) -> tuple[float, float]:
    """Baseload = mean of all hours. Peak = mean of Mon-Fri 08-20 only."""
    baseload = prices.mean()
    is_peak = (
        prices.index.hour.isin(PEAK_HOURS)
        & prices.index.dayofweek.isin(PEAK_WEEKDAYS)
    )
    peak = prices[is_peak].mean()
    return round(baseload, 2), round(peak, 2)


def signal_to_noise(spread: float, mae: float) -> str:
    """Conviction label: spread relative to the model's own forecast error (MAE)."""
    ratio = abs(spread) / mae
    if ratio < 1.0:
        return "LOW"      # spread is inside our own error → noise
    elif ratio < 2.0:
        return "MEDIUM"
    else:
        return "HIGH"


def zscore(spread: float, rmse: float) -> float:
    """Spread expressed as multiples of forecast-error std (RMSE) — context stat."""
    return round(spread / rmse, 2)


def build_signal(df: pd.DataFrame) -> dict:
    df = build_features(df)

    # Split: last 7 days = prompt period to forecast; everything before = train
    forecast_df = df.iloc[-PROMPT_HOURS:]
    train_df = df.iloc[:-PROMPT_HOURS]

    # Train on history, forecast the prompt period
    model = train_lgbm(train_df[FEATURE_COLS], train_df["prices"])
    forecast = predict_lgbm(model, forecast_df[FEATURE_COLS])

    # Aggregate forecast → baseload / peak
    fc_base, fc_peak = baseload_peak(forecast)

    # Reference proxy: realized baseload/peak over the 4 weeks before the prompt period
    ref_window = train_df["prices"].iloc[-(REFERENCE_WEEKS * PROMPT_HOURS):]
    ref_base, ref_peak = baseload_peak(ref_window)

    # Model error from validation, for conviction sizing
    with open(f"{OUTPUTS_DIR}/metrics.json") as f:
        metrics = json.load(f)
    mae = metrics["lgbm"]["mae"]
    rmse = metrics["lgbm"]["rmse"]

    base_spread = round(fc_base - ref_base, 2)
    peak_spread = round(fc_peak - ref_peak, 2)

    def leg(fc, ref, spread):
        return {
            "forecast": fc,
            "reference": ref,
            "spread": spread,
            "signal": "LONG" if spread > 0 else "SHORT",
            "conviction": signal_to_noise(spread, mae),
            "zscore": zscore(spread, rmse),
        }

    return {
        "period_start": str(forecast_df.index[0]),
        "period_end": str(forecast_df.index[-1]),
        "model_mae": mae,
        "model_rmse": rmse,
        "baseload": leg(fc_base, ref_base, base_spread),
        "peak": leg(fc_peak, ref_peak, peak_spread),
    }


def write_report(signal: dict) -> None:
    b = signal["baseload"]
    p = signal["peak"]

    report = f"""# Prompt-Curve Trading View — DE_LU Front-Week

**Prompt period:** {signal['period_start']} → {signal['period_end']}
**Model out-of-sample error:** MAE {signal['model_mae']} €/MWh · RMSE {signal['model_rmse']} €/MWh

## Signal Table

| Product  | Forecast | Reference | Spread | Signal | Conviction | z (vs RMSE) |
|----------|----------|-----------|--------|--------|------------|-------------|
| Baseload | {b['forecast']} | {b['reference']} | {b['spread']:+} | {b['signal']} | {b['conviction']} | {b['zscore']} |
| Peak     | {p['forecast']} | {p['reference']} | {p['spread']:+} | {p['signal']} | {p['conviction']} | {p['zscore']} |

## How to read this
- **Forecast** = LightGBM average over the front-week prompt period.
- **Reference** = trailing {REFERENCE_WEEKS}-week realized average, used as a **documented proxy**
  for where the forward curve sits. Free forward/EEX settlement data is not cleanly sourceable;
  in production you would reference EEX Phelix futures settlements instead.
- **Spread** = forecast − reference. Positive → forecast sees the period richer than recent
  levels → curve looks **cheap** → **LONG** bias. Negative → **SHORT** bias.
- **Conviction** sizes the edge against the model's own error (signal-to-noise): spread < 1×MAE
  = LOW (inside our noise → treat as no-trade), 1–2× = MEDIUM, >2× = HIGH. The **z** column is the
  equivalent in std of forecast error (RMSE) — a spread inside ~1 std is not a tradeable edge.

## Usage & invalidation guidance
- Re-run **daily** — both forecast and reference roll forward each day.
- The view holds while the period's **wind forecast** stays within its current band. A material
  **upward wind revision** lowers residual load, pushes prices down, and **invalidates a LONG**
  (and strengthens a SHORT); downward revisions do the reverse.
- **Stop out** if realized day-ahead diverges from the forecast by more than ~1×MAE
  ({signal['model_mae']} €/MWh) for **2 consecutive days** — the model is mis-calibrated to the
  current regime (e.g. an unmodelled fuel or outage shock).
- Treat **LOW** conviction as no-trade: the edge is inside the model's own error.
"""
    Path(OUTPUTS_DIR).mkdir(exist_ok=True)
    Path(f"{OUTPUTS_DIR}/curve_signal.md").write_text(report)
    print(f"Saved {OUTPUTS_DIR}/curve_signal.md")


def run():
    df = pd.read_parquet(CLEAN_PARQUET)
    signal = build_signal(df)

    print("\n--- Prompt-Curve Signal ---")
    for product in ("baseload", "peak"):
        s = signal[product]
        print(
            f"{product.capitalize():9} forecast {s['forecast']:>7} | "
            f"ref {s['reference']:>7} | spread {s['spread']:>+7} | "
            f"{s['signal']} ({s['conviction']}) | z={s['zscore']}"
        )

    write_report(signal)
    return signal


if __name__ == "__main__":
    run()
