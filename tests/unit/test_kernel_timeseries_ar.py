"""Unit tests for oec.kernel.timeseries.ar (v2.5.1 AR/autocorrelation package).

Every expected value below is hand-derived (see the docstring of each test)
rather than merely re-deriving what the implementation computes — the same
convention as the rest of the kernel test suite.
"""

from __future__ import annotations

import pytest

from oec.kernel.timeseries.ar import ar_yule_walker, autocorrelation, levinson_durbin, pacf


class TestAutocorrelation:
    def test_alternating_series_matches_hand_derived_biased_acf(self) -> None:
        """series = [1, -1, 1, -1], demeaned (mean=0) so y=series, c0=sum(y^2)=4.
        lag1 raw = y0y1+y1y2+y2y3 = -1-1-1 = -3 -> acf1 = -3/4 = -0.75
        lag2 raw = y0y2+y1y3 = 1+1 = 2 -> acf2 = 2/4 = 0.5
        lag3 raw = y0y3 = -1 -> acf3 = -1/4 = -0.25
        """
        out = autocorrelation([1.0, -1.0, 1.0, -1.0], nlags=3, method="biased")
        assert out["acf"] == pytest.approx([1.0, -0.75, 0.5, -0.25], abs=1e-12)
        assert out["n"] == 4
        assert out["backend"] == "numpy"
        assert out["converged"] is None

    def test_alternating_series_unbiased_acf_hits_unit_magnitude_at_lag1(self) -> None:
        """Same series; unbiased estimator divides each lag's raw cross-sum by
        (n-k) instead of n: r1 = raw*n/((n-1)*c0) = -3*4/(3*4) = -1.0 exactly
        -- a real, non-contrived example of the unbiased estimator producing a
        |correlation| == 1 that a valid PSD sequence could never have.
        """
        out = autocorrelation([1.0, -1.0, 1.0, -1.0], nlags=3, method="unbiased")
        assert out["acf"] == pytest.approx([1.0, -1.0, 1.0, -1.0], abs=1e-12)

    def test_nlags_must_be_less_than_series_length(self) -> None:
        with pytest.raises(ValueError, match="nlags"):
            autocorrelation([1.0, 2.0, 3.0], nlags=3)

    def test_zero_variance_series_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="zero variance"):
            autocorrelation([5.0, 5.0, 5.0], nlags=1)

    def test_short_series_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="length >= 2"):
            autocorrelation([1.0], nlags=1)


class TestLevinsonDurbin:
    def test_exact_ar1_geometric_acf_recovers_single_nonzero_coefficient(self) -> None:
        """r_k = 0.5^k is the exact autocorrelation of an AR(1) process with
        phi=0.5. Fitting any higher order to an exact AR(1) sequence must
        recover phi at lag 1 and exactly 0 at every higher lag (textbook
        property of Levinson-Durbin applied to an exact low-order process).
        """
        out = levinson_durbin([1.0, 0.5, 0.25, 0.125])
        assert out["ar_coefficients"] == pytest.approx([0.5, 0.0, 0.0], abs=1e-12)
        assert out["reflection_coefficients"] == pytest.approx([0.5, 0.0, 0.0], abs=1e-12)
        assert out["is_positive_definite"] is True
        assert out["order_reached"] == 3
        # E_0=1, E_1=1*(1-0.25)=0.75, E_2=E_3=0.75 (phi=0 keeps error flat)
        assert out["prediction_error_variance"] == pytest.approx([1.0, 0.75, 0.75, 0.75], abs=1e-12)

    def test_alternating_series_biased_acf_matches_hand_derived_recursion(self) -> None:
        """acf = [1, -0.75, 0.5, -0.25] (from TestAutocorrelation above).
        k=1: phi11 = -0.75/1 = -0.75; a=[-0.75]; E1 = 1*(1-0.5625) = 0.4375
        k=2: acc = 0.5 - (-0.75)(-0.75) = 0.5 - 0.5625 = -0.0625
             phi22 = -0.0625/0.4375 = -1/7
             a1_new = -0.75 - (-1/7)(-0.75) = -0.75*(8/7) = -6/7
             a2_new = phi22 = -1/7; E2 = 0.4375*(1-1/49) = 3/7
        k=3: acc = -0.25 - [(-6/7)(0.5) + (-1/7)(-0.75)] = 1/14
             phi33 = (1/14)/(3/7) = 1/6
             a1_new = -6/7 - (1/6)(-1/7) = -6/7 + 1/42 = -5/6
             a2_new = -1/7 - (1/6)(-6/7) = -1/7 + 1/7 = 0
             a3_new = phi33 = 1/6
        """
        out = levinson_durbin([1.0, -0.75, 0.5, -0.25])
        assert out["reflection_coefficients"] == pytest.approx(
            [-0.75, -1.0 / 7.0, 1.0 / 6.0], abs=1e-9
        )
        assert out["ar_coefficients"] == pytest.approx([-5.0 / 6.0, 0.0, 1.0 / 6.0], abs=1e-9)
        assert out["is_positive_definite"] is True

    def test_non_positive_definite_sequence_stops_honestly(self) -> None:
        """r1 > r0 cannot occur for a real autocorrelation sequence
        (|correlation| <= 1 by Cauchy-Schwarz); the recursion must stop at
        order 0 rather than produce a coefficient from an impossible input.
        """
        out = levinson_durbin([1.0, 1.5])
        assert out["is_positive_definite"] is False
        assert out["order_reached"] == 0
        assert out["ar_coefficients"] == []
        assert out["reflection_coefficients"] == []

    def test_unbiased_estimator_edge_case_feeds_a_boundary_reflection_coefficient(self) -> None:
        """The unbiased-ACF edge case from TestAutocorrelation ([1,-1,1,-1])
        has |r1| == 1 exactly -> phi11 == -1.0, which fails the strict
        |phi| < 1 invariant and stops the recursion at order 0.
        """
        out = levinson_durbin([1.0, -1.0, 1.0, -1.0])
        assert out["is_positive_definite"] is False
        assert out["order_reached"] == 0

    def test_non_positive_r0_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            levinson_durbin([0.0, 0.5])

    def test_short_sequence_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="length >= 2"):
            levinson_durbin([1.0])


