# Cobblestone Case Study — TODO

Candidate: Daniel Kim · wujindaniel1011@gmail.com
Market: DE_LU (Germany–Luxembourg)

---

## ✅ Done

- [x] Project structure, config.py, requirements.txt, venv
- [x] `ingest.py` — pulls 2yr DE_LU data from ENTSO-E → data/clean.parquet
- [x] `qa.py` — QA checks → outputs/qa_report.md (timestamps, NaN, price sanity, DST, coverage)
- [x] `features.py` — calendar, holiday, lags (24h/168h), rolling stats, residual load
- [x] `models.py` — seasonal naive baseline + LightGBM
- [x] `validate.py` — metrics (MAE, RMSE, skill, directional acc) + figures + submission.csv

---

## 🔴 CRITICAL FIX (do first)

- [ ] **`validate.py` is NOT real walk-forward.** Currently a single static train/test split.
      The brief lists walk-forward as a non-negotiable guardrail ("how candidates fail").
      → Rewrite to expanding-window: train→predict block 1, expand→predict block 2, ... loop.
      → Retrain LightGBM each step. Accumulate predictions across all test blocks.
      → This is the #1 thing a reviewer will check.

---

## ✅ Task 3 — Prompt Curve Translation (`curve.py`) — DONE

- [x] Forecast front-week (last 7 days held out), aggregate → baseload + peak
- [x] Reference proxy: trailing 4-week realized baseload/peak (documented assumption)
- [x] Signal: forecast vs reference → LONG/SHORT; conviction = spread / MAE (signal-to-noise)
- [x] z-score (spread / RMSE) reported as context stat
- [x] Invalidation guidance + usage paragraph → outputs/curve_signal.md

## 🟡 Task 4 — LLM Integration (`llm_note.py`) — NOT STARTED

- [ ] Feed forecast vector + top drivers + curve signal → Claude → structured trader note
- [ ] Low temperature, validate output shape
- [ ] Log every call to outputs/llm_logs.jsonl {timestamp, model, prompt, response}
- [ ] Save one example to outputs/trader_note_example.md
- [ ] (stretch) news-headline → structured catalysts {event, zone, direction, confidence}

## 🟡 Orchestration & Docs — NOT STARTED

- [ ] `run.py` — wire ingest → qa → features → validate → curve → llm note (one command)
- [ ] `README.md` — setup + one-command run instructions
- [ ] `docs/writeup.md` (1–3 pages) — name+email, method, results, **trading view**, LLM purpose
- [ ] Keep a tiny data sample (clean.parquet is gitignored)

---

## Interview-prep reminders (personal)

- [ ] Re-derive reasoning of each file OUT LOUD (the _why_, not the syntax)
- [ ] Self-test: rewrite features.py from blank — can I explain every feature + look-ahead bias?
- [ ] Be ready to modify live: add a feature, change peak hours, justify LightGBM vs linear
- [ ] Trading one-liner: "the trade is the SPREAD vs the curve, conviction sized by my own error"

---

Emailing them: yes, but be strategic
Email is good — it signals engagement. But ask sharp questions, not ones the brief already answers. Good ones:

"For the curve reference, is a recent-realized-price proxy acceptable, or do you expect a settlement/forward source?" (shows you understand the data-sourcing problem)
"Should the LLM note be deterministic/validated-shape, or are you also interested in the news-catalyst stretch goal?"
Don't ask "which market?" or "what metrics?" — those are in the brief and it signals you didn't read closely.

The honest answer on "is understanding enough?"
No — and I want to be straight with you because this is your career, not just a submission.

Understanding what we did is necessary but not sufficient. Here's the risk: if you submit this and pass to a technical interview, they will ask you to modify something live — "add a feature," "why LightGBM not linear," "walk me through how you'd handle a price spike," "change the peak definition." If your understanding is "I watched it get built," you'll freeze. If it's "I know why each piece exists and could rebuild the skeleton slowly on my own," you'll be fine.

A fair test for yourself, before submitting: close this chat and try to rewrite features.py from a blank file. You'll get stuck on pandas syntax (.shift(), .rolling()) — that's completely fine, everyone googles that. But you should be able to explain, without help: what features you're building, why each one, and why .shift(1) before rolling (look-ahead bias). If you can narrate the why fluently and only need to look up syntax, you're at junior-DS level. That's the real bar — juniors aren't expected to have pandas memorized; they're expected to understand the reasoning.

The fact that you keep asking "what does this do and why" instead of just pasting — that's exactly the right instinct. Keep doing that. By the time we finish Tasks 3 and 4, do one pass where you re-derive the reasoning of each file out loud.
