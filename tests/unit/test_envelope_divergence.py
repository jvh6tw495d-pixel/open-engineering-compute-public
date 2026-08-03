"""Anti-spurious divergence matrix for ``oec.mcp.divergence`` (v2.5.3 Wave 2).

Covers the post-serialization ``claimed_answer`` vs ``authoritative_answer``
comparison: values that must never be flagged (``MUST_NOT_FLAG``) and values
that must always be flagged (``MUST_FLAG``). ``detect_divergence`` never
mutates its inputs and never overrides ``authoritative_answer`` — it only
ever returns an advisory ``host_output_diverged`` body or ``None``.
"""

from __future__ import annotations

import copy
import json
import math
from typing import Any

import pytest

from oec.mcp.divergence import (
    DEFAULT_ABS_TOLERANCE,
    DEFAULT_REL_TOLERANCE,
    DIVERGENCE_POLICY_VERSION,
    canonical_json,
    compare_values,
    detect_divergence,
    numbers_equal,
    structural_equal,
)

# ---------------------------------------------------------------------------
# Anti-spurious matrix: (case name, authoritative values, claimed_answer)
# ---------------------------------------------------------------------------

MUST_NOT_FLAG: list[tuple[str, dict[str, Any], Any]] = [
    ("float_vs_int_equal", {"x": 1.0}, {"x": 1}),
    ("int_vs_float_equal", {"x": 1}, {"x": 1.0}),
    ("abs_tolerance_within_bound", {"x": 1.0}, {"x": 1.0 + 1e-10}),
    (
        "rel_tolerance_large_numbers",
        {"x": 1_000_000.0},
        {"x": 1_000_000.0 * (1 + 1e-7)},
    ),
    (
        "quantity_value_exact_match",
        {"q": {"value": 10, "unit": "kW"}},
        {"q": {"value": 10, "unit": "kW"}},
    ),
    ("subset_claim_single_key", {"x": 1, "y": 2}, {"x": 1}),
    ("subset_claim_nested", {"a": {"x": 1, "y": 2}}, {"a": {"x": 1}}),
    ("key_omitted_from_claim_is_not_a_claim", {"x": None, "y": 2}, {"y": 2}),
    ("list_equal_elementwise", {"a": [1, 2, 3]}, {"a": [1, 2, 3]}),
    ("tuple_vs_list_post_serialization", {"a": [1, 2, 3]}, {"a": (1, 2, 3)}),
    (
        "nested_structure_equal_mixed_numeric_types",
        {"a": {"b": [1, {"c": 2.0}]}},
        {"a": {"b": [1, {"c": 2}]}},
    ),
    ("string_exact_match", {"s": "optimal"}, {"s": "optimal"}),
    ("bool_exact_match_true", {"flag": True}, {"flag": True}),
    ("bool_exact_match_false", {"flag": False}, {"flag": False}),
    (
        "aggregate_multi_key_all_within_tolerance",
        {"a": 1.0, "b": 2.0, "c": 3.0},
        {"a": 1.0000000001, "b": 2, "c": 3.0},
    ),
    ("dict_key_insertion_order_independent", {"a": 1, "b": 2}, {"b": 2, "a": 1}),
    (
        "double_serialization_round_trip",
        {"a": 1, "b": [1, 2]},
        json.loads(json.dumps({"a": 1, "b": [1, 2]})),
    ),
    ("explicit_null_matches_explicit_null", {"x": None}, {"x": None}),
]

MUST_FLAG: list[tuple[str, dict[str, Any], Any]] = [
    ("value_mismatch_float", {"x": 1.0}, {"x": 1.5}),
    ("nan_claim_fails_closed", {"x": 1.0}, {"x": float("nan")}),
    ("positive_inf_claim_fails_closed", {"x": 1.0}, {"x": float("inf")}),
    ("negative_inf_claim_fails_closed", {"x": 1.0}, {"x": float("-inf")}),
    ("explicit_null_vs_real_value", {"x": 1.0}, {"x": None}),
    ("real_value_vs_authoritative_null", {"x": None}, {"x": 1.0}),
    ("fabricated_claim_key_not_in_authority", {"x": 1.0}, {"y": 1.0}),
    ("list_length_mismatch", {"a": [1, 2, 3]}, {"a": [1, 2]}),
    ("list_element_mismatch", {"a": [1, 2, 3]}, {"a": [1, 9, 3]}),
    ("bool_mismatch", {"flag": True}, {"flag": False}),
    ("string_mismatch", {"s": "optimal"}, {"s": "infeasible"}),
    ("type_mismatch_string_vs_number", {"x": 1}, {"x": "1"}),
    (
        "quantity_value_unit_mismatch",
        {"q": {"value": 10, "unit": "kW"}},
        {"q": {"value": 10, "unit": "MW"}},
    ),
    (
        "nested_deep_mismatch",
        {"a": {"b": {"c": 1.0}}},
        {"a": {"b": {"c": 2.0}}},
    ),
    ("type_mismatch_dict_claim_vs_scalar_authority", {"a": 1.0}, {"a": {"nested": 1.0}}),
    ("type_mismatch_list_claim_vs_scalar_authority", {"a": 1.0}, {"a": [1.0]}),
]


def test_matrix_meets_minimum_coverage_requirement() -> None:
    assert len(MUST_NOT_FLAG) >= 12
    assert len(MUST_FLAG) >= 8


@pytest.mark.parametrize(
    "case_name,authoritative_values,claimed",
    MUST_NOT_FLAG,
    ids=[case[0] for case in MUST_NOT_FLAG],
)
def test_must_not_flag(case_name: str, authoritative_values: dict[str, Any], claimed: Any) -> None:
    authoritative_answer = {
        "kind": "generic_result",
        "values": authoritative_values,
        "provenance": {},
    }
    result = detect_divergence(authoritative_answer, claimed)
    assert result is None, f"{case_name} incorrectly flagged: {result}"


