from pipeline import config, store


def test_path_mapping():
    assert store.path_for("nuclear-war").name == "nuclear-war.json"
    assert store.path_for("nuclear-war").parent.name == "threats"
    assert store.quarantine_path_for("x").parent.name == "quarantine"


def test_atomic_write_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "THREATS_DIR", tmp_path / "threats")
    rec = {"id": "demo-threat", "name": "Demo"}

    path = store.write_record(rec)
    assert path.exists()
    assert path.name == "demo-threat.json"
    # No temp files left behind by the atomic write.
    assert not list((tmp_path / "threats").glob("*.tmp"))
    assert store.load(path) == rec


def test_load_all_keys_by_slug(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "THREATS_DIR", tmp_path / "threats")
    store.write_record({"id": "a-threat", "name": "A"})
    store.write_record({"id": "b-threat", "name": "B"})
    loaded = store.load_all()
    assert set(loaded) == {"a-threat", "b-threat"}
    assert loaded["a-threat"]["name"] == "A"


def test_quarantine_write_targets_quarantine_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "QUARANTINE_DIR", tmp_path / "quarantine")
    path = store.write_record({"id": "bad", "name": "Bad"}, quarantine=True)
    assert path.parent == tmp_path / "quarantine"
    assert path.exists()
