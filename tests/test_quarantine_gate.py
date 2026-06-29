"""The deterministic quarantine gate is the core trust defense — test it directly."""

from pipeline.layers.verify import apply_gate


def _claim(status, url="", sid="claim-1"):
    return {
        "id": sid,
        "text": "a checkable assertion",
        "source_name": "Some Source",
        "source_url": url,
        "retrieved_date": "2026-01-01",
        "verification_status": status,
    }


def _rec(claims):
    return {
        "id": "x",
        "claims": claims,
        "verification": {"status": "unverified", "confidence": "low", "notes": ""},
    }


def test_allowlisted_verified_claim_publishes():
    r = apply_gate(_rec([_claim("verified", "https://www.usgs.gov/x")]))
    assert r["verification"]["status"] == "verified"
    assert r["verification"]["confidence"] == "high"


def test_non_allowlisted_source_is_downgraded_and_quarantined():
    r = apply_gate(_rec([_claim("verified", "https://blog.example.com/post")]))
    assert r["claims"][0]["verification_status"] == "unverified"
    assert r["verification"]["status"] == "quarantined"


def test_disputed_claim_quarantines_even_with_a_verified_one():
    r = apply_gate(_rec([
        _claim("verified", "https://www.usgs.gov/a", "claim-1"),
        _claim("disputed", "https://www.who.int/b", "claim-2"),
    ]))
    assert r["verification"]["status"] == "quarantined"


def test_verified_plus_unverified_is_partial():
    r = apply_gate(_rec([
        _claim("verified", "https://www.usgs.gov/a", "claim-1"),
        _claim("unverified", "", "claim-2"),
    ]))
    assert r["verification"]["status"] == "partial"
    assert r["verification"]["confidence"] == "medium"


def test_no_verified_claim_quarantines():
    r = apply_gate(_rec([_claim("unverified", "", "claim-1")]))
    assert r["verification"]["status"] == "quarantined"


def test_source_name_normalized_to_allowlist_label():
    r = apply_gate(_rec([_claim("verified", "https://cneos.jpl.nasa.gov/x")]))
    assert r["claims"][0]["source_name"] == "NASA CNEOS"
