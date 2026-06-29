"""End-to-end: the full pipeline runs under --dry-run with no API calls and no writes."""

from pipeline import run


def test_dry_run_publishes_and_quarantines():
    summary = run.run(dry_run=True)
    assert summary["dry_run"] is True
    # The real seed plus the deterministic 'verifiable' proposal publish...
    assert "yellowstone-supervolcano" in summary["published"]
    assert "asteroid-impact" in summary["published"]
    # ...and the proposal with a non-authoritative source quarantines.
    assert "rogue-ai" in summary["quarantined"]


def test_only_slug_runs_single_threat():
    summary = run.run(dry_run=True, only_slug="yellowstone-supervolcano")
    assert summary["published"] == ["yellowstone-supervolcano"]
    assert summary["quarantined"] == []
