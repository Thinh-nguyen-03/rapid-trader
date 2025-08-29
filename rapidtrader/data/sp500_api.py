"""
S&P 500 data fetching from Polygon.io and fallback sources.
Clean, simple implementation focused on reliable data.
"""

import requests
import pandas as pd
from typing import List, Tuple, Optional, Dict, Any
from polygon import RESTClient
from ..core.config import settings
import io
import time

class PolygonClient:
    """Polygon.io API client for S&P 500 and market data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = RESTClient(api_key=api_key)
    
    def get_sp500_constituents(self) -> pd.DataFrame:
        """
        Fetch current S&P 500 constituents from Polygon.io.
        
        Returns:
            DataFrame with S&P 500 company data including symbol, name, and sector
        """
        try:
            print("Fetching S&P 500 constituents from Polygon.io...")
            
            # Get all active US stocks
            tickers = []
            for ticker in self.client.list_tickers(
                market="stocks",
                active=True,
                limit=1000
            ):
                tickers.append(ticker)
            
            if not tickers:
                raise ValueError("No ticker data received from Polygon.io")
            
            # Convert to DataFrame
            ticker_data = []
            for ticker in tickers:
                ticker_data.append({
                    'symbol': ticker.ticker,
                    'name': getattr(ticker, 'name', ''),
                    'market': getattr(ticker, 'market', ''),
                    'type': getattr(ticker, 'type', ''),
                    'active': getattr(ticker, 'active', True),
                    'currency_name': getattr(ticker, 'currency_name', 'USD'),
                    'locale': getattr(ticker, 'locale', 'us')
                })
            
            df = pd.DataFrame(ticker_data)
            
            # Filter for US stocks only and common shares (CS)
            df = df[
                (df['market'] == 'stocks') &
                (df['active'] == True) &
                (df['locale'] == 'us') &
                (df['currency_name'] == 'USD') &
                (df['type'] == 'CS')  # Common Stock
            ]
            
            # Clean symbols
            df['symbol'] = df['symbol'].str.strip().str.upper()
            df = df.dropna(subset=['symbol'])
            df = df[df['symbol'] != '']
            
            # Add sector information (will be filled from ticker details)
            df['sector'] = 'Unknown'
            
            # Fetch detailed info for major symbols to get sector data
            # For efficiency, we'll fetch details for a subset and map common sectors
            major_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'SPY']
            sector_mapping = {}
            
            for symbol in major_symbols:
                if symbol in df['symbol'].values:
                    try:
                        details = self.client.get_ticker_details(symbol)
                        if hasattr(details, 'sic_description') and details.sic_description:
                            sector_mapping[symbol] = self._map_sic_to_sector(details.sic_description)
                        time.sleep(0.1)  # Rate limiting
                    except Exception as e:
                        print(f"Could not fetch details for {symbol}: {e}")
                        continue
            
            # Apply sector mapping where available
            for symbol, sector in sector_mapping.items():
                df.loc[df['symbol'] == symbol, 'sector'] = sector
            
            # Use standard sector mapping for known symbols
            df = self._apply_standard_sector_mapping(df)
            
            print(f"Successfully fetched {len(df)} stocks from Polygon.io")
            return df[['symbol', 'name', 'sector']]
            
        except Exception as e:
            raise RuntimeError(f"Polygon.io API request failed: {e}")
    
    def _map_sic_to_sector(self, sic_description: str) -> str:
        """Map SIC description to standard sector names."""
        if not sic_description:
            return 'Unknown'
        
        sic_lower = sic_description.lower()
        
        if any(term in sic_lower for term in ['software', 'computer', 'technology', 'internet', 'data processing']):
            return 'Technology'
        elif any(term in sic_lower for term in ['pharmaceutical', 'biotechnology', 'medical', 'healthcare', 'drug']):
            return 'Healthcare'
        elif any(term in sic_lower for term in ['bank', 'financial', 'insurance', 'investment', 'credit']):
            return 'Financials'
        elif any(term in sic_lower for term in ['retail', 'consumer', 'restaurant', 'food']):
            return 'Consumer Discretionary'
        elif any(term in sic_lower for term in ['oil', 'gas', 'petroleum', 'energy']):
            return 'Energy'
        elif any(term in sic_lower for term in ['manufacturing', 'industrial', 'machinery', 'aerospace']):
            return 'Industrials'
        elif any(term in sic_lower for term in ['utility', 'electric', 'power']):
            return 'Utilities'
        elif any(term in sic_lower for term in ['real estate', 'reit']):
            return 'Real Estate'
        elif any(term in sic_lower for term in ['mining', 'materials', 'chemical', 'metals']):
            return 'Materials'
        elif any(term in sic_lower for term in ['communication', 'media', 'telecommunications']):
            return 'Communication Services'
        else:
            return 'Unknown'
    
    def _apply_standard_sector_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply standard sector mapping for well-known symbols."""
        
        # Technology
        tech_symbols = ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'NVDA', 'ADBE', 'CRM', 'NFLX', 'ORCL', 'IBM', 'INTC', 'AMD', 'QCOM']
        df.loc[df['symbol'].isin(tech_symbols), 'sector'] = 'Technology'
        
        # Healthcare
        healthcare_symbols = ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'DHR', 'ABT', 'LLY', 'BMY']
        df.loc[df['symbol'].isin(healthcare_symbols), 'sector'] = 'Healthcare'
        
        # Financials
        financial_symbols = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'BLK', 'SCHW', 'CB']
        df.loc[df['symbol'].isin(financial_symbols), 'sector'] = 'Financials'
        
        # Consumer Discretionary
        consumer_disc_symbols = ['AMZN', 'TSLA', 'HD', 'MCD', 'DIS', 'NKE', 'SBUX', 'TJX', 'LOW', 'CMG']
        df.loc[df['symbol'].isin(consumer_disc_symbols), 'sector'] = 'Consumer Discretionary'
        
        # Energy
        energy_symbols = ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC', 'KMI', 'OKE']
        df.loc[df['symbol'].isin(energy_symbols), 'sector'] = 'Energy'
        
        # Industrials
        industrial_symbols = ['BA', 'CAT', 'HON', 'UPS', 'LMT', 'RTX', 'GE', 'MMM', 'FDX', 'WM']
        df.loc[df['symbol'].isin(industrial_symbols), 'sector'] = 'Industrials'
        
        # Consumer Staples
        consumer_staples_symbols = ['PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'KMB', 'GIS', 'K', 'HSY']
        df.loc[df['symbol'].isin(consumer_staples_symbols), 'sector'] = 'Consumer Staples'
        
        # Utilities
        utility_symbols = ['NEE', 'DUK', 'SO', 'AEP', 'EXC', 'XEL', 'D', 'PPL', 'PCG', 'EIX']
        df.loc[df['symbol'].isin(utility_symbols), 'sector'] = 'Utilities'
        
        # Real Estate
        real_estate_symbols = ['AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'WELL', 'DLR', 'O', 'SBAC', 'EQR']
        df.loc[df['symbol'].isin(real_estate_symbols), 'sector'] = 'Real Estate'
        
        # Materials
        materials_symbols = ['LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'DOW', 'DD', 'PPG', 'VMC']
        df.loc[df['symbol'].isin(materials_symbols), 'sector'] = 'Materials'
        
        # Communication Services
        comm_symbols = ['GOOGL', 'GOOG', 'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'CHTR', 'TMUS']
        df.loc[df['symbol'].isin(comm_symbols), 'sector'] = 'Communication Services'
        
        # ETF
        df.loc[df['symbol'] == 'SPY', 'sector'] = 'ETF'
        
        return df

class FMPClient:
    """Financial Modeling Prep API client for S&P 500 data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    def get_sp500_constituents(self) -> pd.DataFrame:
        """
        Fetch current S&P 500 constituents from FMP.
        
        Returns:
            DataFrame with S&P 500 company data
        """
        url = f"{self.base_url}/sp500_constituent"
        params = {"apikey": self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                raise ValueError("No S&P 500 data received from FMP")
            
            df = pd.DataFrame(data)
            
            # Standardize column names
            if 'symbol' not in df.columns:
                raise ValueError("Symbol column missing from FMP response")
            
            # Clean and validate data
            df['symbol'] = df['symbol'].str.strip().str.upper()
            df = df.dropna(subset=['symbol'])
            df = df[df['symbol'] != '']
            
            print(f"Successfully fetched {len(df)} S&P 500 constituents from FMP")
            return df
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"FMP API request failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Error processing FMP data: {e}")

def fetch_sp500_from_wikipedia() -> pd.DataFrame:
    """
    Fetch S&P 500 constituents from Wikipedia.
    
    Returns:
        DataFrame with S&P 500 company data including symbol and sector
    """
    print("Fetching S&P 500 constituents from Wikipedia...")
    
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    try:
        # Set headers to avoid being blocked by Wikipedia
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # First fetch the HTML content with proper headers
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Read tables from the HTML content
        tables = pd.read_html(io.StringIO(response.text), header=0)
        
        # The first table contains the current S&P 500 constituents
        sp500_table = tables[0]
        
        # Clean up column names (Wikipedia tables can have inconsistent naming)
        sp500_table.columns = sp500_table.columns.str.strip()
        
        # Map common column name variations
        column_mapping = {}
        for col in sp500_table.columns:
            col_lower = col.lower()
            if 'symbol' in col_lower or 'ticker' in col_lower:
                column_mapping[col] = 'symbol'
            elif 'sector' in col_lower or 'gics sector' in col_lower:
                column_mapping[col] = 'sector'
            elif 'security' in col_lower or 'company' in col_lower:
                column_mapping[col] = 'name'
        
        sp500_table = sp500_table.rename(columns=column_mapping)
        
        # Ensure we have the required columns
        if 'symbol' not in sp500_table.columns:
            raise ValueError("Could not find symbol column in Wikipedia table")
        
        if 'sector' not in sp500_table.columns:
            raise ValueError("Could not find sector column in Wikipedia table")
        
        # Clean the data
        sp500_table['symbol'] = sp500_table['symbol'].str.strip().str.upper()
        sp500_table['sector'] = sp500_table['sector'].str.strip()
        
        # Remove any rows with missing symbols
        sp500_table = sp500_table.dropna(subset=['symbol'])
        sp500_table = sp500_table[sp500_table['symbol'] != '']
        
        print(f"Successfully fetched {len(sp500_table)} S&P 500 constituents from Wikipedia")
        return sp500_table
        
    except Exception as e:
        raise RuntimeError(f"Failed to fetch S&P 500 data from Wikipedia: {e}")

def get_sp500_symbols(source: str = "polygon") -> List[Tuple[str, str]]:
    """
    Get S&P 500 symbols and sectors from various sources.
    
    Args:
        source: Data source ("polygon", "wikipedia", or "fmp")
        
    Returns:
        List of (symbol, sector) tuples
    """
    if source.lower() == "polygon":
        # Primary source: Polygon.io (requires API key)
        api_key = settings.RT_POLYGON_API_KEY
        if not api_key:
            raise ValueError("Polygon API key not provided. Set RT_POLYGON_API_KEY in config.")
        
        client = PolygonClient(api_key)
        
        # For S&P 500, we'll get a filtered subset of stocks
        # Since Polygon doesn't have a direct S&P 500 endpoint, 
        # we'll use the Wikipedia list as a filter and get the data from Polygon
        try:
            # First get S&P 500 symbols from Wikipedia
            wiki_df = fetch_sp500_from_wikipedia()
            sp500_symbols = set(wiki_df['symbol'].str.upper())
            
            # Then get all stock data from Polygon
            polygon_df = client.get_sp500_constituents()
            
            # Filter Polygon data to S&P 500 symbols
            sp500_df = polygon_df[polygon_df['symbol'].isin(sp500_symbols)].copy()
            
            # If we have good coverage, use Polygon data
            if len(sp500_df) >= len(sp500_symbols) * 0.8:  # 80% coverage threshold
                print(f"Using Polygon.io data for {len(sp500_df)} S&P 500 symbols")
                result = []
                for _, row in sp500_df.iterrows():
                    symbol = str(row['symbol']).strip()
                    sector = str(row.get('sector', 'Unknown')).strip()
                    
                    if symbol and symbol != 'nan':
                        result.append((symbol, sector))
            else:
                # Fallback to Wikipedia with some Polygon sector enrichment
                print(f"Limited Polygon coverage ({len(sp500_df)}/{len(sp500_symbols)}), falling back to Wikipedia with Polygon enrichment")
                result = []
                for _, row in wiki_df.iterrows():
                    symbol = str(row['symbol']).strip().upper()
                    
                    # Try to get sector from Polygon data if available
                    polygon_match = sp500_df[sp500_df['symbol'] == symbol]
                    if not polygon_match.empty and polygon_match.iloc[0]['sector'] != 'Unknown':
                        sector = polygon_match.iloc[0]['sector']
                    else:
                        sector = str(row.get('sector', 'Unknown')).strip()
                    
                    if symbol and symbol != 'nan':
                        result.append((symbol, sector))
            
        except Exception as e:
            print(f"Error with Polygon.io: {e}, falling back to Wikipedia")
            # Fallback to Wikipedia
            df = fetch_sp500_from_wikipedia()
            result = []
            for _, row in df.iterrows():
                symbol = str(row['symbol']).strip()
                sector = str(row.get('sector', 'Unknown')).strip()
                
                if symbol and symbol != 'nan':
                    result.append((symbol, sector))
        
        # Ensure SPY is included (needed for market filter)
        spy_present = any(symbol == 'SPY' for symbol, _ in result)
        if not spy_present:
            result.append(('SPY', 'ETF'))
            print("Added SPY (market filter symbol) to symbol list")
        
        return result
        
    elif source.lower() == "wikipedia":
        # Fetch from Wikipedia
        df = fetch_sp500_from_wikipedia()
        
        # Convert to list of tuples
        result = []
        for _, row in df.iterrows():
            symbol = str(row['symbol']).strip()
            sector = str(row.get('sector', 'Unknown')).strip()
            
            if symbol and symbol != 'nan':
                result.append((symbol, sector))
        
        # Ensure SPY is included (needed for market filter)
        spy_present = any(symbol == 'SPY' for symbol, _ in result)
        if not spy_present:
            result.append(('SPY', 'ETF'))
            print("Added SPY (market filter symbol) to symbol list")
        
        return result
        
    elif source.lower() == "fmp":
        # Legacy FMP support (requires API key)
        api_key = getattr(settings, 'RT_FMP_API_KEY', None)
        if not api_key:
            raise ValueError("FMP API key not provided. Set RT_FMP_API_KEY in config.")
        
        client = FMPClient(api_key)
        df = client.get_sp500_constituents()
        
        # Convert to list of tuples
        result = []
        for _, row in df.iterrows():
            symbol = str(row['symbol']).strip()
            sector = str(row.get('sector', 'Unknown')).strip()
            
            if symbol and symbol != 'nan':
                result.append((symbol, sector))
        
        # Ensure SPY is included (needed for market filter)
        spy_present = any(symbol == 'SPY' for symbol, _ in result)
        if not spy_present:
            result.append(('SPY', 'ETF'))
            print("Added SPY (market filter symbol) to symbol list")
        
        return result
    
    else:
        raise ValueError(f"Unsupported source: {source}. Use 'polygon', 'wikipedia', or 'fmp'")

def map_sector_name(sector: str) -> str:
    """
    Standardize sector names for consistency.
    
    Args:
        sector: Raw sector name from FMP
        
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