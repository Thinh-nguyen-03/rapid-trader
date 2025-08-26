from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    
    # Database
    RT_DB_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rapidtrader"
    
    # API Keys
    RT_POLYGON_API_KEY: str = ""
    
    # Market Filter (SPY 200-SMA gate)
    RT_MARKET_FILTER_ENABLE: int = 1
    RT_MARKET_FILTER_SMA: int = 200
    RT_MARKET_FILTER_SYMBOL: str = "SPY"
    
    # Signal Confirmation (2-of-3 accumulator)
    RT_ENABLE_SIGNAL_CONFIRM: int = 1
    RT_CONFIRM_WINDOW: int = 3
    RT_CONFIRM_MIN_COUNT: int = 2
    
    # ATR Stops
    RT_ENABLE_ATR_STOP: int = 1
    RT_ATR_LOOKBACK: int = 14
    RT_ATR_STOP_K: float = 3.0
    RT_COOLDOWN_DAYS_ON_STOP: int = 1
    
    # Position Sizing
    RT_START_CAPITAL: float = 100_000.0
    RT_PCT_PER_TRADE: float = 0.05  # 5% per trade
    RT_DAILY_RISK_CAP: float = 0.005  # 0.5% daily risk
    RT_MAX_EXPOSURE_PER_SECTOR: float = 0.30  # 30% max per sector

settings = Settings()
