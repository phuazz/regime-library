#!/usr/bin/env python3
"""
compile.py - regime-library compiler

Reads every YAML under indicators/, validates the minimum field set,
computes summary statistics (per-asset composite scores, status counts,
category coverage), and writes two outputs next to itself:

    regime-library.json   Flattened payload for downstream consumers
                          such as EDD and PCC to read.
    dashboard.html        Self-contained single-file dashboard with the
                          payload embedded. Open directly in a browser,
                          no server required.

Usage
-----
    python regime-library/compile.py

The compiler is deliberately thin. All rendering logic lives in
template.html. To iterate on the dashboard, edit template.html and rerun
the compiler. To iterate on the data model, add or edit YAML files in
indicators/ and rerun. New categories, new consumers, and new indicator
fields are discovered automatically; the dashboard and JSON both extend
without code changes.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required.  Install with: pip install pyyaml")

ROOT = Path(__file__).resolve().parent
INDICATOR_DIR = ROOT / "indicators"
TEMPLATE = ROOT / "template.html"
OUT_HTML = ROOT / "index.html"
OUT_JSON = ROOT / "regime-library.json"

REQUIRED_FIELDS = (
    "id",
    "name",
    "category",
    "current_state",
    "direction",
    "horizon",
    "confidence",
)
VALID_STATUS = {"on", "off", "unknown"}
VALID_DIRECTION = {"bullish", "bearish", "neutral"}
CONFIDENCE_WEIGHT = {"high": 2.0, "medium": 1.0, "low": 0.5}
DIRECTION_SIGN = {"bullish": 1, "bearish": -1, "neutral": 0}


def load_indicators() -> tuple[list[dict], list[str]]:
    """Read every YAML under indicators/ and validate the minimum shape."""
    records: list[dict] = []
    errors: list[str] = []
    for path in sorted(INDICATOR_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            errors.append(f"{path.name}: YAML parse error: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path.name}: top-level node is not a mapping")
            continue
        missing = [k for k in REQUIRED_FIELDS if k not in data]
        if missing:
            errors.append(f"{path.name}: missing required fields {missing}")
            continue
        status = (data.get("current_state") or {}).get("status", "unknown")
        if status not in VALID_STATUS:
            errors.append(f"{path.name}: invalid status {status!r}")
            continue
        if data["direction"] not in VALID_DIRECTION:
            errors.append(f"{path.name}: invalid direction {data['direction']!r}")
            continue
        # Filename must match id so the library stays self-consistent.
        expected_slug = path.stem
        if data["id"] != expected_slug:
            errors.append(
                f"{path.name}: id {data['id']!r} does not match filename"
            )
            continue
        records.append(data)
    return records, errors


def summarise(records: list[dict]) -> dict:
    """Compute the aggregates shown on the dashboard snapshot panel."""
    by_category: dict[str, dict[str, int]] = {}
    by_status = {"on": 0, "off": 0, "unknown": 0}
    bullish_on = bearish_on = 0
    per_asset: dict[str, dict] = {}

    for r in records:
        cat = r["category"]
        status = r["current_state"]["status"]
        direction = r["direction"]
        confidence = r.get("confidence", "medium")

        by_category.setdefault(cat, {"on": 0, "off": 0, "unknown": 0})
        by_category[cat][status] = by_category[cat].get(status, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

        if status == "on":
            if direction == "bullish":
                bullish_on += 1
            elif direction == "bearish":
                bearish_on += 1

            weight = CONFIDENCE_WEIGHT.get(confidence, 1.0)
            sign = DIRECTION_SIGN.get(direction, 0)
            for asset in r.get("target_assets") or []:
                slot = per_asset.setdefault(
                    asset,
                    {
                        "score": 0.0,
                        "n_bullish": 0,
                        "n_bearish": 0,
                        "categories": set(),
                    },
                )
                slot["score"] += sign * weight
                slot["categories"].add(cat)
                if direction == "bullish":
                    slot["n_bullish"] += 1
                elif direction == "bearish":
                    slot["n_bearish"] += 1

    # JSON-friendly cleanup.
    for asset, v in per_asset.items():
        v["categories"] = sorted(v["categories"])
        v["score"] = round(v["score"], 2)

    return {
        "total": len(records),
        "by_category": by_category,
        "by_status": by_status,
        "bullish_on": bullish_on,
        "bearish_on": bearish_on,
        "net_bullish_on": bullish_on - bearish_on,
        "per_asset": per_asset,
    }


def embed_in_template(payload: dict) -> str:
    """Replace the DATA placeholder in template.html with embedded JSON."""
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE}")
    html = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, indent=None, default=str, ensure_ascii=False)
    # Replace the /*__DATA__*/ null /*__ENDDATA__*/ sentinel.
    marker_open = "/*__DATA__*/"
    marker_close = "/*__ENDDATA__*/"
    if marker_open not in html or marker_close not in html:
        raise RuntimeError("Template is missing DATA sentinels.")
    start = html.index(marker_open) + len(marker_open)
    end = html.index(marker_close)
    return html[:start] + " " + blob + " " + html[end:]


def main() -> int:
    if not INDICATOR_DIR.exists():
        sys.exit(f"indicators/ directory not found at {INDICATOR_DIR}")

    records, errors = load_indicators()

    if errors:
        print("Validation issues:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        if not records:
            sys.exit("No valid indicators loaded. Nothing to write.")

    summary = summarise(records)
    payload = {
        "generated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "indicators": records,
        "summary": summary,
    }

    OUT_JSON.write_text(
        json.dumps(payload, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )
    OUT_HTML.write_text(embed_in_template(payload), encoding="utf-8")

    print(f"Loaded {len(records)} indicator(s) across "
          f"{len(summary['by_category'])} categor(ies).")
    print(f"  On: {summary['by_status']['on']}  "
          f"Off: {summary['by_status']['off']}  "
          f"Unknown: {summary['by_status']['unknown']}")
    print(f"  Net bullish (on): {summary['net_bullish_on']:+d}")
    print()
    print(f"Wrote {OUT_JSON.relative_to(ROOT.parent)}")
    print(f"Wrote {OUT_HTML.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
