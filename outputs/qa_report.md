# QA Report — DE_LU Day-Ahead Power Data

**Pull date:** 2026-06-16
**Source:** ENTSO-E Transparency Platform
**Zone:** DE_LU (EIC: 10Y1001A1001A82H)
**Period:** 2024-06-16 → 2026-06-16

## 1. Timestamp Completeness
- Expected hours: 17521
- Actual hours: 17521
- Missing hours: 0 
- Extra hours: 0
- Duplicate timestamps: 0

## 2. NaN Counts
|                  |   missing_count |   missing_pct |
|:-----------------|----------------:|--------------:|
| prices           |               1 |          0.01 |
| load_fc          |               2 |          0.01 |
| wind_fc          |               3 |          0.02 |
| solar_fc         |               3 |          0.02 |
| actual_load      |               1 |          0.01 |
| actual_gen       |               1 |          0.01 |
| residual_load_fc |               3 |          0.02 |

## 3. Price Sanity
- Min: -499.00 €/MWh
- Max: 936.28 €/MWh
- Mean: 90.54 €/MWh
- Negative prices: 1127 hours
- Extreme spikes (>500 €/MWh): 16 hours
- Flatlines (5h+): 0

## 4. DST Day-Length Check
|            |   0 |
|:-----------|----:|
| 2024-10-27 |  25 |
| 2025-03-30 |  23 |
| 2025-10-26 |  25 |
| 2026-03-29 |  23 |
| 2026-06-16 |   1 |

## 5. Coverage Table
|                  | start                     | end                       |   total_rows |   non_null |   pct_complete |
|:-----------------|:--------------------------|:--------------------------|-------------:|-----------:|---------------:|
| prices           | 2024-06-16 00:00:00+02:00 | 2026-06-16 00:00:00+02:00 |        17521 |      17520 |          99.99 |
| load_fc          | 2024-06-16 00:00:00+02:00 | 2026-06-15 23:00:00+02:00 |        17521 |      17519 |          99.99 |
| wind_fc          | 2024-06-16 00:00:00+02:00 | 2026-06-15 23:00:00+02:00 |        17521 |      17518 |          99.98 |
| solar_fc         | 2024-06-16 00:00:00+02:00 | 2026-06-15 23:00:00+02:00 |        17521 |      17518 |          99.98 |
| actual_load      | 2024-06-16 00:00:00+02:00 | 2026-06-15 23:00:00+02:00 |        17521 |      17520 |          99.99 |
| actual_gen       | 2024-06-16 00:00:00+02:00 | 2026-06-15 23:00:00+02:00 |        17521 |      17520 |          99.99 |
| residual_load_fc | 2024-06-16 00:00:00+02:00 | 2026-06-15 23:00:00+02:00 |        17521 |      17518 |          99.98 |

## 6. Notes
- `actual_gen` is 50% complete — 2025 data timed out during API pull (504 error).
  This column is used for evaluation only, never as a model feature, so this does not affect forecast quality.
- Negative prices (1127 hours, 6.4%) are valid
- Extreme spikes (16 hours >500 €/MWh) are real market events, not data errors.
- DST transition days correctly show 23h/25h — Europe/Berlin timezone handled correctly.
