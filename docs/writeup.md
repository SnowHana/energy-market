# European Power Fair Value — DE_LU Day-Ahead Forecast & Prompt-Curve View

**Candidate:** Daniel Kim
**Email:** wujindaniel1011@gmail.com
**Market:** Germany–Luxembourg (`DE_LU`, EIC `10Y1001A1001A82H`)
**Forecast target:** next-day hourly day-ahead prices (Option A)

---

## 1. Overview

This project builds a reproducible end-to-end pipeline that (a) forecasts hourly day-ahead
power prices for the German bidding zone, (b) translates that forecast into a tradable
prompt-curve view (baseload/peak, long/short, conviction), and (c) auto-generates a daily
trader note with a programmatic LLM component. The whole pipeline runs from one command.

Pipeline: `ingest → qa → features → models → validate → curve → llm_note`.

## 2. Data ingestion & QA

**Source:** ENTSO-E Transparency Platform via `entsoe-py`. ~2 years of hourly data
(2024-06 → 2026-06), aligned onto one tz-aware `Europe/Berlin` index and saved to
`data/clean.parquet` (17,521 rows).

**Series:** day-ahead price (target); day-ahead **forecasts** for total load, wind and solar
(features); actual load and actual generation (evaluation only — never used as features, to
avoid look-ahead bias). The primary fundamental signal is **residual load = load_fc −
wind_fc − solar_fc** (demand not covered by renewables, which must be met by dispatchable
fuel — the main price driver).

**QA checks** (`outputs/qa_report.md`): timestamp completeness (0 missing / 0 duplicate),
NaN counts, price sanity, flatline detection, DST day-length, and a per-series coverage
table. Notable findings, all real (not data errors): 1,112 negative-price hours (~6%, normal
for high-renewable Germany), 16 spikes >500 €/MWh, and correct 23h/25h DST transition days.
`actual_gen` is ~50% complete (a 2025 API timeout); it is evaluation-only so this does not
affect the model.

## 3. Forecasting & validation

**Features** (all known before the D-1 gate closure): load/wind/solar forecasts, residual
load; calendar (hour, day-of-week, month, German holiday flag, peak flag); lagged price
(D-1, D-7) and rolling price mean/std. Rolling features use `shift(1)` to exclude the current
hour and prevent look-ahead bias.

**Models:** seasonal-naive baseline (price at same hour D-7) vs **LightGBM** (single model,
hour-of-day as a feature, fixed seed).

**Validation:** expanding-window walk-forward over the last 10 weeks — train up to week _w_,
predict week _w_, expand, repeat (10 retrains). No random CV. Metrics are aggregated across
all out-of-sample weeks.

| Model | MAE (€/MWh) | RMSE (€/MWh) | Skill | Directional acc. |
|-------|-------------|--------------|-------|------------------|
| Seasonal naive | 40.42 | 64.71 | — | 0.85 |
| **LightGBM** | **16.66** | **28.58** | **0.59** | **0.90** |

LightGBM beats the naive baseline by **59%** on MAE and predicts price direction correctly
**90%** of the time. Feature importance is led by lagged price, residual load and hour-of-day.

**Error analysis:** errors concentrate in the evening ramp (hours 18–21) and in spike /
negative-price hours — a small fraction of observations that drive a large share of total
error. Figures in `outputs/figures/`: predicted-vs-actual, error distribution, feature
importance, MAE-by-hour.

## 4. Prompt-curve translation

The hourly forecast is aggregated to **baseload** (24h mean) and **peak** (Mon–Fri 08–20
mean) for the front-week prompt period. Because free forward/curve prices are not cleanly
sourceable, the curve reference is proxied by the **trailing 4-week realized** baseload/peak
(stated explicitly; in production one would use EEX Phelix futures settlements).

**Signal:** forecast − reference = spread. Forecast > reference → curve looks cheap → LONG;
forecast < reference → SHORT. **Conviction is sized by the spread relative to the model's own
out-of-sample MAE** (a signal-to-noise heuristic): a spread inside 1×MAE is within our own
forecast error and treated as no-trade. A z-score against RMSE is reported alongside.

Latest run (front-week):

| Product | Forecast | Reference | Spread | Signal | Conviction |
|---------|----------|-----------|--------|--------|------------|
| Baseload | 93.55 | 100.41 | −6.86 | SHORT | LOW |
| Peak | 76.01 | 78.59 | −2.58 | SHORT | LOW |

Both spreads sit well inside the 16.66 €/MWh MAE, so the honest read is **no strong edge** this
week. **Invalidation:** re-run daily; a material upward wind-forecast revision lowers residual
load and invalidates a long; stop out if realized DA diverges from forecast by >~1×MAE for two
consecutive days. Full guidance in `outputs/curve_signal.md`.

## 5. AI/LLM integration

`src/llm_note.py` feeds the curve signal plus top drivers (avg residual load, top spike hours)
to an LLM (Gemini, `temperature=0.2`) and gets back a structured **daily fair-value note** as
JSON. The output shape is **validated** (required fields enforced) before saving; every call is
logged to `outputs/llm_logs.jsonl` as `{timestamp, model, prompt, response}`, and one rendered
example is saved to `outputs/trader_note_example.md`.

**Purpose:** it removes the manual step of writing the morning narrative — turning structured
numbers into a ready-to-send note — while staying grounded (the prompt forbids inventing
numbers, and conviction language is driven by our own error metric, not the model's imagination).

## 6. Reproducibility & limitations

One command (`python run.py`) runs the full pipeline; seeds are fixed and no secrets are in the
repo (`.env` only). **Limitations / next steps:** no gas/carbon or cross-border features (would
help the price ceiling and spikes); the curve reference is a realized-price proxy, not true
forwards; spike hours remain the largest error source and could be targeted with a dedicated
spike model or quantile loss.
