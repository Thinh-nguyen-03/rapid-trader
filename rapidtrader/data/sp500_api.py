"""Stock universe and sector classification management."""

import pandas as pd
from typing import List, Tuple, Dict, Optional
import requests
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from ..core.config import settings
from ..core.logging_config import get_logger
from ..core.retry import retry_api_call
from sqlalchemy import text
import time
from datetime import date, timedelta
from io import StringIO

logger = get_logger(__name__)


class iSharesClient:
    """Fetches S&P 500 constituents from iShares Core S&P 500 ETF (IVV)."""

    def __init__(self, url: str = None, timeout: int = None):
        self.url = url or settings.RT_SP500_ISHARES_URL
        self.timeout = timeout or settings.RT_SP500_REQUEST_TIMEOUT
        self.logger = logger

    @retry_api_call(max_attempts=3, min_wait=2.0, max_wait=30.0)
    def fetch_sp500_csv(self) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            self.logger.info("ishares_fetch_start", url=self.url)

            response = requests.get(self.url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            self.logger.info("ishares_fetch_success", bytes=len(response.content))
            return response.text

        except requests.exceptions.Timeout:
            self.logger.error("ishares_fetch_timeout", timeout=self.timeout)
            raise RuntimeError(f"iShares request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            self.logger.error("ishares_fetch_failed", error=str(e))
            raise RuntimeError(f"iShares API request failed: {e}")

    def parse_csv(self, csv_content: str) -> pd.DataFrame:
        try:
            lines = csv_content.split('\n')
            header_idx = None

            for idx, line in enumerate(lines):
                if 'Ticker' in line and 'Name' in line:
                    header_idx = idx
                    break

            if header_idx is None:
                raise ValueError("Could not find CSV header row with 'Ticker' column")

            df = pd.read_csv(StringIO('\n'.join(lines[header_idx:])))
            df.columns = df.columns.str.strip()

            column_mapping = {
                'Ticker': 'symbol',
                'Name': 'name',
                'Sector': 'sector',
                'Weight (%)': 'weight',
                'Asset Class': 'asset_class'
            }

            missing_cols = [col for col in column_mapping.keys() if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            df = df.rename(columns=column_mapping)
            df = df[df['asset_class'].str.upper() == 'EQUITY'].copy()

            df['symbol'] = df['symbol'].str.strip().str.upper()
            df = df[df['symbol'].notna() & (df['symbol'] != '') & (df['symbol'] != '-')]
            df['sector'] = df['sector'].fillna('Unknown').str.strip()
            df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0.0)

            df = df[['symbol', 'name', 'sector', 'weight']].copy()
            df = df.sort_values('weight', ascending=False).reset_index(drop=True)

            self.logger.info("ishares_csv_parsed", count=len(df))
            return df

        except Exception as e:
            self.logger.error("ishares_csv_parse_failed", error=str(e))
            raise ValueError(f"Failed to parse iShares CSV: {e}")

    def get_constituents(self) -> pd.DataFrame:
        csv_content = self.fetch_sp500_csv()
        df = self.parse_csv(csv_content)

        if df.empty:
            raise RuntimeError("iShares returned empty constituent list")

        if 'SPY' not in df['symbol'].values:
            self.logger.warning("spy_missing_from_ishares", action="adding_manually")
            spy_row = pd.DataFrame([{
                'symbol': 'SPY',
                'name': 'SPDR S&P 500 ETF Trust',
                'sector': 'ETF',
                'weight': 0.0
            }])
            df = pd.concat([spy_row, df], ignore_index=True)

        self.logger.info("ishares_constituents_loaded", count=len(df), top_symbol=df.iloc[0]['symbol'])
        return df

    def _ensure_cache_table(self):
        from ..core.db import get_engine

        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sp500_constituents (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT NOT NULL,
                    weight DECIMAL(10, 6),
                    source TEXT DEFAULT 'ishares',
                    last_updated DATE NOT NULL DEFAULT CURRENT_DATE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sp500_last_updated
                ON sp500_constituents(last_updated)
            """))

    def _check_cache_freshness(self) -> bool:
        from ..core.db import get_engine

        self._ensure_cache_table()

        ttl_days = settings.RT_SP500_CACHE_TTL_DAYS
        stale_threshold = date.today() - timedelta(days=ttl_days)

        eng = get_engine()
        with eng.begin() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM sp500_constituents")).scalar()

            if count == 0:
                self.logger.info("sp500_cache_empty")
                return False

            last_update = conn.execute(text("SELECT MAX(last_updated) FROM sp500_constituents")).scalar()

            if last_update is None or last_update <= stale_threshold:
                self.logger.info("sp500_cache_stale", last_update=last_update, threshold=stale_threshold)
                return False

            self.logger.info("sp500_cache_fresh", last_update=last_update, count=count)
            return True

    def _load_from_cache(self) -> pd.DataFrame:
        from ..core.db import get_engine

        eng = get_engine()
        with eng.begin() as conn:
            results = conn.execute(text("""
                SELECT symbol, name, sector, weight
                FROM sp500_constituents
                ORDER BY weight DESC
            """)).fetchall()

        df = pd.DataFrame(results, columns=['symbol', 'name', 'sector', 'weight'])
        self.logger.info("sp500_cache_loaded", count=len(df))
        return df

    def upsert_to_cache(self, df: pd.DataFrame):
        from ..core.db import get_engine

        self._ensure_cache_table()

        eng = get_engine()
        with eng.begin() as conn:
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO sp500_constituents
                    (symbol, name, sector, weight, source, last_updated)
                    VALUES (:symbol, :name, :sector, :weight, 'ishares', CURRENT_DATE)
                    ON CONFLICT (symbol) DO UPDATE SET
                        name = EXCLUDED.name,
                        sector = EXCLUDED.sector,
                        weight = EXCLUDED.weight,
                        source = EXCLUDED.source,
                        last_updated = EXCLUDED.last_updated
                """), {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "sector": row["sector"],
                    "weight": float(row["weight"])
                })

        self.logger.info("sp500_cache_updated", count=len(df))

    def get_constituents_with_cache(self, force_refresh: bool = False) -> pd.DataFrame:
        """Get S&P 500 constituents with TTL-based caching."""
        if not force_refresh and self._check_cache_freshness():
            return self._load_from_cache()

        self.logger.info("sp500_fetching_fresh_data")
        df = self.get_constituents()
        self.upsert_to_cache(df)
        return df


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

            logger.info("stocks_fetched", count=len(df))
            return df[['symbol', 'name', 'sector']]

        except Exception as e:
            logger.error("alpaca_api_failed", error=str(e))
            raise RuntimeError(f"Alpaca API request failed: {e}")
    
    def _apply_sector_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        from ..core.db import get_engine
        from datetime import date, timedelta
        
        eng = get_engine()
        
        self._ensure_sector_cache_table(eng)
        
        with eng.begin() as conn:
            active_symbols = conn.execute(text("""
                SELECT symbol FROM symbols WHERE is_active = true
            """)).fetchall()
            active_symbol_set = {row[0] for row in active_symbols}
        
        symbols_to_check = [s for s in df['symbol'].tolist() if s in active_symbol_set]
        symbols_needing_update = self._check_sector_cache_status(eng, symbols_to_check)
        
        if symbols_needing_update:
            logger.info("auto_updating_sectors", count=len(symbols_needing_update))
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
        
        cached_count = len(sector_map)
        total_count = len(df)
        coverage_pct = cached_count/total_count*100 if total_count > 0 else 0

        logger.info("sector_cache_coverage", cached=cached_count, total=total_count, pct=coverage_pct)
        
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
            logger.warning("large_batch_truncated", original=len(symbols), truncated_to=50)
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
                            logger.warning("fmp_api_failed", symbol=symbol, error=str(e))

                    if sector == 'Unknown' and (sic_description or sic_code):
                        sector = self._map_sic_to_sector(sic_description, str(sic_code) if sic_code else None)
                
                with eng.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO sector_cache (symbol, sector, sic_description, sic_code, last_updated)
                        VALUES (:symbol, :sector, :sic_description, :sic_code, :last_updated)
                        ON CONFLICT (symbol) DO UPDATE SET
                            sector = EXCLUDED.sector,
                            sic_description = EXCLUDED.sic_description,
                            sic_code = EXCLUDED.sic_code,
                            last_updated = EXCLUDED.last_updated
                    """), {
                        "symbol": symbol,
                        "sector": sector,
                        "sic_description": sic_description,
                        "sic_code": sic_code,
                        "last_updated": date.today()
                    })
                
                updated_count += 1
                
                time.sleep(0.12)
                
            except Exception as e:
                logger.warning("sector_update_failed", symbol=symbol, error=str(e))
                
                with eng.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO sector_cache (symbol, sector, sic_description, sic_code, last_updated)
                        VALUES (:symbol, 'Unknown', '', NULL, :last_updated)
                        ON CONFLICT (symbol) DO UPDATE SET
                            last_updated = :last_updated
                    """), {"symbol": symbol, "last_updated": date.today()})
                
                continue

        logger.info("sectors_auto_updated", count=updated_count)
    
    
    def _map_sic_to_sector(self, sic_description: str, sic_code: str = None) -> str:
        """Map SIC code/description to GICS sector using official SIC database."""
        
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
        
        return 'Unknown'
    
    def _get_sector_from_sic_database(self, sic_code: int) -> str:
        """Get sector from SIC database using exact SIC code lookup."""
        from ..core.db import get_engine

        eng = get_engine()
        conn = eng.connect()
        try:
            result = conn.execute(text("""
                SELECT gics_sector
                FROM sic_codes
                WHERE sic_code = :sic_code
            """), {"sic_code": sic_code}).fetchone()

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

        eng = get_engine()
        conn = eng.connect()
        try:
            # Try exact description match first
            result = conn.execute(text("""
                SELECT gics_sector
                FROM sic_codes
                WHERE UPPER(sic_description) = UPPER(:description)
            """), {"description": sic_description}).fetchone()

            if result:
                return result[0]

            sic_lower = sic_description.lower()

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
                fuzzy_result = conn.execute(text("""
                    SELECT gics_sector, sic_description
                    FROM sic_codes
                    WHERE UPPER(sic_description) LIKE '%' || :term || '%'
                    LIMIT 3
                """), {"term": term}).fetchall()

                if fuzzy_result:
                    return fuzzy_result[0][0]

            return 'Unknown'
        finally:
            conn.close()