@pytest.mark.parametrize(
    "case_name,authoritative_values,claimed",
    MUST_FLAG,
    ids=[case[0] for case in MUST_FLAG],
)
def test_must_flag(case_name: str, authoritative_values: dict[str, Any], claimed: Any) -> None:
    authoritative_answer = {
        "kind": "generic_result",
        "values": authoritative_values,
        "provenance": {},
    }
    result = detect_divergence(authoritative_answer, claimed)
    assert result is not None, f"{case_name} should have been flagged but was not"
    assert result["policy_version"] == DIVERGENCE_POLICY_VERSION
    assert result["reason"] == "value_mismatch"
    assert result["mismatches"]


# ---------------------------------------------------------------------------
# Fail-closed / no-override guarantees
# ---------------------------------------------------------------------------


def test_detect_divergence_returns_none_when_no_claim_provided() -> None:
    authoritative_answer = {"kind": "generic_result", "values": {"x": 1.0}, "provenance": {}}
    assert detect_divergence(authoritative_answer, None) is None


def test_detect_divergence_flags_claim_with_no_authoritative_answer() -> None:
    result = detect_divergence(None, {"x": 1.0})
    assert result is not None
    assert result["reason"] == "no_authoritative_answer"
    assert result["policy_version"] == DIVERGENCE_POLICY_VERSION


def test_detect_divergence_never_mutates_authoritative_answer() -> None:
    authoritative_answer = {
        "kind": "generic_result",
        "values": {"x": 1.0},
        "provenance": {"run_id": "r1"},
    }
    before = copy.deepcopy(authoritative_answer)
    detect_divergence(authoritative_answer, {"x": 999.0})
    assert authoritative_answer == before


def test_detect_divergence_never_mutates_claimed_answer() -> None:
    claimed = {"x": 1.0, "nested": {"y": [1, 2, 3]}}
    before = copy.deepcopy(claimed)
    authoritative_answer = {"kind": "generic_result", "values": {"x": 2.0}, "provenance": {}}
    detect_divergence(authoritative_answer, claimed)
    assert claimed == before


def test_detect_divergence_missing_values_key_defaults_to_empty_dict() -> None:
    authoritative_answer = {"kind": "review_result", "provenance": {}}
    result = detect_divergence(authoritative_answer, {"passed": True})
    assert result is not None
    assert result["mismatches"][0]["reason"] == "claimed_key_not_in_authoritative"


def test_mismatch_reports_json_pointer_style_path_for_nested_field() -> None:
    authoritative_answer = {
        "kind": "generic_result",
        "values": {"a": {"b": [1, 2, {"c": 1.0}]}},
        "provenance": {},
    }
    claimed = {"a": {"b": [1, 2, {"c": 5.0}]}}
    result = detect_divergence(authoritative_answer, claimed)
    assert result is not None
    assert result["mismatches"][0]["path"] == "$.a.b[2].c"


# ---------------------------------------------------------------------------
# Helper-function unit coverage
# ---------------------------------------------------------------------------


def test_numbers_equal_within_absolute_tolerance() -> None:
    assert numbers_equal(1.0, 1.0 + DEFAULT_ABS_TOLERANCE / 2) is True


def test_numbers_equal_outside_tolerance() -> None:
    assert numbers_equal(1.0, 1.1) is False


def test_numbers_equal_respects_relative_tolerance_for_large_magnitudes() -> None:
    big = 1e9
    assert numbers_equal(big, big * (1 + DEFAULT_REL_TOLERANCE / 2)) is True


def test_numbers_equal_returns_none_for_nan() -> None:
    assert numbers_equal(float("nan"), 1.0) is None
    assert numbers_equal(1.0, float("nan")) is None


def test_numbers_equal_returns_none_for_infinity() -> None:
    assert numbers_equal(float("inf"), float("inf")) is None


def test_canonical_json_sorts_keys_and_uses_compact_separators() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_json_matches_transport_default_str_behavior() -> None:
    class Odd:
        def __str__(self) -> str:
            return "odd-value"

    assert canonical_json({"x": Odd()}) == '{"x":"odd-value"}'


def test_structural_equal_true_for_reordered_keys() -> None:
    assert structural_equal({"a": 1, "b": 2}, {"b": 2, "a": 1}) is True


def test_structural_equal_false_for_different_values() -> None:
    assert structural_equal({"a": 1}, {"a": 2}) is False


def test_structural_equal_is_strict_no_numeric_tolerance() -> None:
    # Unlike compare_values, structural_equal is a strict hash-style check —
    # it is not the tolerant path and must not silently accept near-matches.
    assert structural_equal({"a": 1.0}, {"a": 1.0 + 1e-12}) is False


def test_compare_values_empty_when_claim_is_empty_dict() -> None:
    assert compare_values({"x": 1.0}, {}) == []


def test_compare_values_reports_multiple_mismatches_independently() -> None:
    mismatches = compare_values({"a": 1.0, "b": "ok"}, {"a": 2.0, "b": "bad"})
    paths = {m["path"] for m in mismatches}
    assert paths == {"$.a", "$.b"}


def test_compare_values_math_isclose_reference_matches_numbers_equal() -> None:
    # Cross-check numbers_equal against math.isclose directly with the same
    # tolerance constants, so a future refactor can't silently drift.
    assert numbers_equal(2.0, 2.0 + 1e-10) == math.isclose(
        2.0, 2.0 + 1e-10, rel_tol=DEFAULT_REL_TOLERANCE, abs_tol=DEFAULT_ABS_TOLERANCE
    )
