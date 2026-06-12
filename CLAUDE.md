# CLAUDE.md — Cobblestone Case Study: European Power Fair Value

> Project brief for Claude Code. Read this fully before writing code.
> Candidate: **Daniel Kim** · Email: `<your-email>`

## 1. Goal

Build a prototype that produces a **daily fair-value view for the German (DE_LU) day-ahead power market** and translates it into a **prompt-curve trading view**. This is a trading-relevant forecasting pipeline with one programmatic LLM component. Prioritize a clean, working, reproducible end-to-end pipeline over model sophistication.

## 2. Locked decisions (do not re-litigate)

- **Market / bidding zone:** Germany–Luxembourg (`DE_LU`, EIC `10Y1001A1001A82H`).
- **Forecast target (Option A):** next-day hourly day-ahead prices (24 values).
- **Data source:** ENTSO-E Transparency Platform (`entsoe-py`, token in env `ENTSOE_API_TOKEN`).
- **Fundamental drivers (≥2):** day-ahead total load forecast; day-ahead wind+solar generation forecast. Derive **residual load = load_fc − wind_fc − solar_fc** (primary signal).
- **Baseline model:** seasonal naive (price at same hour, D-7). Optionally a linear regression on residual load + calendar.
- **Improved model:** LightGBM, single model with hour-of-day as a feature.
- **Validation:** walk-forward (expanding window). Never random k-fold.
- **LLM component:** auto-generate a daily fair-value / trader note from the forecast + drivers + curve signal; log all prompts/outputs. LLM via `ANTHROPIC_API_KEY`.
- **Peak definition:** 08:00–20:00 local, Mon–Fri. **Baseload:** all 24h, all days.
- **History:** pull ~2 years of hourly data ending at the latest available date.

## 3. Non-negotiable guardrails (these are how candidates fail)

1. **No look-ahead bias.** At the D-1 ~12:00 gate closure you only know *forecasts*, not actuals. Model features MUST be limited to information available before gate closure: use ENTSO-E **day-ahead forecasts** for load and wind/solar. Actual load/generation may be ingested ONLY for evaluating forecast quality — never as model features.
2. **DST handling.** Use tz-aware `Europe/Berlin`. Spring/autumn transition days have 23/25 hours. Do not assume 24h/day. QA must check day length.
3. **Walk-forward validation only.** No shuffled/random CV (time leakage).
4. **No MAPE on prices.** Prices go negative. Use MAE and RMSE, plus skill score vs the naive baseline. Directional accuracy optional.
5. **Reproducibility.** Fix random seeds. Whole pipeline runs with a single command. No secrets in the repo.

## 4. Repository structure

```
power-fair-value/
├── README.md                # setup + one-command run instructions
├── CLAUDE.md                # this file
├── requirements.txt
├── .env.example             # ENTSOE_API_TOKEN=, ANTHROPIC_API_KEY=
├── .gitignore               # .env, data/, __pycache__
├── config.py                # zone, EIC, date range, peak hours, seeds
├── run.py                   # orchestrates the full pipeline end-to-end
├── src/
│   ├── ingest.py            # ENTSO-E pulls -> tidy hourly frames
│   ├── qa.py                # QA checks -> outputs/qa_report.md
│   ├── features.py          # residual load, calendar, lags, holidays
│   ├── models.py            # seasonal naive, linear, LightGBM
│   ├── validate.py          # walk-forward CV + metrics
│   ├── curve.py             # hourly -> baseload/peak; DA-to-curve signal
│   └── llm_note.py          # LLM commentary + prompt logging
├── data/                    # raw + clean (gitignored; keep a tiny sample)
└── outputs/
    ├── qa_report.md
    ├── metrics.json
    ├── submission.csv
    ├── llm_logs.jsonl
    ├── trader_note_example.md
    └── figures/
```

## 5. Tasks & acceptance criteria

### Task 1 — Data ingestion & QA (`src/ingest.py`, `src/qa.py`)
Pull for `DE_LU`, hourly, ~2 years:
- Day-ahead prices.
- Day-ahead total load forecast.
- Day-ahead wind & solar generation forecast (sum to a renewables-forecast series).
- (For evaluation only) actual total load and actual generation.

Align everything onto one tz-aware `Europe/Berlin` hourly index. Persist clean data to `data/clean.parquet`.

