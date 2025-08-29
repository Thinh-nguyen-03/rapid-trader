# Data ingestion and management module

from .ingest import (
    PolygonDataClient,
    ingest_symbols,
    ingest_symbol,
    upsert_bars,
    refresh_spy_cache,
    get_latest_bar_date,
    update_symbol_data
)

from .sp500_api import (
    PolygonClient,
    get_sp500_symbols,
    fetch_sp500_from_wikipedia,
    map_sector_name,
    FMPClient  # Legacy support
)

__all__ = [
    # Data ingestion
    'PolygonDataClient',
    'ingest_symbols',
    'ingest_symbol', 
    'upsert_bars',
    'refresh_spy_cache',
    'get_latest_bar_date',
    'update_symbol_data',
    
    # Symbol management
    'PolygonClient',
    'get_sp500_symbols',
    'fetch_sp500_from_wikipedia',
    'map_sector_name',
    'FMPClient'
]