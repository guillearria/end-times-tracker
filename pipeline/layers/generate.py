"""Layer 1 — Generate. Propose new/updated threats; every claim emitted is unverified.

Input is a compact slug index (not full records) so the model cannot anchor on stale claims.
"""

from __future__ import annotations

import json

from .. import client, config, models, schema


def _force_unverified(rec: dict) -> dict:
    """Generate has no web access — it may not assert verification or sources."""
    rec.setdefault("schema_version", models.SCHEMA_VERSION)
    for c in rec.get("claims", []):
        c["source_url"] = ""
        c["retrieved_date"] = ""
        c["verification_status"] = "unverified"
    rec["verification"] = {"status": "unverified", "confidence": "low",
                           "notes": rec.get("verification", {}).get("notes", "")}
    rec.setdefault("sort_keys", {"severity_rank": 1, "probability_rank": 1, "composite": 0.0})
    return rec


def _dry(index: list[dict]) -> list[dict]:
    """Deterministic proposals: one that will verify, one that will quarantine."""
    existing = {r["id"] for r in index}
    candidates = [
        {
            "id": "asteroid-impact",
            "name": "Large Asteroid Impact",
            "category": "cosmic",
            "description": "A kilometer-scale near-Earth object striking Earth would cause "
            "regional devastation and global climatic effects. Such impacts are rare and the "
            "known large near-Earth population is extensively catalogued and tracked.",
            "assessment": {
                "probability": {"window": "next-100-years", "estimate": "very-low",
                                "numeric_annual": None},
                "severity": "civilizational",
                "timeframe": "No known kilometer-scale object is on an impact trajectory this century.",
                "summary": "A rare but high-consequence impact; no catalogued large object currently "
                "threatens Earth.",
            },
            "claims": [{
                "id": "claim-1",
                "text": "NASA's CNEOS tracks near-Earth objects and reports no known asteroid "
                "poses a significant impact risk to Earth for the next century.",
                "source_name": "NASA CNEOS",
                "source_url": "", "retrieved_date": "", "verification_status": "unverified",
            }],
        },
        {
            "id": "rogue-ai",
            "name": "Loss of Control of Advanced AI",
            "category": "technological",
            "description": "The hypothesis that a highly capable AI system could act in ways its "
            "developers cannot control or correct. Quantified official estimates are scarce.",
            "assessment": {
                "probability": {"window": "next-100-years", "estimate": "low",
                                "numeric_annual": None},
                "severity": "civilizational",
                "timeframe": "Highly uncertain; no authoritative timeline exists.",
                "summary": "A debated, hard-to-quantify risk with few authoritative numeric estimates.",
            },
            "claims": [{
                "id": "claim-1",
                "text": "A loss-of-control scenario from advanced AI is estimated to carry a 10% "
                "chance this century.",
                "source_name": "Independent Analysis",
                "source_url": "", "retrieved_date": "", "verification_status": "unverified",
            }],
        },
    ]
    return [_force_unverified(c) for c in candidates if c["id"] not in existing]


def _live(index: list[dict], *, client_obj) -> list[dict]:
    system = config.load_prompt("generate")
    user = "Existing threats (compact index):\n" + json.dumps(index, ensure_ascii=False, indent=2)
    resp = client.call_layer(
        client_obj,
        model=config.MODEL_GENERATE,
        system=system,
        user_content=user,
        effort=config.EFFORT_GENERATE,
        fmt=schema.array_output_format("threats"),
    )
    proposals = client.first_json(resp).get("threats", [])
    return [_force_unverified(p) for p in proposals]


def run(index: list[dict], *, client_obj, run_id: str) -> list[dict]:
    proposals = _dry(index) if client.is_dry_run(client_obj) else _live(index, client_obj=client_obj)
    for rec in proposals:
        models.stamp_provenance(rec, layer="generate", run_id=run_id)
    return proposals
