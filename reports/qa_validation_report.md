# Data Quality Assurance Report
**Target Source:** `data/clean.parquet`

---

### ✅ Temporal Structure QA
* **Recorded Rows:** 17521
* **Expected Rows:** 17521
* **Index Uniqueness:** True
* **Stale/Flatline Data:** 0 consecutive 5-hour price freezes detected.

### ✅ Solar Boundary QA
* **Nighttime Irradiance Signatures:** 104 occurrences out of 4381 night hours.
* **Mean System Load Contribution:** 0.0136%
* *Note: Minor single-digit MW values during peak summer hours reflect expected model/twilight noise.*

### ❌ Price & Bound Sanity QA
* **Unexpected Physical Negative Values:** `{'residual_load_fc': 206}`
* **Regulatory Pricing Violations:** 0 breaches detected (Limits: €-500 to €4000).

### ⚠️ Missing Value (NaN) Audit
* **Total Isolated Missing Cells:** 14
* **Consecutive Missing Blocks (4+ Hours):**
  * No multi-hour dead zones detected.