QA checks (write results to `outputs/qa_report.md`):
- missing/expected-vs-actual timestamps and gaps; duplicate timestamps;
- NaN counts per column; out-of-range / sanity bounds on price; flatline detection;
- DST day-length check (flag any non-24h day and confirm it is a real transition day);
- coverage table (start, end, % complete per series); document source URLs, ENTSO-E document codes, license, and pull date.

**Done when:** `clean.parquet` exists and `qa_report.md` shows each check with pass/flag status and a coverage table.

### Task 2 — Forecasting & validation (`src/features.py`, `src/models.py`, `src/validate.py`)
Features (all known before D-1 gate closure): day-ahead load forecast, wind+solar forecast, residual load; hour-of-day, day-of-week, month, German public-holiday flag; lagged price (D-1 same hour, D-7 same hour) and rolling stats. **No same-day actuals.**

Models:
- Baseline: seasonal naive (price[h, D-7]); optional linear regression.
- Improved: LightGBM with hour-of-day as a feature. Set seed. Report feature importance.

Validation: expanding-window walk-forward over a held-out test period (e.g., last ~8–12 weeks). For each model report **MAE, RMSE, and skill = 1 − MAE_model / MAE_naive**. Add a short error-analysis note (spikes, negative-price hours, evening ramp).

Outputs: `outputs/metrics.json`, a model-comparison table, figures (predicted vs actual; error distribution; feature importance) in `outputs/figures/`, and `outputs/submission.csv` with columns `id, y_pred` for the out-of-sample period.

**Done when:** improved model beats naive on MAE with a positive skill score, metrics + figures saved, `submission.csv` written.

### Task 3 — Prompt curve translation (`src/curve.py`)
Aggregate the hourly forecast into **baseload** (24h mean) and **peak** (Mon–Fri 08–20 mean) averages for the upcoming prompt period (front-week and/or front-month).

Build the DA-to-curve view: compare forecast average to a prompt-curve reference. Free forward prices are hard to source — use **recent realized baseload/peak as a documented proxy** for where the curve sits (state this assumption explicitly), or a settlement figure if available. If forecast > reference → cheap → long bias; if forecast < reference → short bias. Size conviction by the spread relative to the model's historical forecast error.

Write usage & invalidation guidance, e.g.: the view holds while the period's wind forecast stays within band X; a wind-forecast upward revision > Y flips residual load and invalidates a long; re-run daily; stop if realized DA diverges from forecast by > Z for 2 consecutive days.

**Done when:** a table maps forecast → baseload/peak → signal (long/short + conviction) → invalidation triggers, plus a short guidance paragraph.

### Task 4 — AI/LLM integration (`src/llm_note.py`)
Programmatic LLM component that reduces manual work: given the forecast vector, top drivers (residual load, notable spike hours), and the curve signal, generate a concise structured **daily fair-value / trader note**. Use low temperature; validate the output shape.

Log every call to `outputs/llm_logs.jsonl` with `{timestamp, model, prompt, response}`. Save one example to `outputs/trader_note_example.md`.

Optional stretch: ingest a few energy-news headlines and have the LLM extract structured catalysts `{event, zone, direction, confidence}` to flag risks to the forecast.

**Done when:** `llm_note.py` runs, `llm_logs.jsonl` contains real entries, an example note is saved, and the write-up explains the component's purpose.

## 6. Deliverables checklist
- [ ] `docs/writeup.md` (1–3 pages) with name + email, method, results, trading view, LLM purpose.
- [ ] Repo: pipeline code, `README.md`, `requirements.txt`.
- [ ] `outputs/qa_report.md`, figures/tables, `metrics.json`.
- [ ] AI component + `llm_logs.jsonl`.
- [ ] (Optional) `submission.csv` with `id, y_pred`.

## 7. Commands
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill ENTSOE_API_TOKEN and ANTHROPIC_API_KEY
python run.py                 # ingest -> qa -> features -> train -> validate -> curve -> llm note
```

## 8. Working style for Claude Code
- Build incrementally and run after each module; keep functions small and testable.
- Never hardcode secrets; read from env.
- When a modeling or trading choice has options, surface the trade-off in a comment instead of silently picking.
- Keep the deliverable text (README, write-up, trader note) in English.
