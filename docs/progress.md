# Case Study Theme

European Power Fair Value: Forecasting Day-Ahead and Translating to Prompt Curve Views

Task: Build a prototype producing a daily fair-value view for a European power market and show how it informs prompt curve positioning.

Requirements:

# Data Ingestion & QA

> Task: Collect publicly available data for one market (DE, FR, NL, GB)

We chose DE_LU(Germany-Luxembourg) energy market

- prices — the day-ahead auction price for each hour. Not the "actual" price of electricity on the day — it's the price agreed the day before for delivery tomorrow.

- load*fc — the forecast of how much electricity Germany will consume tomorrow. Not actual, it's a \_prediction* made before gate closure.

- wind*fc — the \_forecast* of how much wind power will be generated tomorrow. Again, a prediction, not actual.

- solar*fc — same, \_forecast* of solar generation tomorrow.

- actual*load — what demand \_actually* was after the fact. We only use this to evaluate our model quality, never as a model input (that would be look-ahead bias — you don't know actuals before the day happens).

- actual_gen — total actual generation from all sources (wind, solar, gas, coal, nuclear etc) combined, after the fact. Same — evaluation only.

- residual_load_fc — load_fc - wind_fc - solar_fc. This is "how much demand is left that renewables can't cover." Gas and coal plants fill this gap — and they're expensive, so high residual load → high prices. It's not exactly "non-renewable" — it's more precisely "demand that must be met by dispatchable plants" (gas, coal, nuclear).

> Deliverable: Dataset including hourly Day-Ahead prices + at least two fundamental drivers; document sources and implement QA checks.

Day-Ahead prices : day before, every trader _bids_ for _next day_

## Drviers

- `residual_loads` : loads - renewable_sources(`wind`, `solar`)
- `load` : total loads (demand forecast)

## QA Checks

- Timestamp Completeness : Expected vs actual hours, no gaps found
- Duplicate Timestamps : none found
- NaN counts per column : actual_gen 50% missing (2025 API timeout, it's for eval only)
- Price sanity: min -499 €/MWh, max 936 €/MWh, 1112 negative hours (valid), 16 spikes >500
- Flatline detection: none found
- DST day-length: 23h/25h days confirmed correct (Europe/Berlin timezone)
- Coverage table: all forecast columns >99.98% complete

# Forecasting & Validation

## Task: Forecast either next-day hourly prices (Option A, recommended) or front-week / front-month price averages (Option B).

Takes clean data, builds inputs model can learn from.
Engineering _signals_ helping model to understsand _patterns_.

- Calendar features
- Holiday flag
- Lagged Prices : price at same hour yesterday, last week etc
- Rollign stasts: 24h, 168h etc
- Residual load : already good to go

### build_features

- `datetime` object to `hour, dayofweek, month`
- Check `is_holiday` and `is_peak`
- Check `price_lag` : Prices before 24hr, and 1week
- Check `price_roll_mean` : Prices before 24hr

> No look ahead bias!
> Make sure to `.shift(1)` when finding `roll_mean` cuz otherwise, current price is included!

## Deliverable: At least one baseline and one improved model with validation metrics.

Part 2 — models.py
What: Two models that predict tomorrow's 24 hourly prices.

Baseline — Seasonal Naive:
Just says "tomorrow's price at hour H = last week's price at hour H". Super simple, no training needed. This is our benchmark to beat.

Improved — LightGBM:
A gradient boosting model (like a smarter random forest). Takes all the features from features.py and learns complex patterns. Single model with hour-of-day as a feature — so it learns one model for all 24 hours simultaneously.

Part 3 — validate.py
What: Tests how good our models actually are.

Walk-forward validation:
We simulate real trading conditions. Train on everything up to week X, predict week X+1, then expand the training window and repeat. Never use future data to train — that would be cheating.

Train: Jun 2024 → Sep 2026 → Predict: Oct 2026 week 1
Train: Jun 2024 → Oct 2026 week 1 → Predict: Oct 2026 week 2
...and so on for 10 weeks
Metrics:

MAE (Mean Absolute Error) — average €/MWh error. Lower is better.
RMSE (Root Mean Square Error) — penalises big errors more. Lower is better.
Skill score = 1 - MAE_model / MAE_naive. Positive = beats naive. 0 = same as naive. Negative = worse than naive.
Outputs:

outputs/metrics.json — all numbers
outputs/figures/ — predicted vs actual plot, error distribution, feature importance
outputs/submission.csv — your out-of-sample predictions

### Implementation

#### Metrics

- **MAE (Mean absolute error)** : Avg. of absolute diff btw predicted and actual : Cuz easy to interpret (on avg, we are off by $x$ distance)
- **RMSE (Root Mean Squared Error)** : Big mistakes get penalised more heavily. Catch models that are occasionally very wrong

- **MAPE (Mean Absolute Percentage Error)** : Is not good, because it divdides by actual price, but German one goes negative!

- **Skill Score** : https://en.wikipedia.org/wiki/Forecast_skill

https://www.amperon.co/blog/the-different-kinds-of-forecasting-metrics

https://medium.com/trusted-data-science-haleon/forecasting-navigating-metrics-validation-and-model-selection-881e8b7b76d2

# Prompt Curve Translation

Task: Translate your forecast into a tradable DA-to-curve view.
Deliverable: Short guidance on how the forecasted values would be used or invalidated.

---

- Curve = Forward Prices (Contracts where you agree today to buy/sell electricity at a _fixed price_ for a _future period_)
- Prompt Curve : nearest upcoming period (front-week = next week, front-month = next month)

- DA-to-curve view : DA (Day-Ahead), so have a forecast for tmr's hourly price, aggregate into a single number (baseload avg / peak avg) to compare it what the forward market is currently pricing that period at....

# AI/LLM Integration

Task: Implement one programmatic AI/LLM component to reduce manual work in your pipeline.
Deliverable: Working code calling the AI/LLM, logged prompts and outputs, and a brief explanation of its purpose.

Submission:

    Document: 1–3 pages (PDF or Markdown) with name and email.
    Repo or zipped folder including pipeline code, README, requirements, QA output, figures/tables, AI component.
    Optional: submission.csv with out-of-sample predictions (id, y_pred).

Evaluation:

    Dataset correctness and QA
    Forecasting rigor
    Trading relevance
    Engineering quality and reproducibility
    Programmatic AI/LLM use

Deadline: Please submit your case study within one week from today.
