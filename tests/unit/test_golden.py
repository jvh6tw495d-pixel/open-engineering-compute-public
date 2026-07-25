import pytest

from oec.validation.golden import GoldenCase, assert_matches_golden, diff_against_golden


def _golden(**overrides: object) -> GoldenCase:
    defaults: dict[str, object] = {
        "id": "identity-basic",
        "skill_id": "mathematics.identity",
        "skill_version": "0.1.0",
        "inputs": {"value": 42},
        "expected_result": {"value": 42.0},
        "source": "hand-computed",
        "justification": "trivial identity",
    }
    defaults.update(overrides)
    return GoldenCase(**defaults)  # type: ignore[arg-type]


def test_exact_match_has_no_mismatches() -> None:
    golden = _golden()
    assert diff_against_golden({"value": 42.0}, golden) == []


def test_within_tolerance_has_no_mismatches() -> None:
    golden = _golden(expected_result={"value": 1.0}, tolerance=1e-6)
    assert diff_against_golden({"value": 1.0 + 1e-9}, golden) == []


def test_outside_tolerance_is_reported() -> None:
    golden = _golden(expected_result={"value": 1.0}, tolerance=1e-9)
    mismatches = diff_against_golden({"value": 1.5}, golden)
    assert len(mismatches) == 1
    assert "result.value" in mismatches[0]


def test_missing_key_is_reported() -> None:
    golden = _golden(expected_result={"value": 1.0, "unit": "V"})
    mismatches = diff_against_golden({"value": 1.0}, golden)
    assert any("unit" in m and "missing" in m for m in mismatches)


def test_unexpected_extra_key_is_reported() -> None:
    golden = _golden(expected_result={"value": 1.0})
    mismatches = diff_against_golden({"value": 1.0, "extra": True}, golden)
    assert any("extra" in m and "unexpected" in m for m in mismatches)


def test_nested_structures_are_compared_recursively() -> None:
    golden = _golden(expected_result={"phases": [{"voltage": 380.0}, {"voltage": 380.0}]})
    actual = {"phases": [{"voltage": 380.0}, {"voltage": 381.0}]}
    mismatches = diff_against_golden(actual, golden)
    assert len(mismatches) == 1
    assert "phases[1].voltage" in mismatches[0]


def test_assert_matches_golden_raises_with_all_mismatches() -> None:
    golden = _golden(expected_result={"value": 1.0})
    with pytest.raises(AssertionError, match="identity-basic"):
        assert_matches_golden({"value": 2.0}, golden)


def test_assert_matches_golden_passes_silently_on_match() -> None:
    golden = _golden()
    assert_matches_golden({"value": 42.0}, golden)  # must not raise


def test_expected_mapping_but_actual_is_not_is_reported() -> None:
    golden = _golden(expected_result={"nested": {"value": 1.0}})
    mismatches = diff_against_golden({"nested": "not a mapping"}, golden)
    assert any("expected a mapping" in m for m in mismatches)


def test_expected_list_but_actual_is_not_is_reported() -> None:
    golden = _golden(expected_result={"items": [1.0, 2.0]})
    mismatches = diff_against_golden({"items": "not a list"}, golden)
    assert any("expected a list" in m for m in mismatches)


def test_expected_list_wrong_length_is_reported() -> None:
    golden = _golden(expected_result={"items": [1.0, 2.0]})
    mismatches = diff_against_golden({"items": [1.0]}, golden)
    assert any("expected a list of length 2" in m for m in mismatches)


def test_expected_number_but_actual_is_not_is_reported() -> None:
    golden = _golden(expected_result={"value": 1.0})
    mismatches = diff_against_golden({"value": "not a number"}, golden)
    assert any("expected a number" in m for m in mismatches)


def test_non_numeric_leaf_uses_exact_equality() -> None:
    golden = _golden(expected_result={"unit": "V"})
    assert diff_against_golden({"unit": "V"}, golden) == []
    mismatches = diff_against_golden({"unit": "kV"}, golden)
    assert any("expected 'V'" in m for m in mismatches)
