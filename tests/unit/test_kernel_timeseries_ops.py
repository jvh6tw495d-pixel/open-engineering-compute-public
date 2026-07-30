"""Direct kernel tests for oec.kernel.timeseries.ops (v2.5.1 coverage push).

Targets the branches flagged as untested in
docs/implementation/v2.5-critical-path-coverage.md ("multi-column
resample/align edge cases", ops.py at 68%): each skill only exercises one
example per how/method variant, leaving the alternate branches untested.
"""

from __future__ import annotations

import pytest

from oec.kernel.timeseries.ops import align_series, fill_missing, power_to_energy, resample_series

_TS_HALF_HOUR = [
    "2024-01-01T00:00:00",
    "2024-01-01T00:30:00",
    "2024-01-01T01:00:00",
    "2024-01-01T01:30:00",
]


class TestResampleSeries:
    @pytest.mark.parametrize("how", ["mean", "sum", "min", "max", "last"])
    def test_each_reducer_runs(self, how: str) -> None:
        out = resample_series(_TS_HALF_HOUR, [1.0, 3.0, 2.0, 4.0], freq="1h", how=how)
        assert out["how"] == how
        assert out["n_points"] == 2

    def test_sum_matches_hand_derived_totals(self) -> None:
        out = resample_series(_TS_HALF_HOUR, [1.0, 3.0, 2.0, 4.0], freq="1h", how="sum")
        assert out["values"] == [4.0, 6.0]

    def test_last_matches_hand_derived_values(self) -> None:
        out = resample_series(_TS_HALF_HOUR, [1.0, 3.0, 2.0, 4.0], freq="1h", how="last")
        assert out["values"] == [3.0, 4.0]


class TestAlignSeries:
    def test_inner_join_keeps_only_common_timestamps(self) -> None:
        out = align_series(
            ["2024-01-01T00:00:00", "2024-01-01T01:00:00"],
            [1.0, 2.0],
            ["2024-01-01T00:00:00", "2024-01-01T02:00:00"],
            [10.0, 20.0],
            how="inner",
        )
        assert out["timestamps"] == ["2024-01-01T00:00:00"]
        assert out["values_a"] == [1.0]
        assert out["values_b"] == [10.0]

    def test_outer_join_keeps_every_timestamp_with_nulls(self) -> None:
        out = align_series(
            ["2024-01-01T00:00:00", "2024-01-01T01:00:00"],
            [1.0, 2.0],
            ["2024-01-01T00:00:00", "2024-01-01T02:00:00"],
            [10.0, 20.0],
            how="outer",
        )
        assert out["n_points"] == 3
        assert out["values_a"] == [1.0, 2.0, None]
        assert out["values_b"] == [10.0, None, 20.0]

    def test_duplicate_timestamps_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="unique"):
            align_series(
                ["2024-01-01T00:00:00", "2024-01-01T00:00:00"],
                [1.0, 2.0],
                ["2024-01-01T00:00:00"],
                [10.0],
            )


class TestFillMissing:
    _TS3 = ["2024-01-01T00:00:00", "2024-01-01T01:00:00", "2024-01-01T02:00:00"]

    def test_ffill(self) -> None:
        out = fill_missing(self._TS3, [1.0, None, None], method="ffill")
        assert out["values"] == [1.0, 1.0, 1.0]
        assert out["n_filled"] == 2
        assert out["n_remaining_missing"] == 0

    def test_bfill(self) -> None:
        out = fill_missing(self._TS3, [None, None, 3.0], method="bfill")
        assert out["values"] == [3.0, 3.0, 3.0]

    def test_linear(self) -> None:
        out = fill_missing(self._TS3, [1.0, None, 3.0], method="linear")
        assert out["values"] == [1.0, 2.0, 3.0]

    def test_ffill_leaves_a_leading_gap_unfilled(self) -> None:
        """ffill has nothing to carry forward at the start; n_remaining_missing > 0."""
        out = fill_missing(self._TS3, [None, None, 3.0], method="ffill")
        assert out["values"][0] is None
        assert out["n_remaining_missing"] == 2


class TestPowerToEnergy:
    _TS2 = ["2024-01-01T00:00:00", "2024-01-01T01:00:00"]

    @pytest.mark.parametrize(
        ("power_unit", "energy_unit", "scale"),
        [
            ("kW", "kWh", 1.0),
            ("W", "Wh", 1.0),
            ("W", "kWh", 1.0 / 1000.0),
            ("kW", "Wh", 1000.0),
            ("MW", "MWh", 1.0),
            ("MW", "kWh", 1000.0),
        ],
    )
    def test_every_supported_unit_pair(
        self, power_unit: str, energy_unit: str, scale: float
    ) -> None:
        out = power_to_energy(self._TS2, [2.0, 2.0], power_unit=power_unit, energy_unit=energy_unit)
        # constant 2.0 power over 1h: trapezoid = 0.5*(2+2)*1*scale = 2*scale
        assert out["total_energy"] == pytest.approx(2.0 * scale)
        assert out["power_unit"] == power_unit
        assert out["energy_unit"] == energy_unit

    def test_case_and_whitespace_insensitive_unit_matching(self) -> None:
        out = power_to_energy(self._TS2, [2.0, 2.0], power_unit=" kw ", energy_unit=" KWH ")
        assert out["total_energy"] == pytest.approx(2.0)

    def test_unsupported_unit_pair_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="unsupported power/energy unit pair"):
            power_to_energy(self._TS2, [2.0, 2.0], power_unit="hp", energy_unit="kWh")

    def test_fewer_than_two_timestamps_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 2 timestamps"):
            power_to_energy(["2024-01-01T00:00:00"], [2.0])

    def test_duplicate_timestamps_are_rejected_by_the_shared_to_series_check(self) -> None:
        """Note: power_to_energy's own `dt_hours <= 0` guard is unreachable
        through the public API -- `_to_series` always sorts and rejects
        duplicate timestamps first, so two equal-or-decreasing consecutive
        points can never reach the loop. This test documents the actual
        (earlier, different-message) failure rather than the unreachable one."""
        with pytest.raises(ValueError, match="unique"):
            power_to_energy(["2024-01-01T01:00:00", "2024-01-01T01:00:00"], [2.0, 2.0])
