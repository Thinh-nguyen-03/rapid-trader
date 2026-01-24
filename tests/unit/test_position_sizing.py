"""Unit tests for position sizing algorithms."""
import pytest
from rapidtrader.risk.sizing import (
    shares_fixed_fractional,
    shares_atr_target,
    apply_vix_scaling,
    compute_position_size
)


class TestFixedFractionalSizing:
    """Test fixed fractional position sizing."""

    def test_basic_calculation(self):
        """Test basic position size calculation."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=50.0
        )

        # $100k * 5% / $50 = 100 shares
        assert result == 100

    def test_rounds_down(self):
        """Test that fractional shares are rounded down."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=51.0
        )

        # $100k * 5% / $51 = 98.039... -> 98 shares
        assert result == 98

    def test_expensive_stock(self):
        """Test with expensive stock price."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=5000.0
        )

        # $100k * 5% / $5000 = 1 share
        assert result == 1

    def test_very_expensive_stock_returns_zero(self):
        """Test that very expensive stocks return 0 shares."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=10000.0
        )

        # $100k * 5% / $10000 = 0.5 -> 0 shares
        assert result == 0

    def test_negative_portfolio_returns_zero(self):
        """Test that negative portfolio value returns 0."""
        result = shares_fixed_fractional(
            portfolio_value=-100000,
            pct_per_trade=0.05,
            entry_px=50.0
        )
        assert result == 0

    def test_zero_percentage_returns_zero(self):
        """Test that zero percentage returns 0."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.0,
            entry_px=50.0
        )
        assert result == 0

    def test_very_small_price_handled(self):
        """Test handling of very small (but positive) prices."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=0.01
        )

        # $5000 / $0.01 = 500,000 shares
        assert result == 500000


class TestATRTargetSizing:
    """Test ATR-based volatility targeting."""

    def test_basic_calculation(self):
        """Test basic ATR target calculation."""
        result = shares_atr_target(
            portfolio_value=100000,
            daily_risk_cap=0.005,
            atr_points=2.0,
            k_atr=3.0
        )

        # Risk budget: $100k * 0.5% = $500
        # Unit risk: 3.0 * $2.0 = $6
        # Shares: $500 / $6 = 83.33... -> 83 shares
        assert result == 83

    def test_high_volatility_reduces_size(self):
        """Test that higher volatility reduces position size."""
        low_vol = shares_atr_target(100000, 0.005, atr_points=1.0, k_atr=3.0)
        high_vol = shares_atr_target(100000, 0.005, atr_points=5.0, k_atr=3.0)

        assert high_vol < low_vol

    def test_larger_risk_budget_increases_size(self):
        """Test that larger risk budget increases position size."""
        small_risk = shares_atr_target(100000, 0.001, atr_points=2.0, k_atr=3.0)
        large_risk = shares_atr_target(100000, 0.01, atr_points=2.0, k_atr=3.0)

        assert large_risk > small_risk

    def test_zero_atr_returns_large_position(self):
        """Test that zero ATR is handled (uses small epsilon)."""
        result = shares_atr_target(100000, 0.005, atr_points=0.0, k_atr=3.0)
        # Should not crash, returns very large number due to epsilon
        assert result >= 0

    def test_negative_portfolio_returns_zero(self):
        """Test that negative portfolio returns 0."""
        result = shares_atr_target(-100000, 0.005, atr_points=2.0, k_atr=3.0)
        assert result == 0


class TestVIXScaling:
    """Test VIX-based position scaling."""

    def test_full_multiplier(self):
        """Test that multiplier of 1.0 returns original shares."""
        result = apply_vix_scaling(100, 1.0)
        assert result == 100

    def test_half_multiplier(self):
        """Test that multiplier of 0.5 returns half shares."""
        result = apply_vix_scaling(100, 0.5)
        assert result == 50

    def test_quarter_multiplier(self):
        """Test that multiplier of 0.25 returns quarter shares."""
        result = apply_vix_scaling(100, 0.25)
        assert result == 25

    def test_zero_multiplier_returns_zero(self):
        """Test that zero multiplier returns 0."""
        result = apply_vix_scaling(100, 0.0)
        assert result == 0

    def test_negative_multiplier_returns_zero(self):
        """Test that negative multiplier returns 0."""
        result = apply_vix_scaling(100, -0.5)
        assert result == 0

    def test_multiplier_greater_than_one(self):
        """Test that multiplier > 1 returns original shares (capped)."""
        result = apply_vix_scaling(100, 1.5)
        assert result == 100


class TestComputePositionSize:
    """Test the combined position sizing function."""

    def test_uses_minimum_of_methods(self):
        """Test that it takes minimum of fixed-fractional and ATR."""
        # Set up where fixed-fractional < ATR target
        result = compute_position_size(
            portfolio_value=100000,
            entry_px=50.0,
            atr_points=0.5,  # Low ATR = large ATR-based size
            pct_per_trade=0.05,
            daily_risk_cap=0.005,
            k_atr=3.0,
            vix_multiplier=1.0
        )

        # Fixed fractional: 100000 * 0.05 / 50 = 100
        # ATR target: 100000 * 0.005 / (3 * 0.5) = 333
        # Min = 100
        assert result == 100

    def test_vix_scaling_applied(self):
        """Test that VIX scaling is applied to final size."""
        full_size = compute_position_size(
            portfolio_value=100000,
            entry_px=50.0,
            atr_points=2.0,
            pct_per_trade=0.05,
            daily_risk_cap=0.005,
            k_atr=3.0,
            vix_multiplier=1.0
        )

        scaled_size = compute_position_size(
            portfolio_value=100000,
            entry_px=50.0,
            atr_points=2.0,
            pct_per_trade=0.05,
            daily_risk_cap=0.005,
            k_atr=3.0,
            vix_multiplier=0.5
        )

        assert scaled_size == full_size // 2

    def test_real_world_example(self):
        """Test with realistic trading parameters."""
        result = compute_position_size(
            portfolio_value=250000,
            entry_px=175.0,  # AAPL-like price
            atr_points=3.5,  # Typical ATR
            pct_per_trade=0.05,
            daily_risk_cap=0.005,
            k_atr=3.0,
            vix_multiplier=1.0
        )

        # Should return reasonable number of shares
        assert 0 < result < 500
        # Verify the dollar value is roughly 5% of portfolio
        dollar_value = result * 175.0
        assert dollar_value <= 250000 * 0.05


@pytest.mark.unit
class TestPositionSizingEdgeCases:
    """Edge case tests for position sizing."""

    def test_penny_stock(self):
        """Test sizing for penny stocks."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=0.50
        )
        # $5000 / $0.50 = 10,000 shares
        assert result == 10000

    def test_very_small_portfolio(self):
        """Test sizing for small portfolios."""
        result = shares_fixed_fractional(
            portfolio_value=1000,
            pct_per_trade=0.05,
            entry_px=100.0
        )
        # $50 / $100 = 0 shares (can't afford even 1)
        assert result == 0

    def test_large_portfolio(self):
        """Test sizing for large portfolios."""
        result = shares_fixed_fractional(
            portfolio_value=10_000_000,
            pct_per_trade=0.02,
            entry_px=500.0
        )
        # $200,000 / $500 = 400 shares
        assert result == 400
