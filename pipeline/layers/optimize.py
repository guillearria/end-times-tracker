"""Layer 4 — Optimize. Presentation + ranking over the whole corpus.

Computes sort_keys deterministically. On the live path Sonnet tightens prose, but claims are
restored from a pre-run snapshot and a guard asserts the claims fingerprint is byte-identical
before and after — Optimize can never alter a claim or a source_url.
"""

from __future__ import annotations

import json
from datetime import date

from .. import client, config, models, schema


def compute_sort_keys(record: dict, kind: str = "threat") -> dict:
    if kind == "event":
        return _event_sort_keys(record)
    a = record.get("assessment", {})
    sr = config.SEVERITY_RANK.get(a.get("severity"), 1)
    pr = config.PROBABILITY_RANK.get(a.get("probability", {}).get("estimate"), 1)
    # Severity dominates; probability breaks ties.
    return {"severity_rank": sr, "probability_rank": pr, "composite": float(sr * 10 + pr)}


def _recency_rank(occurrence_date: str) -> int:
    """Ordinal day number of the occurrence date; larger = more recent.

    Uses date.toordinal so the rank is stable (independent of 'today') — a rebuild
    next month yields the same file, yet newer events always outrank older ones.
    """
    try:
        return date.fromisoformat((occurrence_date or "")[:10]).toordinal()
    except ValueError:
        return 0


def _impact_rank(impact: dict) -> int:
    """1-4 from casualty/displacement bands; the larger signal wins (see config)."""
    rank = 1
    deaths = impact.get("deaths")
    displaced = impact.get("displaced")
    for value, bands in ((deaths, config.EVENT_IMPACT_DEATHS),
                         (displaced, config.EVENT_IMPACT_DISPLACED)):
        if isinstance(value, (int, float)):
            for threshold, r in bands:
                if value >= threshold:
                    rank = max(rank, r)
                    break
    return rank


def _event_sort_keys(record: dict) -> dict:
    ev = record.get("event", {})
    recency = _recency_rank(ev.get("occurrence_date", ""))
    impact = _impact_rank(ev.get("impact", {}))
    # Recency dominates (day-ordinal * 10 dwarfs the 1-4 impact); impact breaks same-day ties.
    return {"recency_rank": recency, "impact_rank": impact, "composite": float(recency * 10 + impact)}


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
