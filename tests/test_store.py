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


# --- Event-kind mirrors: guard the regression already hit once (a frozen dict of
# paths in dirs_for broke monkeypatch isolation until fixed with lambdas). ---

def test_path_mapping_events():
    assert store.path_for("earthquake", kind="event").parent.name == "events"
    assert store.quarantine_path_for("x", kind="event").parent.name == "quarantine-events"


def test_atomic_write_roundtrip_events(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENTS_DIR", tmp_path / "events")
    rec = {"id": "demo-event", "name": "Demo"}

    path = store.write_record(rec, kind="event")
    assert path.exists()
    assert path.parent == tmp_path / "events"
    assert store.load(path) == rec


def test_load_all_keys_by_slug_events(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENTS_DIR", tmp_path / "events")
    store.write_record({"id": "a-event", "name": "A"}, kind="event")
    store.write_record({"id": "b-event", "name": "B"}, kind="event")
    loaded = store.load_all(kind="event")
    assert set(loaded) == {"a-event", "b-event"}
    assert loaded["a-event"]["name"] == "A"


def test_quarantine_write_targets_quarantine_events_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "QUARANTINE_EVENTS_DIR", tmp_path / "quarantine-events")
    path = store.write_record({"id": "bad-event", "name": "Bad"}, quarantine=True, kind="event")
    assert path.parent == tmp_path / "quarantine-events"
    assert path.exists()


def test_writing_one_kind_does_not_touch_the_other(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "THREATS_DIR", tmp_path / "threats")
    monkeypatch.setattr(config, "EVENTS_DIR", tmp_path / "events")
    store.write_record({"id": "isolated-threat", "name": "T"}, kind="threat")
    store.write_record({"id": "isolated-event", "name": "E"}, kind="event")
    assert set(store.load_all(kind="threat")) == {"isolated-threat"}
    assert set(store.load_all(kind="event")) == {"isolated-event"}
    assert not (tmp_path / "events" / "isolated-threat.json").exists()
    assert not (tmp_path / "threats" / "isolated-event.json").exists()
