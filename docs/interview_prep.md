# Interview Prep — Cobblestone Case Study

These are the "why" answers behind every design decision. The writeup has the numbers;
this doc has what you say when they ask you to defend them live.

---

## Data & Features

**Q: Why Germany (DE_LU)?**
The brief specified it. DE_LU is the largest bidding zone in continental Europe, with the most
renewable penetration — meaning more price volatility and more interesting signal from residual load.

**Q: What is residual load and why is it your primary driver?**
Residual load = load_fc − wind_fc − solar_fc. It's the demand that renewables can't cover.
That gap has to be filled by gas and coal plants, which are expensive — so when residual load is
high, prices tend to go up, and when it's low (lots of wind/solar), prices fall or even go negative.
It's the cleanest single number connecting physical fundamentals to price.

**Q: Why did you use forecasts rather than actuals as features?**
Look-ahead bias. At noon on the day before (gate closure), you only know forecasts — the actual
load, wind and solar for tomorrow don't exist yet. If you train on actuals, your model would work
in backtest but fail completely in production because the inputs it expects don't exist.

**Q: What is look-ahead bias, concretely?**
It's when your model accidentally uses information from the future while training. Example: if you
include today's actual load as a feature but you're predicting today's price, you've cheated —
that number isn't available when you need to make the bid. The fix is to only use forecasts as
inputs.

**Q: Why shift(1) before rolling features?**
Without `shift(1)`, the rolling mean of the last 24 hours would include the current hour's own
price — meaning the feature for hour H would already "know" the price at hour H. That's look-ahead
bias at the feature level. Shifting by 1 first means the rolling window only looks at truly past
hours.

**Q: Why lagged prices at D-1 and D-7?**
D-1 (24h lag) captures the recent price level — yesterday's prices are usually a decent anchor for
today. D-7 (168h lag) captures the weekly seasonality — power markets have strong day-of-week patterns
(weekday vs weekend demand), so the same hour last week is a useful reference. The naive baseline is
literally just D-7, which shows how strong this signal is.

---

## Model

**Q: Why LightGBM over linear regression?**
Linear regression can't capture the interactions between features — for example, the effect of
residual load on price is different at peak hours vs overnight. LightGBM handles these interactions
naturally. It also handles the non-linear relationship between, say, very high residual load and
price spikes better than a linear model can. That said, linear regression is a valid simpler option
and I'd add it if I had more time.

**Q: Why one model for all 24 hours rather than 24 separate models?**
One model with hour-of-day as a feature shares information across hours — patterns learned at 18:00
can inform the 19:00 prediction. 24 separate models each train on 1/24 of the data and can't share
what they learn. For the data volumes here, the shared model works better. (If you had years of
very rich data and high-quality per-hour features, 24 models could make sense.)

**Q: Why fix the random seed?**
Reproducibility. Anyone running the pipeline should get exactly the same results. LightGBM has
randomness in how it builds trees — fixing the seed pins that.

---

## Validation

**Q: Why walk-forward, not random cross-validation?**
With time series, random CV mixes up the timeline — the model can train on data from October and
predict September. In production you never know the future, so this leaks future information into
training and makes your metrics look better than they really are. Walk-forward respects time:
you always train on the past and predict the future.

**Q: Why expanding window rather than sliding window?**
Expanding window means each retrain uses all available history — so the model gets better as more
data accumulates, which mirrors how you'd use it in production. Sliding window throws away older
data, which could be useful if the market regime changed a lot, but for 2 years of relatively
stable data, expanding is the right default.

**Q: Why MAE and RMSE, not MAPE?**
MAPE (Mean Absolute Percentage Error) divides by the actual price. German power prices go negative
(e.g. −30 €/MWh). You can't divide by a negative or zero number without getting nonsense. MAE and
RMSE don't have this problem and are the standard for power markets for this reason.

**Q: What is the skill score?**
Skill = 1 − MAE_model / MAE_naive. It measures how much better we are than just using last week's
price. A skill of 0 means we're no better than naive; 1 would be perfect; negative means we're
worse. Our 0.59 means we cut the naive error by 59%.

**Q: Where is the model weakest?**
The evening ramp (18–21h) and spike/negative-price hours. These are the hardest to predict — demand
spikes quickly in the evening, and extreme prices (>300 or negative) happen during weather or
demand events that aren't well-captured by the features we have.

---

## Curve & Signal

**Q: What is the difference between day-ahead and forward markets?**
Day-ahead (EPEX): you bid for tomorrow's hourly delivery. Price is set today for tomorrow.
Forward/futures (EEX): you agree today to buy/sell electricity at a fixed price for a future period
(next week, next month, next quarter). The "prompt curve" is the near-term end of this forward
market — front-week and front-month contracts.

**Q: Why use a trailing realized average as the curve reference instead of actual futures prices?**
Free forward prices aren't cleanly sourceable programmatically. We flagged this explicitly in the
report and stated it as a limitation. Energy-Charts (Fraunhofer ISE) provides free public Phelix
futures data that would replace this proxy in production. The trailing realized average is a
reasonable first-order proxy — the forward curve tends to track recent realized prices when no big
structural shift has happened.

**Q: What does conviction mean here, and why LOW = no-trade?**
Conviction = spread / MAE. MAE is our own typical forecast error. If the spread (forecast minus
reference) is smaller than our own average error, we can't tell whether the signal is real or just
noise from our own imprecision. So we refuse to trade — we don't pretend we have an edge we don't
have.

**Q: What does the backtest show?**
Over 10 test weeks, 3 had MEDIUM or HIGH conviction. All 3 were correct — 100% hit rate, +33.91
€/MWh average. That's a small sample and not statistically definitive, but it shows the conviction
filter is doing its job: staying out when the signal is weak and being right when it fires. In a
real trading context you'd want many more weeks before putting capital behind it.

**Q: What would invalidate a long signal?**
A material upward revision to the wind forecast. That would lower residual load, push prices down,
and make the "curve looks cheap" call wrong. Also: if realized day-ahead prices diverge from your
forecast by more than one MAE for two consecutive days, the model may be mis-calibrated to the
current regime (e.g. an unmodelled gas supply shock) and you'd stop out.

---

## LLM Component

**Q: Why use an LLM here?**
The signal numbers and tables already exist — the manual work is writing the morning narrative that
explains them to a trader. The LLM turns structured numbers into a readable note. The key is it
doesn't make any decisions; it just does the wording.

**Q: Why low temperature (0.2)?**
Higher temperature means more creative/random outputs. For a daily note that needs to accurately
reflect specific numbers, you want deterministic and factual, not creative. 0.2 keeps the output
stable and grounded.

**Q: What if the LLM makes something up?**
The prompt explicitly forbids inventing numbers. And we validate the output shape before saving —
if required fields are missing or the JSON is malformed, the code raises an error rather than
silently saving garbage. Every call is logged to `llm_logs.jsonl` so you can audit what the model
actually said.

---

## Things to be honest about

- The curve reference is a proxy, not real futures. We know this and said so.
- No gas, carbon or cross-border features — these would help especially on spike hours.
- 10-week backtest is too small to claim statistical edge. Don't oversell it.
- `actual_gen` is 50% complete due to API timeouts — it's eval-only so it doesn't affect the model,
  but it's a data quality gap worth mentioning.
- The model is a prototype. It would need more robust feature engineering, regime detection, and
  proper risk sizing before going anywhere near real capital.
