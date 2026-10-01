"""Project paths shared by offline pilot commands."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "current"
BASELINE_DIR = PROJECT_ROOT / "data" / "raw" / "baseline_2026-10-01"
REPORT_DIR = PROJECT_ROOT / "reports" / "pilot"
