"""Application configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """RapidTrader configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    RT_DB_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rapidtrader"

    # Alpaca API - Market data and trading execution
    RT_ALPACA_API_KEY: str = ""
    RT_ALPACA_SECRET_KEY: str = ""
    RT_ALPACA_PAPER: bool = True
    RT_ALPACA_ENDPOINT: str = "https://paper-api.alpaca.markets"

    # FMP API - Company fundamentals and sector data (optional)
    RT_FMP_API_KEY: str = ""

    # Market Filter - SPY 200-day SMA trend filter
    RT_MARKET_FILTER_ENABLE: int = 1
    RT_MARKET_FILTER_SMA: int = 200
    RT_MARKET_FILTER_SYMBOL: str = "SPY"
    RT_ALLOW_EXITS_IN_BEAR: int = 1
    RT_SELLS_HELD_POSITIONS_ONLY: int = 0

    # Signal Confirmation - Requires multiple strategy confirmations
    RT_ENABLE_SIGNAL_CONFIRM: int = 1
    RT_CONFIRM_WINDOW: int = 3
    RT_CONFIRM_MIN_COUNT: int = 2

    # ATR Stops - Volatility-based stop losses
    RT_ENABLE_ATR_STOP: int = 1
    RT_ATR_LOOKBACK: int = 14
    RT_ATR_STOP_K: float = 3.0
    RT_COOLDOWN_DAYS_ON_STOP: int = 1

    # Position Sizing
    RT_START_CAPITAL: float = 100_000.0
    RT_PCT_PER_TRADE: float = 0.05
    RT_DAILY_RISK_CAP: float = 0.005
    RT_MAX_EXPOSURE_PER_SECTOR: float = 0.30

    # Kill Switch - Emergency stop at drawdown threshold
    RT_DRAWDOWN_THRESHOLD: float = -0.12

    # Portfolio Heat - Maximum aggregate risk across all positions
    RT_MAX_PORTFOLIO_HEAT: float = 0.06
    RT_PORTFOLIO_HEAT_ENABLE: int = 1

    # VIX Scaling - Reduce position sizes in high volatility
    RT_VIX_SCALING_ENABLE: int = 1
    RT_VIX_THRESHOLD_ELEVATED: float = 20.0
    RT_VIX_THRESHOLD_HIGH: float = 30.0
    RT_VIX_SCALE_ELEVATED: float = 0.5
    RT_VIX_SCALE_HIGH: float = 0.25

    # Correlation Check - Prevent overconcentration in correlated positions
    RT_CORRELATION_CHECK_ENABLE: int = 1
    RT_CORRELATION_THRESHOLD: float = 0.75
    RT_CORRELATION_LOOKBACK: int = 60
    RT_CORRELATION_TOP_N: int = 3

    # Logging
    RT_LOG_LEVEL: str = "INFO"
    RT_LOG_JSON: bool = False
    RT_LOG_FILE: str = ""

settings = Settings()