def _get_hardcoded_fallback_symbols() -> List[Tuple[str, str]]:
    """Fallback list of ~100 major S&P 500 symbols when iShares is unavailable."""
    fallback_map = {
        # Technology
        'AAPL': 'Technology', 'MSFT': 'Technology', 'NVDA': 'Technology',
        'AVGO': 'Technology', 'ORCL': 'Technology', 'AMD': 'Technology',
        'CRM': 'Technology', 'ADBE': 'Technology', 'CSCO': 'Technology',
        'ACN': 'Technology', 'TXN': 'Technology', 'QCOM': 'Technology',
        'INTU': 'Technology', 'IBM': 'Technology', 'NOW': 'Technology',

        # Communication Services
        'GOOGL': 'Communication Services', 'GOOG': 'Communication Services',
        'META': 'Communication Services', 'NFLX': 'Communication Services',
        'DIS': 'Communication Services', 'CMCSA': 'Communication Services',
        'T': 'Communication Services', 'VZ': 'Communication Services',

        # Consumer Discretionary
        'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary',
        'HD': 'Consumer Discretionary', 'NKE': 'Consumer Discretionary',
        'MCD': 'Consumer Discretionary', 'LOW': 'Consumer Discretionary',
        'BKNG': 'Consumer Discretionary', 'SBUX': 'Consumer Discretionary',
        'TJX': 'Consumer Discretionary',

        # Consumer Staples
        'WMT': 'Consumer Staples', 'PG': 'Consumer Staples',
        'COST': 'Consumer Staples', 'KO': 'Consumer Staples',
        'PEP': 'Consumer Staples', 'PM': 'Consumer Staples',
        'MO': 'Consumer Staples', 'MDLZ': 'Consumer Staples',
        'CL': 'Consumer Staples',

        # Financials
        'JPM': 'Financials', 'V': 'Financials', 'MA': 'Financials',
        'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
        'MS': 'Financials', 'BLK': 'Financials', 'SPGI': 'Financials',
        'C': 'Financials', 'SCHW': 'Financials', 'AXP': 'Financials',
        'CB': 'Financials', 'PNC': 'Financials', 'USB': 'Financials',
        'CME': 'Financials', 'ICE': 'Financials', 'MCO': 'Financials',
        'BRK.B': 'Financials', 'AON': 'Financials',

        # Healthcare
        'UNH': 'Healthcare', 'JNJ': 'Healthcare', 'LLY': 'Healthcare',
        'ABBV': 'Healthcare', 'MRK': 'Healthcare', 'TMO': 'Healthcare',
        'ABT': 'Healthcare', 'DHR': 'Healthcare', 'PFE': 'Healthcare',
        'BMY': 'Healthcare', 'AMGN': 'Healthcare', 'GILD': 'Healthcare',
        'VRTX': 'Healthcare', 'CI': 'Healthcare', 'ELV': 'Healthcare',
        'CVS': 'Healthcare', 'ISRG': 'Healthcare', 'REGN': 'Healthcare',
        'ZTS': 'Healthcare', 'SYK': 'Healthcare', 'BSX': 'Healthcare',

        # Industrials
        'CAT': 'Industrials', 'GE': 'Industrials', 'RTX': 'Industrials',
        'HON': 'Industrials', 'UNP': 'Industrials', 'LMT': 'Industrials',
        'ADP': 'Industrials', 'DE': 'Industrials', 'BA': 'Industrials',
        'NOC': 'Industrials', 'WM': 'Industrials', 'ITW': 'Industrials',
        'EMR': 'Industrials', 'CSX': 'Industrials', 'NSC': 'Industrials',
        'FDX': 'Industrials', 'UPS': 'Industrials',

        # Energy
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
        'SLB': 'Energy', 'EOG': 'Energy', 'MPC': 'Energy',

        # Materials
        'LIN': 'Materials', 'APD': 'Materials', 'ECL': 'Materials',
        'SHW': 'Materials', 'FCX': 'Materials', 'NEM': 'Materials',

        # Real Estate
        'PLD': 'Real Estate', 'AMT': 'Real Estate', 'EQIX': 'Real Estate',
        'CCI': 'Real Estate', 'PSA': 'Real Estate',

        # Utilities
        'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
        'D': 'Utilities', 'AEP': 'Utilities',

        # ETF (for market filter)
        'SPY': 'ETF'
    }

    return list(fallback_map.items())


def get_sp500_symbols(force_refresh: bool = False) -> List[Tuple[str, str]]:
    """
    Get S&P 500 symbols and sectors.

    Primary: iShares IVV ETF (cached, configurable TTL)
    Fallback: Hardcoded ~100 major constituents
    """
    source_mode = settings.RT_SP500_SOURCE.lower()

    if source_mode != "hardcoded":
        try:
            logger.info("sp500_fetch_start", source="ishares", force_refresh=force_refresh)

            ishares_client = iSharesClient()
            df = ishares_client.get_constituents_with_cache(force_refresh=force_refresh)

            result = [(row['symbol'], row['sector']) for _, row in df.iterrows()]

            logger.info("sp500_symbols_loaded", source="ishares", count=len(result))
            return result

        except Exception as e:
            logger.warning("ishares_fetch_failed_using_fallback", error=str(e))

    logger.info("sp500_fetch_start", source="hardcoded_fallback")
    result = _get_hardcoded_fallback_symbols()
    logger.info("sp500_symbols_loaded", source="hardcoded_fallback", count=len(result))
    return result

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