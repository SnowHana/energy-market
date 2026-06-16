import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from google import genai

from config import CLEAN_PARQUET, OUTPUTS_DIR
from src.curve import build_signal

load_dotenv()

MODEL = "gemini-2.5-flash"
# Fields we require back from the LLM — used to validate output shape.
REQUIRED_FIELDS = ["headline", "baseload_view", "peak_view", "key_drivers", "risks"]


def gather_inputs() -> dict:
    """Collect the curve signal + top fundamental drivers for the prompt."""
    df = pd.read_parquet(CLEAN_PARQUET)
    signal = build_signal(df)

    prompt_window = df.iloc[-(7 * 24):]
    avg_residual = round(prompt_window["residual_load_fc"].mean(), 0)
    spike = prompt_window["prices"].groupby(prompt_window.index.hour).mean().nlargest(3)
    spike_hours = [f"{h:02d}:00 (~{p:.0f} €/MWh)" for h, p in spike.items()]

    return {
        "signal": signal,
        "avg_residual_load_mw": avg_residual,
        "top_spike_hours": spike_hours,
    }


def build_prompt(inputs: dict) -> str:
    """Turn structured inputs into a deterministic, JSON-only prompt."""
    s = inputs["signal"]
    b, p = s["baseload"], s["peak"]

    return f"""You are a power trading analyst. Write a concise daily fair-value note for the
German (DE_LU) day-ahead market, for the front-week prompt period {s['period_start'][:10]} to {s['period_end'][:10]}.

DATA (do not invent numbers beyond these):
- Baseload: forecast {b['forecast']} €/MWh vs reference {b['reference']} €/MWh (spread {b['spread']:+}), signal {b['signal']}, conviction {b['conviction']}.
- Peak: forecast {p['forecast']} €/MWh vs reference {p['reference']} €/MWh (spread {p['spread']:+}), signal {p['signal']}, conviction {p['conviction']}.
- Model out-of-sample MAE: {s['model_mae']} €/MWh (edge below this is noise).
- Avg residual load over the week: {inputs['avg_residual_load_mw']:.0f} MW.
- Highest-price hours: {", ".join(inputs['top_spike_hours'])}.

Reference is a trailing-4-week realized-price proxy for the forward curve.

Respond with ONLY valid JSON (no markdown, no backticks) using exactly these keys:
{{
  "headline": "one-sentence summary of the view",
  "baseload_view": "1-2 sentences: direction, conviction, why",
  "peak_view": "1-2 sentences: direction, conviction, why",
  "key_drivers": ["short bullet", "short bullet"],
  "risks": ["what would invalidate this view", "..."]
}}"""


def call_llm(prompt: str) -> str:
    """Call Gemini at low temperature for deterministic, factual output."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"temperature": 0.2},
    )
    return response.text


def validate_note(raw: str) -> dict:
    """Parse JSON and confirm all required fields are present (output-shape check)."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()

    note = json.loads(text)  # raises if not valid JSON
    missing = [f for f in REQUIRED_FIELDS if f not in note]
    if missing:
        raise ValueError(f"LLM output missing required fields: {missing}")
    return note


def log_call(prompt: str, response: str) -> None:
    """Append the full call to outputs/llm_logs.jsonl."""
    Path(OUTPUTS_DIR).mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "prompt": prompt,
        "response": response,
    }
    with open(f"{OUTPUTS_DIR}/llm_logs.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def save_example(note: dict, signal: dict) -> None:
    """Render the validated note to a readable markdown example."""
    md = f"""# Daily Fair-Value Note — DE_LU Front-Week

**Period:** {signal['period_start'][:10]} → {signal['period_end'][:10]}
**Generated:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

> {note['headline']}

**Baseload:** {note['baseload_view']}

**Peak:** {note['peak_view']}

**Key drivers:**
{chr(10).join(f"- {d}" for d in note['key_drivers'])}

**Risks / invalidation:**
{chr(10).join(f"- {r}" for r in note['risks'])}
"""
    Path(f"{OUTPUTS_DIR}/trader_note_example.md").write_text(md)
    print(f"Saved {OUTPUTS_DIR}/trader_note_example.md")


def run():
    inputs = gather_inputs()
    prompt = build_prompt(inputs)

    raw = call_llm(prompt)
    log_call(prompt, raw)          # log every call, even before validation

    note = validate_note(raw)      # raises if shape is wrong
    save_example(note, inputs["signal"])

    print("\n--- Trader Note ---")
    print(note["headline"])
    return note


if __name__ == "__main__":
    run()