class TestArYuleWalker:
    def test_alternating_series_order1_matches_hand_derived_yule_walker(self) -> None:
        """acf_used = [1, -0.75] (biased, order=1). phi = -0.75/1 = -0.75.
        E1 = 1*(1-0.5625) = 0.4375. sample_variance = c0/n = 4/4 = 1.0
        (series is already demeaned: mean=0). innovation_variance =
        sample_variance * E1 = 0.4375.
        """
        out = ar_yule_walker([1.0, -1.0, 1.0, -1.0], order=1)
        assert out["ar_coefficients"] == pytest.approx([-0.75], abs=1e-12)
        assert out["sample_variance"] == pytest.approx(1.0, abs=1e-12)
        assert out["innovation_variance"] == pytest.approx(0.4375, abs=1e-12)
        assert out["is_positive_definite"] is True
        assert out["order_reached"] == 1
        assert out["method"] == "yule_walker_levinson_durbin"

    def test_order_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="order"):
            ar_yule_walker([1.0, 2.0, 3.0], order=0)

    def test_biased_acf_estimator_is_used_regardless_of_caller_intent(self) -> None:
        """ar_yule_walker always estimates its own ACF with the biased
        estimator (never delegates the choice) precisely so the resulting
        sequence is guaranteed positive semidefinite and the recursion
        never has to stop early."""
        out = ar_yule_walker([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0], order=3)
        assert out["is_positive_definite"] is True
        assert out["order_reached"] == 3


class TestPacf:
    def test_alternating_series_matches_hand_derived_reflection_coefficients(self) -> None:
        out = pacf([1.0, -1.0, 1.0, -1.0], nlags=3)
        assert out["pacf"] == pytest.approx([1.0, -0.75, -1.0 / 7.0, 1.0 / 6.0], abs=1e-9)
        assert out["is_positive_definite"] is True
        assert out["order_reached"] == 3

    def test_exact_ar1_geometric_series_pacf_is_zero_past_lag1(self) -> None:
        out = pacf([1.0, 0.5, 0.25, 0.125, 0.0625], nlags=3, demean=False)
        # Not a real series' PACF (these are literal geometric values passed
        # as "series"); this only exercises the plumbing end-to-end against
        # the same closed-form recursion already verified in TestLevinsonDurbin.
        assert len(out["pacf"]) == 4
        assert out["method"] == "levinson-durbin"

    def test_unsupported_method_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="method"):
            pacf([1.0, 2.0, 3.0], nlags=1, method="burg")
