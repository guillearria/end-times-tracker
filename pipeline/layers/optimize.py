"""Layer 4 — Optimize. Presentation + ranking over the whole corpus.

Computes sort_keys deterministically. On the live path Sonnet tightens prose, but claims are
restored from a pre-run snapshot and a guard asserts the claims fingerprint is byte-identical
before and after — Optimize can never alter a claim or a source_url.
"""

from __future__ import annotations

import json

from .. import client, config, models, schema
from ..curate import compute_sort_keys


def _live_prose(record: dict, *, client_obj) -> dict:
    resp = client.call_layer(
        client_obj,
        model=config.MODEL_OPTIMIZE,
        system=config.load_prompt("optimize"),
        user_content=json.dumps(record, ensure_ascii=False, indent=2),
        effort=config.EFFORT_OPTIMIZE,
        fmt=schema.output_format(),
    )
    out = client.first_json(resp)
    record["description"] = out.get("description", record.get("description", ""))
    oa = out.get("assessment", {})
    if isinstance(oa.get("summary"), str):
        record.setdefault("assessment", {})["summary"] = oa["summary"]
    return record


def run(records: list[dict], *, client_obj, run_id: str) -> list[dict]:
    dry = client.is_dry_run(client_obj)
    out: list[dict] = []
    for rec in records:
        before = models.claims_fingerprint(rec)
        claims_snapshot = json.loads(json.dumps(rec.get("claims", [])))
        if not dry:
            rec = _live_prose(rec, client_obj=client_obj)
        # Guard: Optimize may not touch claims. Restore, then assert no drift.
        rec["claims"] = claims_snapshot
        assert models.claims_fingerprint(rec) == before, "Optimize altered claims"
        rec["sort_keys"] = compute_sort_keys(rec)
        models.stamp_provenance(rec, layer="optimize", run_id=run_id)
        out.append(rec)
    return out
