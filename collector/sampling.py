"""Validate collection budgets and source searches before any request occurs."""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SearchSpec:
    name: str
    url_template: str
    expected_make: str | None
    expected_model: str | None
    target_complete_rows: int
    max_detail_requests: int
    max_pages: int
    start_page: int = 1

    def matches(self, row: dict) -> bool:
        if self.expected_make is None:
            return True
        return all(
            isinstance(row.get(field), str)
            and " ".join(row[field].split()).casefold() == expected.casefold()
            for field, expected in [("make", self.expected_make), ("model", self.expected_model)]
        )


def _positive_integer(value, label: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def load_plan(path: Path) -> tuple[SearchSpec, ...]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or type(data.get("plan_version")) is not int or data.get("plan_version") != 1:
        raise ValueError("Unsupported sampling plan version")
    searches = data.get("searches")
    if not isinstance(searches, list) or not searches:
        raise ValueError("The sampling plan needs at least one search")
    specs, names = [], set()
    for item in searches:
        if not isinstance(item, dict):
            raise ValueError("Each search must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in names:
            raise ValueError("Search names must be unique lowercase identifiers")
        names.add(name)
        template = item.get("url_template")
        if not isinstance(template, str) or template.count("{page}") != 1:
            raise ValueError(f"{name}: URL needs one {{page}} placeholder")
        try:
            parsed = urlsplit(template.format(page=1))
            port = parsed.port
        except (ValueError, KeyError, IndexError) as exc:
            raise ValueError(f"{name}: invalid URL template") from exc
        if parsed.scheme != "https" or parsed.hostname != "www.pakwheels.com" or not parsed.path.startswith("/used-cars/") or parsed.username or parsed.password or port not in (None, 443) or parsed.fragment:
            raise ValueError(f"{name}: URL must be an HTTPS PakWheels used-car search")
        make, model = item.get("expected_make"), item.get("expected_model")
        if (make is None) != (model is None) or any(value is not None and (not isinstance(value, str) or not value.strip()) for value in [make, model]):
            raise ValueError(f"{name}: supply both expected make and model, or neither")
        specs.append(SearchSpec(
            name, template, make.strip() if make else None, model.strip() if model else None,
            _positive_integer(item.get("target_complete_rows"), "target_complete_rows"),
            _positive_integer(item.get("max_detail_requests"), "max_detail_requests"),
            _positive_integer(item.get("max_pages"), "max_pages"),
            _positive_integer(item.get("start_page", 1), "start_page"),
        ))
    return tuple(specs)


def plan_definition(specs: tuple[SearchSpec, ...]) -> list[dict]:
    return [asdict(spec) for spec in specs]
