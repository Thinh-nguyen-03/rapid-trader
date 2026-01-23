"""Stock universe and sector classification management."""

import pandas as pd
from typing import List, Tuple, Dict
import requests
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from ..core.config import settings
from sqlalchemy import text
import time


class CompanyDataClient:
    """Client for fetching company metadata from Alpaca and FMP APIs."""

    def __init__(self, fmp_api_key: str = None, alpaca_api_key: str = None, alpaca_secret_key: str = None):
        """
        Initialize company data client.

        Args:
            fmp_api_key: Financial Modeling Prep API key (optional)
            alpaca_api_key: Alpaca API key for asset listings
            alpaca_secret_key: Alpaca secret key
        """
        self.fmp_api_key = fmp_api_key
        self.alpaca_api_key = alpaca_api_key
        self.alpaca_secret_key = alpaca_secret_key
        if alpaca_api_key and alpaca_secret_key:
            self.alpaca_client = TradingClient(api_key=alpaca_api_key, secret_key=alpaca_secret_key)
        else:
            self.alpaca_client = None
    
    def get_sp500_constituents(self) -> pd.DataFrame:
        """
        Fetch tradable US equities from Alpaca with sector classifications.

        Returns:
            DataFrame with columns: symbol, name, sector
        """
        try:
            if not self.alpaca_client:
                raise ValueError("Alpaca client not initialized")

            request = GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=AssetStatus.ACTIVE)
            assets = self.alpaca_client.get_all_assets(request)

            if not assets:
                raise ValueError("No assets received from Alpaca")

            ticker_data = []
            for asset in assets:
                if asset.tradable and asset.fractionable:
                    ticker_data.append({
                        'symbol': asset.symbol,
                        'name': asset.name,
                        'exchange': asset.exchange,
                        'tradable': asset.tradable
                    })

            df = pd.DataFrame(ticker_data)
            df['symbol'] = df['symbol'].str.strip().str.upper()
            df = df.dropna(subset=['symbol'])
            df = df[df['symbol'] != '']

            df = self._apply_sector_mapping(df)

            print(f"Successfully fetched {len(df)} stocks from Alpaca")
            return df[['symbol', 'name', 'sector']]

        except Exception as e:
            raise RuntimeError(f"Alpaca API request failed: {e}")
    
    def _apply_sector_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        from ..core.db import get_engine
        from datetime import date, timedelta
        
        eng = get_engine()
        
        self._ensure_sector_cache_table(eng)
        
        # Only auto-update sectors for symbols that are in the active symbols table
        # This prevents sector_cache from being populated with non-S&P500 symbols
        with eng.begin() as conn:
            active_symbols = conn.execute(text("""
                SELECT symbol FROM symbols WHERE is_active = true
            """)).fetchall()
            active_symbol_set = {row[0] for row in active_symbols}
        
        # Filter to only include active symbols for auto-update
        symbols_to_check = [s for s in df['symbol'].tolist() if s in active_symbol_set]
        
        # Check cache coverage and freshness for active symbols only
        symbols_needing_update = self._check_sector_cache_status(eng, symbols_to_check)
        
        # Auto-update missing or stale sectors (only for active symbols)
        if symbols_needing_update:
            print(f"Auto-updating sector data for {len(symbols_needing_update)} active symbols...")
            self._update_sectors_automatically(symbols_needing_update)
        
        # Now get cached sector data
        with eng.begin() as conn:
            cached_sectors = conn.execute(text("""
                SELECT symbol, sector 
                FROM sector_cache 
                WHERE symbol = ANY(:symbols)
            """), {"symbols": df['symbol'].tolist()}).fetchall()
        
        sector_map = {row[0]: row[1] for row in cached_sectors}
        df['sector'] = df['symbol'].map(sector_map).fillna('Unknown')
        
        # Report final coverage
        cached_count = len(sector_map)
        total_count = len(df)
        coverage_pct = cached_count/total_count*100 if total_count > 0 else 0
        
        print(f"Sector cache coverage: {cached_count}/{total_count} symbols ({coverage_pct:.1f}%)")
        
        return df
    
    def _ensure_sector_cache_table(self, eng):
        """Create sector cache table if it doesn't exist."""
        with eng.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sector_cache (
                    symbol TEXT PRIMARY KEY,
                    sector TEXT NOT NULL,
                    sic_description TEXT,
                    sic_code INTEGER,
                    last_updated DATE NOT NULL DEFAULT CURRENT_DATE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
    
    def _check_sector_cache_status(self, eng, symbols: List[str]) -> List[str]:
        """Check which symbols need sector updates."""
        from datetime import date, timedelta
        
        # Consider data stale after 30 days
        stale_threshold = date.today() - timedelta(days=30)
        
        with eng.begin() as conn:
            # Get symbols that are missing or stale
            existing_fresh = conn.execute(text("""
                SELECT symbol FROM sector_cache 
                WHERE symbol = ANY(:symbols)
                AND last_updated > :threshold
            """), {
                "symbols": symbols,
                "threshold": stale_threshold
            }).fetchall()
        
        fresh_symbols = {row[0] for row in existing_fresh}
        symbols_needing_update = [s for s in symbols if s not in fresh_symbols]
        
        return symbols_needing_update
    
    def _update_sectors_automatically(self, symbols: List[str]):
        """
        Update sector classifications for symbols using FMP API.

        Args:
            symbols: List of symbols to update (limited to 50 to prevent delays)
        """
        from ..core.db import get_engine
        from datetime import date

        if not symbols:
            return

        if len(symbols) > 50:
            print(f"Large batch ({len(symbols)} symbols) - updating first 50 automatically")
            print(f"Run 'python scripts/update_sector_cache.py' to update remaining symbols")
            symbols = symbols[:50]

        eng = get_engine()
        updated_count = 0

        for symbol in symbols:
            try:
                if symbol == 'SPY':
                    sector = 'ETF'
                    sic_description = 'Investment Fund'
                    sic_code = None
                else:
                    sector = 'Unknown'
                    sic_description = ''
                    sic_code = None

                    if self.fmp_api_key:
                        try:
                            url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}"
                            params = {'apikey': self.fmp_api_key}
                            response = requests.get(url, params=params, timeout=10)

                            if response.status_code == 200:
                                data = response.json()
                                if data and len(data) > 0:
                                    profile = data[0]
                                    sector = profile.get('sector', 'Unknown')
                                    sic_description = profile.get('industry', '')
                        except Exception as e:
                            print(f"Warning: FMP API request failed for {symbol}: {e}")

                    if sector == 'Unknown' and (sic_description or sic_code):
                        sector = self._map_sic_to_sector(sic_description, str(sic_code) if sic_code else None)
                
                # Upsert into database (include sic_code for consistency)
                with eng.begin() as conn:
                    # Escape single quotes in text fields
                    symbol_escaped = symbol.replace("'", "''")
                    sector_escaped = sector.replace("'", "''")
                    sic_description_escaped = sic_description.replace("'", "''")
                    sic_code_value = sic_code if sic_code is not None else "NULL"
                    
                    conn.execute(text(f"""
                        INSERT INTO sector_cache (symbol, sector, sic_description, sic_code, last_updated)
                        VALUES ('{symbol_escaped}', '{sector_escaped}', '{sic_description_escaped}', {sic_code_value}, '{date.today()}')
                        ON CONFLICT (symbol) DO UPDATE SET
                            sector = '{sector_escaped}',
                            sic_description = '{sic_description_escaped}',
                            sic_code = {sic_code_value},
                            last_updated = '{date.today()}'
                    """))
                
                updated_count += 1
                
                # Rate limiting
                time.sleep(0.12)  # ~8 requests per second
                
            except Exception as e:
                print(f"Warning: Could not update sector for {symbol}: {e}")
                
                # Store as Unknown if we can't fetch data
                with eng.begin() as conn:
                    # Escape single quotes in symbol
                    symbol_escaped = symbol.replace("'", "''")
                    
                    conn.execute(text(f"""
                        INSERT INTO sector_cache (symbol, sector, sic_description, sic_code, last_updated)
                        VALUES ('{symbol_escaped}', 'Unknown', '', NULL, '{date.today()}')
                        ON CONFLICT (symbol) DO UPDATE SET
                            last_updated = '{date.today()}'
                    """))
                
                continue
        
        print(f"Auto-updated {updated_count} sector records")
    
    
    def _map_sic_to_sector(self, sic_description: str, sic_code: str = None) -> str:
        """Map SIC code/description to GICS sector using official SIC database."""
        
        # First try exact SIC code lookup (most accurate)
        if sic_code:
            try:
                sic_num = int(sic_code)
                sector = self._get_sector_from_sic_database(sic_num)
                if sector != 'Unknown':
                    return sector
            except (ValueError, TypeError):
                pass
        
        # Try fuzzy description matching from SIC database
        if sic_description:
            sector = self._get_sector_from_sic_fuzzy(sic_description)
            if sector != 'Unknown':
                return sector
        
        # Final fallback
        return 'Unknown'
    
    def _get_sector_from_sic_database(self, sic_code: int) -> str:
        """Get sector from SIC database using exact SIC code lookup."""
        from ..core.db import get_engine
        
        # Create a fresh connection to avoid prepared statement conflicts
        eng = get_engine()
        conn = eng.connect()
        try:
            # Use raw SQL to avoid prepared statement conflicts with Supabase
            result = conn.execute(text(f"""
                SELECT gics_sector 
                FROM sic_codes 
                WHERE sic_code = {sic_code}
            """)).fetchone()
            
            if result:
                return result[0]
            
            return 'Unknown'
        finally:
            conn.close()
    
    def _get_sector_from_sic_fuzzy(self, sic_description: str) -> str:
        """Get sector from SIC database using fuzzy description matching."""
        from ..core.db import get_engine
        
        if not sic_description:
            return 'Unknown'
        
        # Create a fresh connection to avoid prepared statement conflicts
        eng = get_engine()
        conn = eng.connect()
        try:
            # Escape single quotes in description
            description_escaped = sic_description.replace("'", "''")
            
            # Try exact description match first
            result = conn.execute(text(f"""
                SELECT gics_sector 
                FROM sic_codes 
                WHERE UPPER(sic_description) = UPPER('{description_escaped}')
            """)).fetchone()
            
            if result:
                return result[0]
            
            # Try fuzzy matching with key terms from description
            sic_lower = sic_description.lower()
            
            # Extract key terms for better matching
            key_terms = []
            if 'services' in sic_lower:
                key_terms.append('SERVICES')
            if 'business' in sic_lower:
                key_terms.append('BUSINESS')
            if 'electronic' in sic_lower:
                key_terms.append('ELECTRONIC')
            if 'computer' in sic_lower:
                key_terms.append('COMPUTER')
            if 'semiconductor' in sic_lower:
                key_terms.append('SEMICONDUCTOR')
            if 'prepackaged' in sic_lower:
                key_terms.append('PREPACKAGED')
            if 'software' in sic_lower:
                key_terms.append('SOFTWARE')
            
            # Try matching with key terms
            for term in key_terms:
                term_escaped = term.replace("'", "''")
                fuzzy_result = conn.execute(text(f"""
                    SELECT gics_sector, sic_description
                    FROM sic_codes 
                    WHERE UPPER(sic_description) LIKE '%{term_escaped}%'
                    LIMIT 3
                """)).fetchall()
                
                if fuzzy_result:
                    # Return the first match
                    return fuzzy_result[0][0]
            
            return 'Unknown'
        finally:
            conn.close()

