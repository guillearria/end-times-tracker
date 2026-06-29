import json

from pipeline import config, models, store

SEED = store.load(config.THREATS_DIR / "yellowstone-supervolcano.json")


def test_dumps_is_deterministic_and_byte_stable():
    once = models.dumps(SEED)
    twice = models.dumps(json.loads(once))
    assert once == twice
    assert once.endswith("\n")


def test_index_of_excludes_claims():
    idx = models.index_of([SEED])
    assert set(idx[0].keys()) == {"id", "name", "category", "summary"}


def test_claims_fingerprint_ignores_prose_but_tracks_claims():
    fp = models.claims_fingerprint(SEED)
    other = json.loads(json.dumps(SEED))
    other["description"] = "totally rewritten prose"
    assert models.claims_fingerprint(other) == fp
    other["claims"][0]["text"] = "a different claim"
    assert models.claims_fingerprint(other) != fp


def test_provenance_history_is_capped_and_tracks_latest():
    rec: dict = {"provenance": {"history": []}}
    for i in range(25):
        models.stamp_provenance(rec, layer="verify", run_id=str(i))
    assert len(rec["provenance"]["history"]) == 20
    assert rec["provenance"]["last_run_id"] == "24"
    assert rec["last_updated"]


def test_slug_ok():
    assert models.slug_ok("nuclear-war")
    assert not models.slug_ok("Has Caps")
    assert not models.slug_ok("under_score")
