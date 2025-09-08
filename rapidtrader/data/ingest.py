""" OHLCV data ingestion."""

import pandas as pd
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from polygon import RESTClient
from sqlalchemy import text
from ..core.db import get_engine
from ..core.config import settings
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class PolygonDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = RESTClient(api_key=api_key)
    
    def get_daily_bars(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        try:
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
            
            df = pd.DataFrame(aggs)
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
            df = df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df[~df.index.duplicated(keep='last')]
            df = df.sort_index()
            
            print(f"Retrieved {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_previous_close(self, symbol: str) -> Optional[Dict[str, Any]]:
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
    """Insert or update daily OHLCV bars in the database."""
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

def check_data_exists_for_date(symbols: List[str], target_date: date) -> Dict[str, bool]:
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
        print(f"ERROR: Failed to check existing data: {e}")
        return {symbol: False for symbol in symbols}

def ingest_symbols(symbols: List[str], days: int = 365, target_date: date = None, 
                  skip_existing: bool = True, max_workers: int = 10) -> None:
    """Ingest OHLCV data for multiple symbols using parallel processing."""
    if not symbols:
        print("No symbols provided for ingestion")
        return
    
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        raise ValueError("Polygon API key not provided. Set RT_POLYGON_API_KEY in config.")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    if target_date is None:
        target_date = end_date
    
    symbols_to_process = symbols
    skipped_count = 0
    
    if skip_existing:
        print(f"INFO: Checking for existing data for {target_date}")
        existing_data = check_data_exists_for_date(symbols, target_date)
        
        symbols_to_process = [symbol for symbol in symbols if not existing_data.get(symbol, False)]
        skipped_count = len(symbols) - len(symbols_to_process)
        
        if skipped_count > 0:
            print(f"SUCCESS: Skipping symbols that already have data for {target_date}")
    
    if not symbols_to_process:
        print(f"SUCCESS: All symbols already have data for {target_date}")
        return
    
    if settings.RT_POLYGON_RATE_LIMIT == 0:
        # For small batches, use all available. For large batches, cap at 50 for stability
        if len(symbols_to_process) <= 20:
            max_workers = min(max_workers, len(symbols_to_process))
        else:
            max_workers = min(max_workers, 50, len(symbols_to_process))
    else:
        max_workers = min(max_workers, 5, len(symbols_to_process))
    
    print(f"Starting data ingestion from {start_date} to {end_date}")
    
    success_count = 0
    error_count = 0
    completed_count = 0
    
    db_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(_fetch_symbol_data, symbol, api_key, start_date, end_date): symbol 
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
    print(f"\nSUCCESS: Ingestion complete: {success_count} successful, {error_count} errors")
    if skipped_count > 0:
        print(f"INFO: {skipped_count} symbols skipped (data already exists), {total_processed} symbols processed")

def _fetch_symbol_data(symbol: str, api_key: str, start_date: date, end_date: date) -> tuple:
    try:
        client = PolygonDataClient(api_key)
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
        print(f"Error getting latest bar date for {symbol}: {e}")
        return None

def update_symbol_data(symbol: str, days_back: int = 30) -> bool:
    try:
        latest_date = get_latest_bar_date(symbol)
        
        if latest_date is None:
            print(f"No existing data for {symbol}, fetching full history")
            ingest_symbols([symbol], days=365)
            return True
        
        today = date.today()
        start_date = max(latest_date + timedelta(days=1), today - timedelta(days=days_back))
        
        if start_date >= today:
            print(f"{symbol} data is up to date")
            return True
        
        api_key = settings.RT_POLYGON_API_KEY
        if not api_key:
            raise ValueError("Polygon API key not provided")
        
        client = PolygonDataClient(api_key)
        df = client.get_daily_bars(symbol, start_date, today)
        
        if not df.empty:
            upsert_bars(symbol, df)
        else:
            print(f"No new data available for {symbol}")
        
        return True
        
    except Exception as e:
        print(f"Error updating {symbol}: {e}")
        return False

def refresh_spy_cache(days: int = 300) -> pd.Series:
    spy_symbol = settings.RT_MARKET_FILTER_SYMBOL
    
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        raise ValueError("Polygon API key not provided")
    
    client = PolygonDataClient(api_key)
    
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
            print(f"INFO: No bars data found for {trade_date}")
            return False
            
        if spy_data == 0:
            print(f"INFO: No SPY market state found for {trade_date}")
            return False
            
        print(f"INFO: Data validation passed: {bars_count} symbols, SPY state OK")
        return True

def get_last_trading_session() -> date:
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT MAX(d) FROM bars_daily
        """)).scalar_one()
    
    return result