def get_sp500_symbols() -> List[Tuple[str, str]]:
    """
    Get S&P 500 symbols and sectors from Alpaca with dynamic sector mapping using FMP.

    Returns:
        List of (symbol, sector) tuples
    """
    alpaca_api_key = settings.RT_ALPACA_API_KEY
    alpaca_secret_key = settings.RT_ALPACA_SECRET_KEY
    fmp_api_key = settings.RT_FMP_API_KEY

    if not alpaca_api_key or not alpaca_secret_key:
        raise ValueError("Alpaca API credentials not provided. Set RT_ALPACA_API_KEY and RT_ALPACA_SECRET_KEY in config.")

    client = CompanyDataClient(
        fmp_api_key=fmp_api_key,
        alpaca_api_key=alpaca_api_key,
        alpaca_secret_key=alpaca_secret_key
    )

    try:
        # Get all US stocks from Alpaca - this will now fetch sectors dynamically
        df = client.get_sp500_constituents()

        # For now, we'll use a curated list of major S&P 500 symbols
        # In production, you'd want to get the actual S&P 500 list from a reliable source
        major_sp500_symbols = {
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'UNH',
            'JNJ', 'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'ABBV', 'PFE', 'AVGO', 'KO',
            'PEP', 'COST', 'TMO', 'WMT', 'BAC', 'NFLX', 'DIS', 'ABT', 'ADBE', 'CRM', 'ACN',
            'VZ', 'CMCSA', 'ORCL', 'NKE', 'DHR', 'NEE', 'TXN', 'LIN', 'PM', 'RTX', 'QCOM',
            'HON', 'UNP', 'T', 'LOW', 'SPGI', 'INTU', 'IBM', 'GS', 'CAT', 'AXP', 'AMD',
            'BLK', 'DE', 'LMT', 'ELV', 'BKNG', 'SYK', 'GE', 'MDLZ', 'ADP', 'TJX', 'GILD',
            'MMM', 'CVS', 'VRTX', 'C', 'MO', 'SCHW', 'ZTS', 'CB', 'CI', 'NOW', 'ISRG',
            'BSX', 'ETN', 'PLD', 'DUK', 'SO', 'PYPL', 'WM', 'ITW', 'CL', 'EMR', 'AON',
            'CSX', 'EQIX', 'PNC', 'NOC', 'SHW', 'CME', 'USB', 'WFC', 'MS', 'MCO', 'FDX',
            'NSC', 'APD', 'ECL', 'COP', 'REGN', 'FCX', 'ICE', 'SPY'  # SPY for market filter
        }

        # Filter to major S&P 500 symbols that exist in Alpaca data
        available_symbols = set(df['symbol'].str.upper())
        valid_symbols = major_sp500_symbols.intersection(available_symbols)

        sp500_df = df[df['symbol'].isin(valid_symbols)].copy()

        # Convert to list of tuples
        result = []
        for _, row in sp500_df.iterrows():
            symbol = str(row['symbol']).strip()
            sector = str(row.get('sector', 'Unknown')).strip()

            if symbol and symbol != 'nan':
                result.append((symbol, sector))

        # Ensure SPY is included (needed for market filter)
        spy_present = any(symbol == 'SPY' for symbol, _ in result)
        if not spy_present:
            result.append(('SPY', 'ETF'))
            print("Added SPY (market filter symbol) to symbol list")

        print(f"Using Alpaca data for {len(result)} major S&P 500 symbols with dynamic sectors")
        return result

    except Exception as e:
        raise RuntimeError(f"Error fetching S&P 500 symbols from Alpaca: {e}")

def map_sector_name(sector: str) -> str:
    """
    Standardize sector names for consistency.
    
    Args:
        sector: Raw sector name
        
    Returns:
        Standardized sector name
    """
    if not sector or sector.lower() in ['', 'null', 'none', 'unknown']:
        return 'Unknown'
    
    # Common sector mappings
    sector_map = {
        'Information Technology': 'Technology',
        'Health Care': 'Healthcare',
        'Consumer Discretionary': 'Consumer Discretionary', 
        'Financials': 'Financials',
        'Communication Services': 'Communication Services',
        'Industrials': 'Industrials',
        'Consumer Staples': 'Consumer Staples',
        'Energy': 'Energy',
        'Utilities': 'Utilities',
        'Real Estate': 'Real Estate',
        'Materials': 'Materials'
    }
    
    return sector_map.get(sector, sector)