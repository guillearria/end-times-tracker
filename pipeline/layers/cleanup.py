"""Layer 3 — Clean-up. Mechanical normalization only; no factual changes.

Python's `normalize` is the authority (stable claim sort, dedup, source-name normalization). On
the live path Haiku may polish prose, but only `description`/`summary` are adopted from it — every
factual field stays from the input record, so Clean-up cannot alter facts. Haiku omits adaptive
thinking via call_layer (Correction #1).
"""

from __future__ import annotations

import json

from .. import client, config, models, schema


def normalize(record: dict) -> dict:
    """Deterministic mechanical normalization. Mutates and returns the record."""
    record.setdefault("schema_version", models.SCHEMA_VERSION)
    record["name"] = record.get("name", "").strip()
    record["description"] = record.get("description", "").strip()

    a = record.get("assessment", {})
    if isinstance(a.get("summary"), str):
        a["summary"] = a["summary"].strip()
    if isinstance(a.get("timeframe"), str):
        a["timeframe"] = a["timeframe"].strip()

    seen: set[str] = set()
    claims: list[dict] = []
    for c in sorted(record.get("claims", []), key=lambda c: c.get("id", "")):
        c["text"] = c.get("text", "").strip()
        key = c["text"].lower()
        if key in seen:
            continue  # dedup identical claims
        seen.add(key)
        ok, label = config.allowlisted(c.get("source_url", "") or "")
        c["source_name"] = label if (ok and label) else c.get("source_name", "").strip()
        claims.append(c)
    record["claims"] = claims
    return record


def _live_prose(record: dict, *, client_obj) -> dict:
    resp = client.call_layer(
        client_obj,
        model=config.MODEL_CLEANUP,
        system=config.load_prompt("cleanup"),
        user_content=json.dumps(record, ensure_ascii=False, indent=2),
        fmt=schema.output_format(),
    )
    out = client.first_json(resp)
    # Adopt prose only; all factual fields remain from the input record.
    record["description"] = out.get("description", record.get("description", ""))
    oa = out.get("assessment", {})
    if isinstance(oa.get("summary"), str):
        record.setdefault("assessment", {})["summary"] = oa["summary"]
    return record


def run(record: dict, index: list[dict], *, client_obj, run_id: str) -> dict:
    # `index` is reserved for future cross-threat dedup; merges are out of MVP scope.
    if not client.is_dry_run(client_obj):
        record = _live_prose(record, client_obj=client_obj)
    record = normalize(record)
    models.stamp_provenance(record, layer="cleanup", run_id=run_id)
    return record
