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

        Task: Forecast either next-day hourly prices (Option A, recommended) or front-week / front-month price averages (Option B).
        Deliverable: At least one baseline and one improved model with validation metrics.
    Prompt Curve Translation
        Task: Translate your forecast into a tradable DA-to-curve view.
        Deliverable: Short guidance on how the forecasted values would be used or invalidated.
    AI/LLM Integration
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
