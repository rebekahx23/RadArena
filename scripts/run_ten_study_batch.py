"""Paired ten-study run with strict Red validation and selectable model."""
import argparse
import os
from pathlib import Path

from radarena.batch import BASE, run_batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE)
    parser.add_argument("--model", choices=["gemma", "flash"], default="gemma")
    parser.add_argument("--max-cost", type=float, default=1)
    parser.add_argument("--structured-blue", action="store_true")
    parser.add_argument(
        "--allow-unvalidated-attacks",
        action="store_true",
        help="Legacy research mode; rejects no semantic family violations",
    )
    args = parser.parse_args()
    model = (
        "google/gemini-2.5-flash"
        if args.model == "flash"
        else "google/gemma-3-27b-it"
    )
    os.environ["RADARENA_TEXT_MODEL"] = model
    os.environ["RADARENA_VISION_MODEL"] = model
    result = run_batch(
        args.output,
        args.max_cost,
        not args.allow_unvalidated_attacks,
        args.structured_blue,
    )
    print({key: result[key] for key in ["complete", "counts", "accounted_cost_usd"]})


if __name__ == "__main__":
    main()
