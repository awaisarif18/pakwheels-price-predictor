"""Persist collection accounting independently of vehicle extraction."""

import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


class RunLog:
    """Record each attempted request, including failed and interrupted requests."""

    def __init__(self, output_dir: Path, settings: dict):
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        self.path = output_dir / "runs" / f"{self.run_id}.json"
        self.started_clock = time.monotonic()
        self.data = {
            "run_id": self.run_id, "started_at": utc_now(), "status": "running",
            "settings": settings, "requests": [], "selections": [], "groups": {},
        }
        root = Path(__file__).resolve().parents[1]
        self.data["code_sha256"] = {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ["scraper.py", "collector/fields.py", "collector/sampling.py", "collector/runner.py", "collector/run_log.py"]
        }
        self.save()

    def save(self) -> None:
        write_json(self.path, self.data)

    def fetch(self, source, session, url: str, delay: float, kind: str, group: str) -> str:
        event = {"kind": kind, "group": group, "url": url, "started_at": utc_now(), "outcome": "started"}
        self.data["requests"].append(event)
        self.save()
        started_clock = time.monotonic()
        try:
            html = source.fetch_page(session, url, delay)
        except KeyboardInterrupt:
            event["outcome"] = "interrupted"
            raise
        except Exception as exc:
            event.update(outcome="restricted" if isinstance(exc, source.AccessRestricted) else "failed", error=str(exc))
            response = getattr(exc, "response", None)
            if response is not None:
                event["http_status"] = response.status_code
            raise
        else:
            event["outcome"] = "success"
            return html
        finally:
            event.update(finished_at=utc_now(), elapsed_seconds=round(time.monotonic() - started_clock, 3))
            self.save()

    def finish(self, status: str, reason: str | None = None) -> None:
        self.data.update(status=status, stop_reason=reason, finished_at=utc_now(), elapsed_seconds=round(time.monotonic() - self.started_clock, 3))
        self.data["request_counts"] = dict(Counter(event["kind"] for event in self.data["requests"]))
        self.data["request_outcomes"] = dict(Counter(event["outcome"] for event in self.data["requests"]))
        self.data["selection_outcomes"] = dict(Counter(event["outcome"] for event in self.data["selections"]))
        self.save()


def write_summary(output_dir: Path, manifest: dict, run: RunLog) -> None:
    counts = run.data["request_counts"]
    selections = run.data["selection_outcomes"]
    lines = [
        "# Collection batch summary", "", f"Latest run: `{run.run_id}`. Status: `{run.data['status']}`.",
        "", f"Stop reason: {run.data.get('stop_reason') or 'None'}.", "",
        f"This run attempted {counts.get('search', 0)} search requests and {counts.get('detail', 0)} detail requests.",
        f"Request outcomes: `{run.data['request_outcomes']}`.",
        f"New stored rows: {selections.get('new_complete', 0) + selections.get('new_incomplete', 0)}. Refreshed rows: {selections.get('refreshed_complete', 0) + selections.get('refreshed_incomplete', 0)}.",
        f"Skipped saved complete rows: {selections.get('already_complete', 0)}. Duplicate IDs considered: {selections.get('duplicate', 0)}.",
        f"Elapsed: {run.data['elapsed_seconds']} seconds.", "",
        f"Cumulative batch contains {manifest['total_rows']} rows, {manifest['complete_rows']} parser-complete rows, and {manifest['unique_listing_ids']} unique listing IDs.", "",
        "| Search group | Requested complete rows | Stored complete matches | Latest run detail attempts | End reason |",
        "|---|---:|---:|---:|---|",
    ]
    for spec in manifest["sampling_plan"]:
        state = run.data["groups"][spec["name"]]
        lines.append(f"| {spec['name']} | {spec['target_complete_rows']} | {manifest['group_complete_counts'][spec['name']]} | {state['detail_attempts']} | {state['end_reason']} |")
    lines.extend(["", "Counts are observed extraction outcomes, not training eligibility or independent vehicle groups. Rows with missing fields or a family mismatch remain in raw storage and the run log.", "", "Field availability across all stored rows:", "", "| Field | Non-empty rows |", "|---|---:|"])
    lines.extend(f"| {field} | {count}/{manifest['total_rows']} |" for field, count in manifest["field_non_null_counts"].items())
    lines.extend(["", "See `manifest.json` for dataset fingerprints and assignments, and `runs/` for request, failure, and selection details. Quotas are not guaranteed. Page ordering and featured advertisements can bias the sample. No date, city, or variant balance is claimed.", ""])
    (output_dir / "collection_summary.md").write_text("\n".join(lines), encoding="utf-8")
