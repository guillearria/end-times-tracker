"""Layer 2 — Verify (the trust core).

Two independent sub-calls on the live path (search with web tools and no format; then a fresh
structure call with the schema format and no tools — because web-search citations and
output_config.format cannot coexist). The deterministic `apply_gate` is the real defense and is
shared by both the live and dry paths, so it is the single source of truth and is unit-tested
directly.
"""

from __future__ import annotations

import json

from .. import client, config, models, schema


# --- The deterministic quarantine gate (pure) ------------------------------
def _gate_notes(status, verified, disputed, unverified) -> str:
    return (
        f"gate: {len(verified)} verified, {len(disputed)} disputed, {len(unverified)} unverified "
        f"-> {status}"
    )


def apply_gate(record: dict) -> dict:
    """Re-check every claim against the source allowlist and set verification status.

    A claim marked verified but citing a non-allowlisted domain is downgraded to unverified — the
    model's say-so is never trusted over the deterministic domain check. A record publishes only
    with >=1 verified claim and 0 disputed claims; otherwise it is quarantined.
    """
    claims = record.get("claims", [])
    for c in claims:
        if c.get("verification_status") == "verified":
            ok, label = config.allowlisted(c.get("source_url") or "")
            if not ok:
                c["verification_status"] = "unverified"
            elif label:
                c["source_name"] = label

    verified = [c for c in claims if c.get("verification_status") == "verified"]
    disputed = [c for c in claims if c.get("verification_status") == "disputed"]
    unverified = [c for c in claims if c.get("verification_status") == "unverified"]

    if disputed or not verified:
        status, confidence = "quarantined", "low"
    elif unverified:
        status, confidence = "partial", "medium"
    else:
        status, confidence = "verified", "high"

    record["verification"] = {
        "status": status,
        "confidence": confidence,
        "notes": _gate_notes(status, verified, disputed, unverified),
    }
    return record


# --- Dry path --------------------------------------------------------------
def _reverse_labels() -> dict[str, str]:
    rev: dict[str, str] = {}
    for domain, label in config.SOURCE_ALLOWLIST.items():
        rev.setdefault(label, domain)
    return rev


def _dry(record: dict) -> dict:
    """Assign citations deterministically: a claim whose source_name is an allowlist label
    'verifies'; anything else stays unverified (and the gate quarantines it)."""
    rev = _reverse_labels()
    today = models.utc_now_iso()[:10]
    for c in record.get("claims", []):
        c["retrieved_date"] = today
        # An already-cited, allowlisted source re-verifies (the common re-run case).
        ok, _ = config.allowlisted(c.get("source_url", "") or "")
        if ok:
            c["verification_status"] = "verified"
            continue
        # Otherwise fall back to the source_name -> allowlist-label mapping.
        domain = rev.get(c.get("source_name", ""))
        if domain:
            c["source_url"] = f"https://www.{domain}/"
            c["verification_status"] = "verified"
        else:
            c["source_url"] = ""
            c["verification_status"] = "unverified"
    return apply_gate(record)


# --- Live path -------------------------------------------------------------
def _extract_citations(resp) -> list[dict]:
    """Best-effort extraction of (url, source_name) from web_search/web_fetch result blocks.

    Branches on the documented shape: a successful result `content` is a list; an error `content`
    is an object carrying error_code, which we skip.
    """
    cites: list[dict] = []
    for block in getattr(resp, "content", []):
        if getattr(block, "type", None) not in ("web_search_tool_result", "web_fetch_tool_result"):
            continue
        content = getattr(block, "content", None)
        if not isinstance(content, list):  # error object -> skip
            continue
        for item in content:
            url = getattr(item, "url", None)
            if url:
                cites.append({"url": url, "source_name": getattr(item, "title", "") or ""})
    return cites


def _merge_verification(original: dict, structured: dict) -> dict:
    """Take only citation fields + status from the model; keep claim text/id from the original.

    This enforces 'Verify may not change claim text' structurally rather than by trust.
    """
    by_id = {c.get("id"): c for c in structured.get("claims", [])}
    for c in original.get("claims", []):
        s = by_id.get(c["id"], {})
        c["source_url"] = s.get("source_url", "") or ""
        c["source_name"] = s.get("source_name") or c.get("source_name", "")
        c["retrieved_date"] = s.get("retrieved_date", "") or ""
        c["verification_status"] = s.get("verification_status", "unverified")
    return original


def _live(record: dict, *, client_obj) -> dict:
    search_resp = client.call_layer(
        client_obj,
        model=config.MODEL_VERIFY,
        system=config.load_prompt("verify.search"),
        user_content="Verify these claims:\n"
        + json.dumps(record.get("claims", []), ensure_ascii=False, indent=2),
        effort=config.EFFORT_VERIFY,
        tools=[config.WEB_SEARCH_TOOL, config.WEB_FETCH_TOOL],
    )
    citations = _extract_citations(search_resp)

    struct_resp = client.call_layer(
        client_obj,
        model=config.MODEL_VERIFY,
        system=config.load_prompt("verify.structure"),
        user_content=json.dumps(
            {"record": record, "citations": citations}, ensure_ascii=False, indent=2
        ),
        effort=config.EFFORT_VERIFY,
        fmt=schema.output_format(),
    )
    merged = _merge_verification(record, client.first_json(struct_resp))
    return apply_gate(merged)


def run(record: dict, *, client_obj, run_id: str) -> dict:
    out = _dry(record) if client.is_dry_run(client_obj) else _live(record, client_obj=client_obj)
    models.stamp_provenance(out, layer="verify", run_id=run_id)
    return out
