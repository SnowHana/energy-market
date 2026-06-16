# European Power Fair Value — DE_LU Day-Ahead Forecast

End-to-end forecasting pipeline for the German (DE_LU) day-ahead power market.  
Produces hourly price forecasts, a prompt-curve trading view (baseload/peak, long/short, conviction), and a daily LLM-generated trader note.

---

## Setup

**Requirements:** Python 3.10+

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env
# Then open .env and fill in:
#   ENTSOE_API_TOKEN=<your ENTSO-E token>
#   GEMINI_API_KEY=<your Google AI Studio key>
```

**Getting API keys:**

- ENTSO-E token: register at [transparency.entsoe.eu](https://transparency.entsoe.eu)
- Gemini key: [aistudio.google.com](https://aistudio.google.com)

---

## Run

```bash
python run.py
```

This runs the full pipeline in order:

| Step        | Module            | Output                                                               |
| ----------- | ----------------- | -------------------------------------------------------------------- |
| 1. Ingest   | `src/ingest.py`   | `data/clean.parquet`                                                 |
| 2. QA       | `src/qa.py`       | `outputs/qa_report.md`                                               |
| 3. Validate | `src/validate.py` | `outputs/metrics.json`, `outputs/submission.csv`, `outputs/figures/` |
| 4. Curve    | `src/curve.py`    | `outputs/curve_signal.md`                                            |
| 5. LLM Note | `src/llm_note.py` | `outputs/llm_logs.jsonl`, `outputs/trader_note_example.md`           |

---

## Project structure

```
cobblestone_study/
├── run.py                   # one-command pipeline execution
├── config.py                # all constants (zone, dates, paths, seeds)
├── requirements.txt
├── .env.example
├── src/
│   ├── ingest.py            # ENTSO-E API pulls → clean.parquet
│   ├── qa.py                # QA checks → qa_report.md
│   ├── features.py          # residual load, calendar, lags, rolling stats
│   ├── models.py            # seasonal naive + LightGBM
│   ├── validate.py          # expanding walk-forward CV + metrics + figures
│   ├── curve.py             # hourly forecast → baseload/peak signal
│   └── llm_note.py          # LLM daily trader note
├── docs/
│   ├── writeup.md           # 1–3 page method + results write-up
│   └── TODO.md
└── outputs/                 # generated files (gitignored)
```

---

## Key design decisions

- **No look-ahead bias:** model features use only ENTSO-E _forecasts_ (load, wind, solar), not actuals. Rolling features use `shift(1)` before `.rolling()`.
- **DST-safe:** all timestamps are tz-aware `Europe/Berlin`. Spring/autumn days with 23/25 hours are handled correctly.
- **Walk-forward validation:** 10 expanding-window weekly retrains — no random CV.
- **Conviction sizing:** spread / MAE. A spread inside 1×MAE is treated as noise (no-trade).
- **Reproducibility:** `RANDOM_SEED = 42` in `config.py`; no secrets in the repo.
