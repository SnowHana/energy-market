# European Power Fair Value — DE_LU Day-Ahead Forecast & Prompt-Curve View

**Candidate:** Daniel Kim · wujindaniel1011@gmail.com
**Market:** Germany–Luxembourg (`DE_LU`) · **Target:** next-day hourly day-ahead prices (Option A)

---

## 1. Overview

The pipeline forecasts tomorrow's 24 hourly day-ahead prices for Germany, then turns that forecast into
an actual trading view: a baseload/peak signal against the prompt curve, with a rule for how hard to lean
and when to stay out. A short daily trader note is generated on top via Google Gemini. Everything runs
from one command (`python run.py`): `ingest → qa → features → validate → curve → llm_note`.

The thing I cared most about wasn't squeezing the last bit of accuracy out of the model. It was making
sure the forecast (a) isn't cheating by using information I wouldn't have at trade time, and (b) actually
translates into a disciplined trade instead of just a number. More on that in Section 4.

## 2. Data & QA

### 2.1 Data

I pulled ~2 years of hourly history (2024-06 to 2026-06) from ENTSO-E via `entsoe-py`, put it on a
tz-aware `Europe/Berlin` index, and saved it to `data/clean.parquet` (17,521 rows).

- **Target:** day-ahead price
- **Features:** day-ahead forecasts for load, wind and solar
- **Evaluation only:** actual load and actual generation

The main driver is **residual load = load_fc − wind_fc − solar_fc** — the demand that wind and solar
can't cover, which then has to be met by gas and coal plants. Those are expensive, so high residual load
pushes price up and lots of renewables pushes it down (sometimes negative). It's the cleanest single link
between the physical grid and the price.

One thing I was strict about: the actual load/generation columns are used _only_ to score forecast
quality, never as model inputs. Using them as features would be look-ahead bias, since I wouldn't have
those numbers at the point I have to bid.

### 2.2 QA

QA checks live in `outputs/qa_report.md`: timestamp completeness (0 missing, 0 duplicates), NaN counts,
price sanity, flatline detection, DST day-length, and a per-series coverage table. A few things that
looked wrong but were actually real:

- 1,112 **negative-price** hours — normal for high-renewable Germany, not a data error.
- 16 spikes above 500 €/MWh — genuine scarcity events.
- A 23-hour and a 25-hour day — the daylight-saving switches, handled correctly by the tz-aware index.

`actual_gen` only comes back ~50% complete (the 2025 chunk kept timing out on the API). Since it's
evaluation-only and never feeds the model, the forecast isn't affected.

## 3. Forecasting & Validation

Features, all of which I'd actually know before the day:
the load/wind/solar forecasts,
residual load, calendar fields (hour, day-of-week, month, German holiday flag, peak flag), lagged prices
(yesterday and last week, same hour), and rolling price mean/std. The rolling features use `shift(1)`
before `.rolling()` so the current hour's price can't leak into its own feature.

Two models:

- a seasonal-naive baseline (just last week's price at the same hour) : This turned out to be a stronger model despite its simplicity, because weekly patterns do exist especially in energy consumption.
- LightGBM (one model with hour as a feature,
  fixed seed).

Validation is a 10-week expanding walk-forward: train up to a week, predict it, retrain,move on.

| Model          | MAE (€/MWh) | RMSE (€/MWh) | Skill    | Dir. acc. |
| -------------- | ----------- | ------------ | -------- | --------- |
| Seasonal naive | 40.42       | 64.71        | —        | 0.85      |
| **LightGBM**   | **16.66**   | **28.58**    | **0.59** | **0.90**  |

LightGBM cuts the naive error by 59% and gets the direction right 90% of the time.
The biggest features are lagged price, residual load and hour-of-day, which is what I'd expect.
Where it struggles is the evening ramp (18–21h) and the spike / negative hours — the handful of moments that drive most of the
total error.
Figures in `outputs/figures/`.

## 4. From forecast to trade

To get a trade I aggregate the hourly forecast into a **baseload**
(all-hours mean) and a **peak** (Mon–Fri 08–20 mean) for the front week, and compare it to where the curve is sitting.
I don't have clean forward prices, so I use the trailing 4-week realized average as a documented proxy (We can use Energy-Charts' free Phelix futures or EEX's paid API in production —
I confirmed with the team that a trailing proxy is acceptable as long as it's stated).

The rule: spread = forecast − reference. If my forecast is above where the market's been trading, the
curve looks cheap -> lean long; below → lean short. But the important bit is sizing: I only act if the
spread is bigger than the model's own typical error (MAE). If the edge is smaller than my own
imprecision, I genuinely can't tell signal from noise, so I don't trade.
I believe this becomes quite important when it comes to trading.

| Product  | Forecast | Reference | Spread | Signal | Conviction |
| -------- | -------- | --------- | ------ | ------ | ---------- |
| Baseload | 93.55    | 100.41    | −6.86  | SHORT  | LOW        |
| Peak     | 76.01    | 78.59     | −2.58  | SHORT  | LOW        |

This week both spreads sit inside the 16.66 €/MWh error, so the honest call is a mild short lean with no
real edge — stand aside.

**Does the rule actually make money?** To check, I backtested the signal across the same 10 test weeks:
each week, generate the signal as if live, then see what realized prices did. The discipline held up —
out of 10 weeks it only fired on 3 (the other 7 were too weak and got skipped), and all 3 were right:
100% hit rate, +33.91 €/MWh average, +101.73 €/MWh cumulative (`outputs/figures/backtest_pnl.png`).

I want to be straight that 3 trades is a tiny sample and I wouldn't put real size behind it on that
basis.
But it shows the mechanism doing exactly what it's designed to do: sit out when there's no edge,
and be right when it does commit.
Invalidation triggers (mainly an upward wind-forecast revision killing a
long, plus a 2-day stop-out) are in `outputs/curve_signal.md`.

## 5. LLM Integration

`src/llm_note.py` feeds the curve signal plus a couple of supporting numbers (avg residual load, top
spike hours) to Gemini at `temperature=0.2` and gets back a structured daily fair-value note as JSON. I
validate the JSON shape before saving, so a malformed response errors out instead of being saved quietly.
Every call is logged to `outputs/llm_logs.jsonl`; an example note is in `outputs/trader_note_example.md`.

The LLM only does the wording, not the decision — the prompt forbids it from inventing numbers, and the
conviction call comes from my own MAE, not the model's opinion. The point is just to kill the manual step
of writing up the morning narrative every day.

## 6. Limitations & Next Steps

The honest gaps: the curve reference is a realized-price proxy, not true forwards; there are no gas,
carbon or cross-border features (which is probably why the spike hours are the weakest); and the backtest
sample is small. If I took this further I'd swap in EEX settlement prices, add a spike-specific model or
quantile loss for the tail hours, and bring in cross-border flows.
