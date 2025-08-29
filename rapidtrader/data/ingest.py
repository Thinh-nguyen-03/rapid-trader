"""
OHLCV data ingestion using Polygon.io API.
Clean, simple implementation focused on reliable data.
"""

import pandas as pd
from datetime import date, timedelta, datetime
from typing import List, Optional, Dict, Any
from polygon import RESTClient
from sqlalchemy import text
from ..core.db import get_engine
from ..core.config import settings
import time


class PolygonDataClient:
    """Polygon.io data client for OHLCV ingestion."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = RESTClient(api_key=api_key)
    
    def get_daily_bars(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Fetch daily OHLCV bars for a symbol from Polygon.io.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data indexed by date
        """
        try:
            print(f"Fetching {symbol} data from {start_date} to {end_date}")
            
            # Convert dates to strings
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Fetch aggregates (daily bars) from Polygon
            aggs = []
            for agg in self.client.list_aggs(
                ticker=symbol,
                multiplier=1,
                timespan="day",
                from_=start_str,
                to=end_str,
                adjusted=True,  # Use adjusted prices
                limit=50000
            ):
                aggs.append({
                    'timestamp': agg.timestamp,
                    'open': agg.open,
                    'high': agg.high, 
                    'low': agg.low,
                    'close': agg.close,
                    'volume': agg.volume,
                    'vwap': getattr(agg, 'vwap', None),
                    'transactions': getattr(agg, 'transactions', None)
                })
            
            if not aggs:
                print(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(aggs)
            
            # Convert timestamp to datetime
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
            
            # Set date as index and select OHLCV columns
            df = df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]
            
            # Rename columns to match expected format
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            # Remove any duplicate dates (keep last)
            df = df[~df.index.duplicated(keep='last')]
            
            # Sort by date
            df = df.sort_index()
            
            print(f"Retrieved {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_previous_close(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the previous trading day's close data for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with previous close data or None
        """
        try:
            prev_close = self.client.get_previous_close_agg(ticker=symbol)
            
            if prev_close and hasattr(prev_close, 'close'):
                return {
                    'symbol': symbol,
                    'close': prev_close.close,
                    'high': getattr(prev_close, 'high', None),
                    'low': getattr(prev_close, 'low', None),
                    'open': getattr(prev_close, 'open', None),
                    'volume': getattr(prev_close, 'volume', None),
                    'timestamp': getattr(prev_close, 'timestamp', None)
                }
            return None
            
        except Exception as e:
            print(f"Error fetching previous close for {symbol}: {e}")
            return None


def upsert_bars(symbol: str, bars: pd.DataFrame) -> None:
    """
    Insert or update daily OHLCV bars in the database.
    
    Args:
        symbol: Stock symbol
        bars: DataFrame with OHLCV data indexed by date
    """
    if bars.empty:
        print(f"No data to upsert for {symbol}")
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
                print(f"Error inserting data for {symbol} on {d}: {e}")
                continue
    
    print(f"Upserted {len(bars)} bars for {symbol}")


def ingest_symbols(symbols: List[str], days: int = 365) -> None:
    """
    Ingest OHLCV data for a list of symbols using Polygon.io.
    
    Args:
        symbols: List of stock symbols
        days: Number of days of historical data to fetch
    """
    if not symbols:
        print("No symbols provided for ingestion")
        return
    
    # Check API key
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        raise ValueError("Polygon API key not provided. Set RT_POLYGON_API_KEY in config.")
    
    # Initialize client
    client = PolygonDataClient(api_key)
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    print(f"Starting data ingestion for {len(symbols)} symbols from {start_date} to {end_date}")
    
    success_count = 0
    error_count = 0
    
    for i, symbol in enumerate(symbols, 1):
        try:
            print(f"[{i}/{len(symbols)}] Processing {symbol}")
            
            # Fetch data
            df = client.get_daily_bars(symbol, start_date, end_date)
            
            if not df.empty:
                # Store in database
                upsert_bars(symbol, df)
                success_count += 1
            else:
                print(f"No data available for {symbol}")
                error_count += 1
            
            # No rate limiting needed with Stocks Starter subscription (unlimited API calls)
            # Removed time.sleep(12) for faster data collection
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            error_count += 1
            continue
    
    print(f"\nIngestion complete: {success_count} successful, {error_count} errors")


def ingest_symbol(symbol: str, days: int = 365) -> bool:
    """
    Ingest OHLCV data for a single symbol.
    
    Args:
        symbol: Stock symbol
        days: Number of days of historical data to fetch
        
    Returns:
        True if successful, False otherwise
    """
    try:
        ingest_symbols([symbol], days)
        return True
    except Exception as e:
        print(f"Error ingesting {symbol}: {e}")
        return False


def get_latest_bar_date(symbol: str) -> Optional[date]:
    """
    Get the date of the most recent bar for a symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Date of most recent bar or None if no data
    """
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
        print(f"Error getting latest bar date for {symbol}: {e}")
        return None


def update_symbol_data(symbol: str, days_back: int = 30) -> bool:
    """
    Update data for a symbol, fetching only missing recent data.
    
    Args:
        symbol: Stock symbol
        days_back: How many days back to check for missing data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the latest date we have
        latest_date = get_latest_bar_date(symbol)
        
        if latest_date is None:
            # No data exists, fetch full history
            print(f"No existing data for {symbol}, fetching full history")
            return ingest_symbol(symbol, days=365)
        
        # Calculate start date for update
        today = date.today()
        start_date = max(latest_date + timedelta(days=1), today - timedelta(days=days_back))
        
        if start_date >= today:
            print(f"{symbol} data is up to date")
            return True
        
        # Fetch missing data
        api_key = settings.RT_POLYGON_API_KEY
        if not api_key:
            raise ValueError("Polygon API key not provided")
        
        client = PolygonDataClient(api_key)
        df = client.get_daily_bars(symbol, start_date, today)
        
        if not df.empty:
            upsert_bars(symbol, df)
            print(f"Updated {symbol} with {len(df)} new bars")
        else:
            print(f"No new data available for {symbol}")
        
        return True
        
    except Exception as e:
        print(f"Error updating {symbol}: {e}")
        return False


def refresh_spy_cache(days: int = 300) -> pd.Series:
    """
    Refresh SPY data for market filter calculations.
    
    Args:
        days: Number of days of SPY data to fetch
        
    Returns:
        SPY close price series
    """
    print("Refreshing SPY cache for market filter...")
    
    # Get SPY symbol from settings
    spy_symbol = settings.RT_MARKET_FILTER_SYMBOL
    
    # Fetch SPY data
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        raise ValueError("Polygon API key not provided")
    
    client = PolygonDataClient(api_key)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    df = client.get_daily_bars(spy_symbol, start_date, end_date)
    
    if df.empty:
        raise RuntimeError(f"{spy_symbol} download failed")
    
    # Store in database
    upsert_bars(spy_symbol, df)
    
    # Return close prices for market state calculations
    close_series = df["Close"].copy()
    close_series.index = pd.to_datetime(close_series.index)
    
    print(f"Refreshed {len(close_series)} days of {spy_symbol} data")
    return close_series
