"""Deterministic, no-API authoring of a single threat record.

The $0 path for adding or updating a threat: Claude Code (on a Max subscription) or a human drafts
the factual content, and `finalize` runs it through the exact trust machinery the model pipeline
uses — the allowlist quarantine gate decides verified-vs-quarantined, never the drafter's say-so.

A draft is a published record MINUS the fields computed here: `verification`, `sort_keys`,
`provenance`, `last_updated`, and `schema_version` (defaulted). It must already contain `id`, `name`,
`category`, `description`, `assessment`, and `claims` (each with a real `source_url` +
`retrieved_date`).
"""

from __future__ import annotations

from . import models, schema, store
from .layers.optimize import compute_sort_keys
from .layers.verify import apply_gate


def finalize(record: dict, *, run_id: str | None = None) -> dict:
    """Run a draft through gate -> sort_keys -> provenance -> schema. Mutates and returns it.

    Reuses `verify.apply_gate` (the allowlist quarantine gate), `optimize.compute_sort_keys`, and
    `models.stamp_provenance`. Raises `schema.ValidationError` on any invalid field. No API calls.
    """
    record.setdefault("schema_version", models.SCHEMA_VERSION)
    apply_gate(record)  # sets verification block + normalizes source_name from the allowlist
    record["sort_keys"] = compute_sort_keys(record)
    models.stamp_provenance(record, layer="verify", run_id=run_id or models.new_run_id())
    schema.validate(record)
    return record


def write(record: dict, *, run_id: str | None = None) -> tuple[dict, str, bool]:
    """Finalize then write to data/threats/ or data/quarantine/ by gate result."""
    rec = finalize(record, run_id=run_id)
    quarantined = rec["verification"]["status"] == "quarantined"
    path = store.write_record(rec, quarantine=quarantined)
    return rec, str(path), quarantined
