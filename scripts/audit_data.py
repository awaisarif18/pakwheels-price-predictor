"""Generate the first offline audit and a pending identity review worksheet."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from pilot.audit import audit_csv, render_report, seed_identity_review
from pilot.paths import BASELINE_DIR, REPORT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=BASELINE_DIR / "pakwheels_raw.csv")
    parser.add_argument("--clean", type=Path, default=BASELINE_DIR / "pakwheels_clean.csv")
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    try:
        raw = audit_csv(args.raw)
        clean = audit_csv(args.clean)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Audit failed: {exc}\n")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "initial_audit.md"
    report_path.write_text(
        render_report(raw, clean, datetime.now(timezone.utc).isoformat()), encoding="utf-8",
    )
    review_path = args.output_dir / "identity_review.csv"
    created = seed_identity_review(raw, review_path)
    print(f"Raw: {raw.row_count} rows; clean: {clean.row_count} rows")
    print(f"Report: {report_path.resolve()}")
    status = "created" if created else "preserved existing file"
    print(f"Review worksheet: {status} at {review_path.resolve()}")
    if not created:
        print("For a different dataset, choose another --output-dir to create its review worksheet.")
    print("Source verification and training eligibility remain pending.")


if __name__ == "__main__":
    main()
