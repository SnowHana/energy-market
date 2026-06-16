# Prompt-Curve Trading View — DE_LU Front-Week

**Prompt period:** 2026-06-09 00:00:00+02:00 → 2026-06-15 23:00:00+02:00
**Model out-of-sample error:** MAE 16.72 €/MWh · RMSE 28.72 €/MWh

## Signal Table

| Product  | Forecast | Reference | Spread | Signal | Conviction | z (vs RMSE) |
|----------|----------|-----------|--------|--------|------------|-------------|
| Baseload | 74.2 | 98.88 | -24.68 | SHORT | MEDIUM | -0.86 |
| Peak     | 72.29 | 76.97 | -4.68 | SHORT | LOW | -0.16 |

## How to read this
- **Forecast** = LightGBM average over the front-week prompt period.
- **Reference** = trailing 4-week realized average, used as a **documented proxy**
  for where the forward curve sits. Free forward/EEX settlement data is not cleanly sourceable;
  in production you would reference EEX Phelix futures settlements instead.
- **Spread** = forecast − reference. Positive → forecast sees the period richer than recent
  levels → curve looks **cheap** → **LONG** bias. Negative → **SHORT** bias.
- **Conviction** sizes the edge against the model's own error (signal-to-noise): spread < 1×MAE
  = LOW (inside our noise → treat as no-trade), 1–2× = MEDIUM, >2× = HIGH. The **z** column is the
  equivalent in std of forecast error (RMSE) — a spread inside ~1 std is not a tradeable edge.
