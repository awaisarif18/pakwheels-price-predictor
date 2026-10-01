"""Sequential collection with bounded searches, round-robin sampling, and resume."""

import hashlib
import json
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from collector.run_log import RunLog, utc_now, write_json, write_summary
from collector.sampling import SearchSpec, plan_definition


@dataclass(frozen=True)
class CollectionSettings:
    searches: tuple[SearchSpec, ...]
    output_dir: Path
    max_detail_requests: int
    delay: float = 5
    contact: str = "your-email@example.com"
    refresh: bool = False
    cumulative_targets: bool = True
    single_url: str | None = None


def _present(value) -> bool:
    return value is not None and str(value).strip().casefold() not in {"", "nan", "<na>"}


def _counts(records: dict, assignments: dict, searches: tuple[SearchSpec, ...]) -> dict:
    return {
        spec.name: sum(
            row.get("parse_status") == "complete" and assignments.get(url) == spec.name and spec.matches(row)
            for url, row in records.items()
        )
        for spec in searches
    }


def run_collection(settings: CollectionSettings, source) -> dict:
    """Collect using the existing scraper functions supplied as a module.

    ``source`` supplies fetch/parse/discovery/storage functions and requests.
    The explicit dependency avoids circular imports and lets offline tests
    replace fetch_page while exercising the real parser, resume, and exports.
    A detail budget counts attempts, including failures, and excludes skips.
    """
    if settings.max_detail_requests < 1 or not math.isfinite(settings.delay) or settings.delay < 1:
        raise ValueError("Detail budget must be positive and delay must be finite and >= 1")
    output = settings.output_dir.resolve()
    if output == (source.PROJECT_DIR / "data" / "raw" / "baseline_2026-10-01").resolve():
        raise ValueError("The preserved baseline cannot be used as an output directory")
    definition = plan_definition(settings.searches)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "manifest_version": 1, "sampling_plan": definition, "runs": [], "group_assignments": {},
    }
    if manifest.get("sampling_plan") != definition:
        raise ValueError("This batch already uses a different sampling plan; choose a new output directory")
    records = source.load_existing(output)
    initial_urls = set(records)
    assignments = manifest["group_assignments"]
    for url, row in records.items():
        if url not in assignments:
            assignments[url] = next((spec.name for spec in settings.searches if spec.matches(row)), "unmatched")
    initial_counts = _counts(records, assignments, settings.searches)
    run = RunLog(output, {
        "max_detail_requests": settings.max_detail_requests, "delay_seconds": settings.delay,
        "refresh": settings.refresh, "cumulative_targets": settings.cumulative_targets,
        "sampling_plan": definition,
    })
    manifest["runs"].append({"run_id": run.run_id, "log": str(run.path.relative_to(output)), "status": "running"})
    states = {}
    for spec in settings.searches:
        states[spec.name] = {
            "queue": deque([settings.single_url] if settings.single_url else []),
            "next_page": spec.start_page, "pages_attempted": 0, "detail_attempts": 0,
            "completed_this_run": 0, "end_reason": None, "discovered_urls": 0,
        }
    seen_ids = set()
    saved_ids = {str(row.get("listing_id")): url for url, row in records.items() if _present(row.get("listing_id"))}
    detail_attempts = 0
    complete_observations = 0
    status, reason = "completed", None

    def checkpoint() -> None:
        manifest.update(
            updated_at=utc_now(), total_rows=len(records),
            complete_rows=sum(row.get("parse_status") == "complete" for row in records.values()),
            unique_listing_ids=len({str(row["listing_id"]) for row in records.values() if _present(row.get("listing_id"))}),
            group_complete_counts=_counts(records, assignments, settings.searches),
            field_non_null_counts={
                field: sum(_present(row.get(field)) for row in records.values())
                for field in ["make", "model", "variant", "year", "price_pkr", "mileage_km", "fuel", "transmission", "engine_cc", "listing_city", "assembly", "body_type", "registration_year", "listing_date"]
            },
        )
        run.data["groups"] = {name: {key: value for key, value in state.items() if key != "queue"} for name, state in states.items()}
        run.save()
        write_json(manifest_path, manifest)

    def selection(url: str, group: str, outcome: str, **extra) -> None:
        run.data["selections"].append({"url": url, "group": group, "outcome": outcome, **extra})

    checkpoint()
    session = source.requests.Session()
    session.headers.update({
        "User-Agent": f"CarPriceResearch/0.3 (contact: {settings.contact})",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        active = True
        while active and detail_attempts < settings.max_detail_requests:
            active = False
            for spec in settings.searches:
                state = states[spec.name]
                if state["end_reason"]:
                    continue
                fulfilled = (
                    _counts(records, assignments, settings.searches)[spec.name]
                    if settings.cumulative_targets and not settings.refresh
                    else state["completed_this_run"]
                )
                if fulfilled >= spec.target_complete_rows:
                    state["end_reason"] = "target_reached"
                    continue
                if state["detail_attempts"] >= spec.max_detail_requests:
                    state["end_reason"] = "group_detail_budget_reached"
                    continue
                if detail_attempts >= settings.max_detail_requests:
                    break
                active = True
                candidate = None
                while candidate is None and state["end_reason"] is None:
                    if not state["queue"]:
                        if settings.single_url or state["pages_attempted"] >= spec.max_pages:
                            state["end_reason"] = "pages_exhausted"
                            break
                        page = state["next_page"]
                        state["next_page"] += 1
                        state["pages_attempted"] += 1
                        url = spec.url_template.format(page=page)
                        print(f"[SEARCH {spec.name}] Page {page}: {url}", flush=True)
                        try:
                            html = run.fetch(source, session, url, settings.delay, "search", spec.name)
                        except source.AccessRestricted:
                            raise
                        except source.requests.RequestException:
                            state["end_reason"] = "search_request_failed"
                            break
                        links = source.listing_links(html)
                        state["discovered_urls"] += len(links)
                        if not links:
                            directory = output / "diagnostics"
                            directory.mkdir(parents=True, exist_ok=True)
                            (directory / f"{run.run_id}_{spec.name}_page_{page}.html").write_text(html, encoding="utf-8")
                            state["end_reason"] = "no_listing_links"
                            break
                        state["queue"].extend(links)
                    url = state["queue"].popleft()
                    listing_id = url.rstrip("/").rsplit("-", 1)[-1]
                    if listing_id in seen_ids:
                        selection(url, spec.name, "duplicate", listing_id=listing_id)
                        continue
                    seen_ids.add(listing_id)
                    existing_url = saved_ids.get(listing_id, url)
                    existing = records.get(existing_url)
                    if existing and existing.get("parse_status") == "complete" and not settings.refresh:
                        selection(url, spec.name, "already_complete", listing_id=listing_id)
                        continue
                    candidate = url, listing_id, existing_url
                if candidate is None:
                    checkpoint()
                    continue
                url, listing_id, existing_url = candidate
                detail_attempts += 1
                state["detail_attempts"] += 1
                print(f"[DETAIL {spec.name}] {detail_attempts}/{settings.max_detail_requests}: {url}", flush=True)
                try:
                    html = run.fetch(source, session, url, settings.delay, "detail", spec.name)
                except source.AccessRestricted:
                    raise
                except source.requests.RequestException:
                    selection(url, spec.name, "request_failed", listing_id=listing_id)
                    checkpoint()
                    continue
                row, preview = source.parse_car(html, url)
                if existing_url != url and existing_url in records:
                    del records[existing_url]
                    assignments.pop(existing_url, None)
                records[url] = row
                saved_ids[listing_id] = url
                matches = spec.matches(row)
                assignments[url] = spec.name if matches else "unmatched"
                complete = row["parse_status"] == "complete"
                if complete:
                    complete_observations += 1
                if complete and matches:
                    state["completed_this_run"] += 1
                outcome = ("refreshed" if existing_url in initial_urls else "new") + ("_complete" if complete else "_incomplete")
                evidence = {}
                sampled = int(hashlib.sha256(f"{run.run_id}:{listing_id}".encode()).hexdigest(), 16) % 10 == 0
                flagged = not complete or not matches or row.get("identity_status") != "extracted_pending_review" or row.get("registration_year_status") == "conflicting"
                if flagged or complete_observations <= 50 or sampled:
                    directory = output / "evidence"
                    directory.mkdir(parents=True, exist_ok=True)
                    html_path = directory / f"{run.run_id}_{listing_id}.html"
                    html_path.write_text(html, encoding="utf-8")
                    evidence = {"html_evidence": str(html_path.relative_to(output)), "html_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest()}
                    if not complete:
                        html_path.with_suffix(".txt").write_text(preview, encoding="utf-8")
                selection(url, spec.name, outcome, listing_id=listing_id, family_match=matches, missing_fields=row["missing_fields"], **evidence)
                total, complete_count = source.save_csv(records, output)
                checkpoint()
                print(f"[SAVED] {complete_count}/{total} complete; family match: {matches}", flush=True)
    except source.AccessRestricted as exc:
        status, reason = "restricted", str(exc)
        print(f"[STOP] {reason}", flush=True)
    except KeyboardInterrupt:
        status, reason = "interrupted", "Operator interrupted collection; saved rows can be resumed"
        print(f"[STOP] {reason}", flush=True)
    except Exception as exc:
        status, reason = "failed", str(exc)
        raise
    finally:
        session.close()
        for spec in settings.searches:
            state = states[spec.name]
            if not state["end_reason"]:
                fulfilled = _counts(records, assignments, settings.searches)[spec.name] if settings.cumulative_targets and not settings.refresh else state["completed_this_run"]
                state["end_reason"] = "target_reached" if fulfilled >= spec.target_complete_rows else ("run_detail_budget_reached" if status == "completed" else status)
        if status == "completed" and any(state["end_reason"] != "target_reached" for state in states.values()):
            status = "partial"
        source.save_csv(records, output)
        checkpoint()
        run.finish(status, reason)
        manifest["runs"][-1]["status"] = status
        manifest["runs"][-1]["complete_matches_this_run"] = sum(state["completed_this_run"] for state in states.values())
        manifest["initial_group_complete_counts"] = initial_counts
        manifest["file_sha256"] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in ["pakwheels_raw.csv", "pakwheels_clean.csv"]}
        write_json(manifest_path, manifest)
        write_summary(output, manifest, run)
        print(f"[DONE] {output}: {manifest['complete_rows']}/{manifest['total_rows']} complete", flush=True)
        print(f"[SUMMARY] {output / 'collection_summary.md'}", flush=True)
    return run.data
