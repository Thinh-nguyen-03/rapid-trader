"""
S&P 500 data fetching from Wikipedia and other sources.
Clean, simple implementation focused on reliable data.
"""

import requests
import pandas as pd
from typing import List, Tuple, Optional
from ..core.config import settings
import io

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

def get_sp500_symbols(source: str = "wikipedia") -> List[Tuple[str, str]]:
    """
    Get S&P 500 symbols and sectors from various sources.
    
    Args:
        source: Data source ("wikipedia" or "fmp")
        
    Returns:
        List of (symbol, sector) tuples
    """
    if source.lower() == "wikipedia":
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
        api_key = settings.RT_FMP_API_KEY
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
        raise ValueError(f"Unsupported source: {source}. Use 'wikipedia' or 'fmp'")

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