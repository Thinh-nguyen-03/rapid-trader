"""Domain models with validation for RapidTrader."""
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date
from typing import Literal
from decimal import Decimal


class TradingSymbol(BaseModel):
    """Validated trading symbol."""

    symbol: str = Field(..., pattern=r"^[A-Z\.]{1,10}$", description="Stock ticker symbol")
    sector: str = Field(..., min_length=1, max_length=50)
    is_active: bool = True

    class Config:
        frozen = True


class OHLCVBar(BaseModel):
    """Validated OHLCV bar data."""

    symbol: str = Field(..., pattern=r"^[A-Z\.]{1,10}$")
    date: date
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="High price")
    low: Decimal = Field(..., gt=0, description="Low price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")

    @model_validator(mode='after')
    def validate_prices(self):
        """Validate price relationships."""
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) cannot be less than low ({self.low})")

        if self.open > self.high:
            raise ValueError(f"Open ({self.open}) cannot exceed high ({self.high})")

        if self.close > self.high:
            raise ValueError(f"Close ({self.close}) cannot exceed high ({self.high})")

        if self.open < self.low:
            raise ValueError(f"Open ({self.open}) cannot be below low ({self.low})")

        if self.close < self.low:
            raise ValueError(f"Close ({self.close}) cannot be below low ({self.low})")

        return self


class PositionSizeRequest(BaseModel):
    """Request for position sizing calculation."""

    portfolio_value: Decimal = Field(..., gt=0, description="Total portfolio value")
    pct_per_trade: Decimal = Field(..., gt=0, lt=1, description="Percentage per trade")
    entry_price: Decimal = Field(..., gt=0, description="Entry price")

    class Config:
        validate_assignment = True


class ATRSizeRequest(BaseModel):
    """Request for ATR-based position sizing."""

    portfolio_value: Decimal = Field(..., gt=0)
    daily_risk_cap: Decimal = Field(..., gt=0, lt=0.1, description="Max 10% daily risk")
    atr_points: Decimal = Field(..., gt=0)
    k_atr: Decimal = Field(default=Decimal("3.0"), gt=0, le=10, description="ATR multiplier")

    class Config:
        validate_assignment = True


class TradingSignal(BaseModel):
    """Validated trading signal."""

    symbol: str = Field(..., pattern=r"^[A-Z\.]{1,10}$")
    date: date
    strategy: Literal['RSI_MR', 'SMA_X', 'COMBINED']
    direction: Literal['buy', 'sell', 'hold']
    strength: float = Field(..., ge=0.0, le=1.0, description="Signal strength")

    class Config:
        frozen = True


class OrderRequest(BaseModel):
    """Validated order request."""

    symbol: str = Field(..., pattern=r"^[A-Z\.]{1,10}$")
    date: date
    side: Literal['buy', 'sell', 'exit']
    quantity: int = Field(..., ge=0, description="Number of shares")
    order_type: Literal['market', 'limit'] = 'market'
    reason: str = Field(..., min_length=1, max_length=100)

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v, info):
        """Validate quantity based on side."""
        # Note: exit orders can have 0 quantity (means close full position)
        return v


class RiskLimits(BaseModel):
    """Risk limit configuration."""

    max_position_pct: Decimal = Field(default=Decimal("0.05"), gt=0, lt=1)
    max_sector_exposure: Decimal = Field(default=Decimal("0.30"), gt=0, le=1)
    max_portfolio_heat: Decimal = Field(default=Decimal("0.06"), gt=0, lt=1)
    drawdown_threshold: Decimal = Field(default=Decimal("-0.12"), lt=0, gt=-1)

    @field_validator('drawdown_threshold')
    @classmethod
    def validate_drawdown(cls, v):
        """Ensure drawdown is negative."""
        if v >= 0:
            raise ValueError("Drawdown threshold must be negative")
        return v
