import os
import requests
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

class HolidayService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('RT_POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("Polygon API key is required. Set RT_POLYGON_API_KEY environment variable.")
            
        self.base_url = "https://api.polygon.io/v1/marketstatus/upcoming"
        
        # Cache for upcoming holidays (refresh every 24 hours)
        self._upcoming_holidays_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[datetime] = None
    
    def _is_cache_valid(self) -> bool:
        if not self._cache_timestamp or not self._upcoming_holidays_cache:
            return False
        return datetime.now() - self._cache_timestamp < timedelta(hours=24)
    
    def get_upcoming_holidays(self, force_refresh: bool = False) -> List[Dict]:
        if not force_refresh and self._is_cache_valid():
            return self._upcoming_holidays_cache
        
        try:
            params = {'apikey': self.api_key}
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                holidays = []
                
                if isinstance(data, list):
                    for holiday in data:
                        if holiday.get('status') == 'closed':
                            holidays.append({
                                'date': holiday.get('date'),
                                'name': holiday.get('name'),
                                'status': holiday.get('status'),
                                'exchange': holiday.get('exchange')
                            })
                
                self._upcoming_holidays_cache = holidays
                self._cache_timestamp = datetime.now()
                
                return holidays
                
            else:
                error_msg = f"API request failed with status {response.status_code}"
                if response.status_code == 401:
                    error_msg += " - Check your Polygon API key"
                elif response.status_code == 403:
                    error_msg += " - API key may not have access to market status endpoint"
                print(f"WARNING: {error_msg}")
                return []
                
        except Exception as e:
            print(f"WARNING: Failed to fetch holidays from Polygon API: {e}")
            return []
    
    def get_next_holiday(self) -> Optional[Dict]:
        holidays = self.get_upcoming_holidays()
        if not holidays:
            return None
        
        today = date.today()
        upcoming = []
        
        for holiday in holidays:
            try:
                holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d').date()
                if holiday_date >= today:
                    upcoming.append((holiday_date, holiday))
            except ValueError:
                continue
        
        if not upcoming:
            return None
        
        upcoming.sort(key=lambda x: x[0])
        return upcoming[0][1]
    
    def get_holidays_in_range(self, start_date: date, end_date: date) -> List[Dict]:
        holidays = self.get_upcoming_holidays()
        filtered = []
        
        for holiday in holidays:
            try:
                holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d').date()
                if start_date <= holiday_date <= end_date:
                    filtered.append(holiday)
            except ValueError:
                continue
        
        return filtered
    
    def is_trading_day(self, check_date: date) -> bool:
        if check_date.weekday() >= 5:
            return False
        
        holidays = self.get_upcoming_holidays()
        for holiday in holidays:
            try:
                holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d').date()
                if holiday_date == check_date:
                    return False
            except ValueError:
                continue
        
        return True

_holiday_service = None

def get_holiday_service(api_key: Optional[str] = None) -> HolidayService:
    global _holiday_service
    if _holiday_service is None:
        _holiday_service = HolidayService(api_key=api_key)
    return _holiday_service

def get_upcoming_holidays(api_key: Optional[str] = None) -> List[Dict]:
    service = get_holiday_service(api_key)
    return service.get_upcoming_holidays()

def get_next_holiday(api_key: Optional[str] = None) -> Optional[Dict]:
    service = get_holiday_service(api_key)
    return service.get_next_holiday()

def is_trading_day(check_date: date, api_key: Optional[str] = None) -> bool:
    service = get_holiday_service(api_key)
    return service.is_trading_day(check_date)