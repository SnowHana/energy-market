"""
run.py — full pipeline orchestrator.
Usage:  python run.py
Order:  ingest → qa → features+validate → curve → llm_note
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def main():
    # Step 1 — pull raw data from ENTSO-E and save clean.parquet
    log.info("=== Step 1/5  Ingest ===")
    from src.ingest import run as ingest_run
    ingest_run()

    # Step 2 — QA checks → outputs/qa_report.md
    log.info("=== Step 2/5  QA ===")
    from src.qa import run as qa_run
    qa_run()

    # Step 3 — feature engineering + walk-forward validation → metrics.json + figures
    log.info("=== Step 3/5  Validate ===")
    from src.validate import run as validate_run
    validate_run()

    # Step 4 — prompt-curve translation → curve_signal.md
    log.info("=== Step 4/5  Curve ===")
    from src.curve import run as curve_run
    curve_run()

    # Step 5 — LLM trader note → llm_logs.jsonl + trader_note_example.md
    log.info("=== Step 5/5  LLM Note ===")
    from src.llm_note import run as llm_run
    llm_run()

    log.info("Pipeline complete. Outputs in outputs/")


if __name__ == "__main__":
    main()
