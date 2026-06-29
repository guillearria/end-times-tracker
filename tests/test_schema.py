import copy
import json

import jsonschema
import pytest

from pipeline import config, schema, store

SEED = store.load(config.THREATS_DIR / "yellowstone-supervolcano.json")


def test_schema_is_valid_draft_2020_12():
    jsonschema.Draft202012Validator.check_schema(schema.load_schema())


def test_seed_validates():
    schema.validate(copy.deepcopy(SEED))


def test_missing_required_field_rejected():
    bad = copy.deepcopy(SEED)
    del bad["verification"]
    with pytest.raises(schema.ValidationError):
        schema.validate(bad)


def test_unknown_enum_value_rejected():
    bad = copy.deepcopy(SEED)
    bad["category"] = "alien-invasion"
    with pytest.raises(schema.ValidationError):
        schema.validate(bad)


def test_bad_slug_rejected_in_python():
    bad = copy.deepcopy(SEED)
    bad["id"] = "Not A Slug"
    with pytest.raises(schema.ValidationError):
        schema.validate(bad)


def test_rank_out_of_range_rejected_in_python():
    bad = copy.deepcopy(SEED)
    bad["sort_keys"]["severity_rank"] = 9
    with pytest.raises(schema.ValidationError):
        schema.validate(bad)


def test_output_format_has_no_unsupported_keywords():
    """The schema must stay usable as a Claude structured-output format."""
    blob = json.dumps(schema.output_format())
    for kw in ("minLength", "maxLength", "minimum", "maximum", "pattern"):
        assert kw not in blob, f"structured-output schema must not contain {kw}"


def test_array_output_format_wraps_records():
    fmt = schema.array_output_format("threats")
    props = fmt["schema"]["properties"]
    assert "threats" in props
    assert props["threats"]["type"] == "array"
