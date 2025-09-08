"""Data utility functions for gap detection and trading session management."""

from datetime import date, datetime, timedelta
from rapidtrader.core.holidays import get_holiday_service
from rapidtrader.data.ingest import get_last_trading_session

def is_trading_day(check_date: date) -> bool:
    if check_date.weekday() >= 5:
        return False
    
    try:
        holiday_service = get_holiday_service()
        return holiday_service.is_trading_day(check_date)
    except Exception as e:
        print(f"WARNING: Holiday service unavailable ({e}), using simple weekday check")
        return check_date.weekday() < 5

def get_expected_latest_trading_date() -> date:
    today = date.today()
    current_time = datetime.now().time()
    
    market_close_time = datetime.strptime("16:00", "%H:%M").time()
    
    if current_time < market_close_time:
        candidate_date = today - timedelta(days=1)
    else:
        candidate_date = today
    
    while not is_trading_day(candidate_date):
        candidate_date -= timedelta(days=1)
    
    return candidate_date

def get_missing_trading_days() -> list[date]:
    try:
        last_data_date = get_last_trading_session()
        expected_date = get_expected_latest_trading_date()
        
        if not last_data_date:
            print("INFO: No existing data found - will ingest latest trading day")
            return [expected_date]
        
        missing_days = []
        current_date = last_data_date + timedelta(days=1)
        
        while current_date <= expected_date:
            if is_trading_day(current_date):
                missing_days.append(current_date)
                print(f"INFO: Missing data for trading day: {current_date}")
            current_date += timedelta(days=1)
        
        if not missing_days:
            print(f"INFO: Data is current (latest: {last_data_date}) - no gaps detected")
        else:
            print(f"INFO: Found {len(missing_days)} missing trading days: {[str(d) for d in missing_days]}")
        
        return missing_days
        
    except Exception as e:
        print(f"WARNING: Could not check for missing data ({e}) - will ingest latest day to be safe")
        expected_date = get_expected_latest_trading_date()
        return [expected_date]

def should_run_data_ingestion() -> bool:
    missing_days = get_missing_trading_days()
    return len(missing_days) > 0