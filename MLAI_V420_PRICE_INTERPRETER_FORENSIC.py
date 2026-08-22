"""
MLAI V4.2.0 — PRICE INTERPRETER + FORENSIC EVALUATOR
=====================================================

Safe combined entry point for the XAU/USD 50-day dataset.

Default mode produces the causal, price-anchored English interpretation from
MLAI_V420_PRICE_INTERPRETER.py.  Optional --forensic mode runs the complete
walk-forward retrieval evaluation from
MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py first, using the same 50-day dataset,
then prints the English interpretation.

The original interpreter and forensic evaluator remain unchanged.

Examples:
    python MLAI_V420_PRICE_INTERPRETER_FORENSIC.py
    python MLAI_V420_PRICE_INTERPRETER_FORENSIC.py --index 35000 --horizon 8
    python MLAI_V420_PRICE_INTERPRETER_FORENSIC.py --forensic
    python MLAI_V420_PRICE_INTERPRETER_FORENSIC.py --forensic --json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import MLAI_V420_PRICE_INTERPRETER as interpreter
import MLAI_V420_RETRIEVAL_FORENSIC_REPAIR as forensic


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "market_data_50d.bin"
INTERPRETATION_REPORT = ROOT / "MLAI_V420_PRICE_INTERPRETATION_50D.md"
FORENSIC_REPORT = ROOT / "MLAI_V420_RETRIEVAL_FORENSIC_REPAIR_50D_REPORT.md"
FORENSIC_ARTIFACT = ROOT / "MLAI_V420_RETRIEVAL_FORENSIC_REPAIR_50D.bin"


def parse_wrapper_options() -> bool:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--forensic",
        action="store_true",
        help="Run the complete causal walk-forward forensic evaluation first.",
    )
    known, _ = parser.parse_known_args()
    return known.forensic


def configure_modules() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Required 50-day dataset is missing: {DATA_FILE}"
        )

    # The imported modules keep their original behavior; only this combined
    # entry point redirects them to the validated XAU/USD 50-day corpus.
    interpreter.DATA_FILE = DATA_FILE
    interpreter.REPORT_FILE = INTERPRETATION_REPORT
    forensic.DATA_FILE = str(DATA_FILE)
    forensic.REPORT_FILE = str(FORENSIC_REPORT)
    forensic.ARTIFACT_FILE = str(FORENSIC_ARTIFACT)


def main() -> None:
    forensic_mode = parse_wrapper_options()
    configure_modules()

    if forensic_mode:
        print("=" * 100)
        print("FORENSIC MODE: causal retrieval evaluation on XAU/USD 50-day data")
        print("=" * 100)
        forensic.main()
        print()
        print("=" * 100)
        print("PRICE INTERPRETATION: same XAU/USD 50-day data")
        print("=" * 100)

    # Let the existing interpreter own its documented options and rendering.
    # Remove only the wrapper flag before handing control to its argparse.
    sys.argv = [argument for argument in sys.argv if argument != "--forensic"]
    interpreter.main()


if __name__ == "__main__":
    main()