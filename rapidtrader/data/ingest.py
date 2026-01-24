"""OHLCV data ingestion from Alpaca Markets API."""

import pandas as pd
from datetime import date, timedelta, datetime
from typing import List, Optional, Dict, Any
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestBarRequest
from alpaca.data.timeframe import TimeFrame
from sqlalchemy import text
from ..core.db import get_engine
from ..core.config import settings
from ..core.logging_config import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = get_logger(__name__)


class AlpacaDataClient:
    """Client for fetching historical market data from Alpaca."""

    def __init__(self, api_key: str, secret_key: str):
        """Initialize Alpaca data client with API credentials."""
        self.api_key = api_key
        self.secret_key = secret_key
        self.client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)

    def get_daily_bars(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Fetch daily OHLCV bars for a symbol.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            DataFrame with OHLCV data indexed by date
        """
        try:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_dt,
                end=end_dt,
                adjustment='all'
            )

            bars = self.client.get_stock_bars(request)

            if bars.df.empty:
                logger.warning("no_data_returned", symbol=symbol)
                return pd.DataFrame()

            df = bars.df

            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index(level=0, drop=True)

            df.index = df.index.date
            df.index.name = 'date'

            df = df[['open', 'high', 'low', 'close', 'volume']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

            df = df[~df.index.duplicated(keep='last')]
            df = df.sort_index()

            logger.debug("bars_retrieved", symbol=symbol, count=len(df))
            return df

        except Exception as e:
            logger.error("fetch_error", symbol=symbol, error=str(e))
            return pd.DataFrame()

    def get_previous_close(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent closing price and bar data for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with latest bar data or None if unavailable
        """
        try:
            request = StockLatestBarRequest(symbol_or_symbols=symbol)
            latest = self.client.get_stock_latest_bar(request)

            if symbol in latest:
                bar = latest[symbol]
                return {
                    'symbol': symbol,
                    'close': bar.close,
                    'high': bar.high,
                    'low': bar.low,
                    'open': bar.open,
                    'volume': bar.volume,
                    'timestamp': bar.timestamp.timestamp() * 1000 if bar.timestamp else None
                }
            return None

        except Exception as e:
            logger.error("previous_close_error", symbol=symbol, error=str(e))
            return None

def upsert_bars(symbol: str, bars: pd.DataFrame) -> None:
    """Insert or update daily OHLCV bars in the database."""
    if bars.empty:
        logger.warning("no_data_to_upsert", symbol=symbol)
        return

    eng = get_engine()
    
    with eng.begin() as c:
        for d, row in bars.iterrows():
            try:
                c.execute(text("""
                    INSERT INTO bars_daily(symbol, d, open, high, low, close, volume)
                    VALUES (:s, :d, :o, :h, :l, :c, :v)
                    ON CONFLICT (symbol, d) DO UPDATE SET 
                        open = :o, high = :h, low = :l, close = :c, volume = :v
                """), {
                    "s": symbol, 
                    "d": d, 
                    "o": float(row["Open"]), 
                    "h": float(row["High"]),
                    "l": float(row["Low"]), 
                    "c": float(row["Close"]), 
                    "v": int(row["Volume"])
                })
            except Exception as e:
                logger.error("upsert_error", symbol=symbol, date=str(d), error=str(e))
                continue

def check_data_exists_for_date(symbols: List[str], target_date: date) -> Dict[str, bool]:
    """
    Check which symbols already have data for a specific date.

    Args:
        symbols: List of symbols to check
        target_date: Date to check for existing data

    Returns:
        Dictionary mapping symbols to whether data exists
    """
    if not symbols:
        return {}

    eng = get_engine()

    symbol_placeholders = ','.join([f':symbol_{i}' for i in range(len(symbols))])
    query = text(f"""
        SELECT symbol, COUNT(*) as count
        FROM bars_daily
        WHERE symbol IN ({symbol_placeholders})
        AND d = :target_date
        GROUP BY symbol
    """)

    params = {"target_date": target_date}
    for i, symbol in enumerate(symbols):
        params[f'symbol_{i}'] = symbol

    try:
        with eng.begin() as conn:
            results = conn.execute(query, params).fetchall()

        existing_data = {symbol: False for symbol in symbols}
        for symbol, count in results:
            existing_data[symbol] = count > 0

        return existing_data

    except Exception as e:
        logger.error("check_existing_data_error", error=str(e))
        return {symbol: False for symbol in symbols}

def ingest_symbols(symbols: List[str], days: int = 365, target_date: date = None,
                  skip_existing: bool = True, max_workers: int = 10) -> None:
    """Ingest OHLCV data for multiple symbols using parallel processing."""
    if not symbols:
        logger.warning("no_symbols_provided")
        return

    api_key = settings.RT_ALPACA_API_KEY
    secret_key = settings.RT_ALPACA_SECRET_KEY
    if not api_key or not secret_key:
        raise ValueError("Alpaca API credentials not provided. Set RT_ALPACA_API_KEY and RT_ALPACA_SECRET_KEY in config.")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    if target_date is None:
        target_date = end_date
    
    symbols_to_process = symbols
    skipped_count = 0

    if skip_existing:
        logger.info("checking_existing_data", target_date=str(target_date))
        existing_data = check_data_exists_for_date(symbols, target_date)

        symbols_to_process = [symbol for symbol in symbols if not existing_data.get(symbol, False)]
        skipped_count = len(symbols) - len(symbols_to_process)

        if skipped_count > 0:
            logger.info("skipping_existing_symbols", count=skipped_count)

    if not symbols_to_process:
        logger.info("all_symbols_have_data", target_date=str(target_date))
        return
    
    # Alpaca has generous rate limits - use moderate parallelism
    # For small batches, use all available. For large batches, cap at 20 for stability
    if len(symbols_to_process) <= 20:
        max_workers = min(max_workers, len(symbols_to_process))
    else:
        max_workers = min(max_workers, 20, len(symbols_to_process))

    logger.info("starting_ingestion", start_date=str(start_date), end_date=str(end_date),
               symbol_count=len(symbols_to_process), max_workers=max_workers)
    
    success_count = 0
    error_count = 0
    completed_count = 0
    
    db_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(_fetch_symbol_data, symbol, api_key, secret_key, start_date, end_date): symbol
            for symbol in symbols_to_process
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            completed_count += 1
            
            try:
                symbol_result, df, success, error_msg = future.result()
                
                if success and not df.empty:
                    with db_lock:
                        upsert_bars(symbol_result, df)
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
    
    total_processed = success_count + error_count
    logger.info("ingestion_complete", success=success_count, errors=error_count,
               skipped=skipped_count, total_processed=total_processed)

def _fetch_symbol_data(symbol: str, api_key: str, secret_key: str, start_date: date, end_date: date) -> tuple:
    try:
        client = AlpacaDataClient(api_key, secret_key)
        df = client.get_daily_bars(symbol, start_date, end_date)

        if not df.empty:
            return (symbol, df, True, None)
        else:
            return (symbol, pd.DataFrame(), False, f"No data available for {symbol}")

    except Exception as e:
        return (symbol, pd.DataFrame(), False, str(e))

def get_latest_bar_date(symbol: str) -> Optional[date]:
    eng = get_engine()
    
    try:
        with eng.begin() as c:
            result = c.execute(text("""
                SELECT MAX(d) as max_date 
                FROM bars_daily 
                WHERE symbol = :symbol
            """), {"symbol": symbol}).first()
            
            if result and result.max_date:
                return result.max_date
            return None
            
    except Exception as e:
        logger.error("get_latest_bar_date_error", symbol=symbol, error=str(e))
        return None

def update_symbol_data(symbol: str, days_back: int = 30) -> bool:
    try:
        latest_date = get_latest_bar_date(symbol)

        if latest_date is None:
            logger.info("no_existing_data", symbol=symbol)
            ingest_symbols([symbol], days=365)
            return True

        today = date.today()
        start_date = max(latest_date + timedelta(days=1), today - timedelta(days=days_back))

        if start_date >= today:
            logger.debug("data_up_to_date", symbol=symbol)
            return True

        api_key = settings.RT_ALPACA_API_KEY
        secret_key = settings.RT_ALPACA_SECRET_KEY
        if not api_key or not secret_key:
            raise ValueError("Alpaca API credentials not provided")

        client = AlpacaDataClient(api_key, secret_key)
        df = client.get_daily_bars(symbol, start_date, today)

        if not df.empty:
            upsert_bars(symbol, df)
        else:
            logger.debug("no_new_data", symbol=symbol)

        return True

    except Exception as e:
        logger.error("update_symbol_error", symbol=symbol, error=str(e))
        return False

def refresh_spy_cache(days: int = 300) -> pd.Series:
    spy_symbol = settings.RT_MARKET_FILTER_SYMBOL

    api_key = settings.RT_ALPACA_API_KEY
    secret_key = settings.RT_ALPACA_SECRET_KEY
    if not api_key or not secret_key:
        raise ValueError("Alpaca API credentials not provided")

    client = AlpacaDataClient(api_key, secret_key)

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    df = client.get_daily_bars(spy_symbol, start_date, end_date)

    if df.empty:
        raise RuntimeError(f"{spy_symbol} download failed")

    upsert_bars(spy_symbol, df)

    close_series = df["Close"].copy()
    close_series.index = pd.to_datetime(close_series.index)

    return close_series

def validate_data_completeness(trade_date: date) -> bool:
    eng = get_engine()

    with eng.begin() as conn:
        bars_count = conn.execute(text("""
            SELECT COUNT(*) FROM bars_daily WHERE d = :d
        """), {"d": trade_date}).scalar_one()

        spy_data = conn.execute(text("""
            SELECT COUNT(*) FROM market_state WHERE d = :d
        """), {"d": trade_date}).scalar_one()

        if bars_count == 0:
            logger.warning("no_bars_data", trade_date=str(trade_date))
            return False

        if spy_data == 0:
            logger.warning("no_spy_market_state", trade_date=str(trade_date))
            return False

        logger.info("data_validation_passed", bars_count=bars_count)
        return True

def get_last_trading_session() -> date:
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT MAX(d) FROM bars_daily
        """)).scalar_one()
    
    return result
