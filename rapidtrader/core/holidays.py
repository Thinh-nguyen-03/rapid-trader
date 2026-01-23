"""Market holiday and trading day utilities using pandas_market_calendars."""

import pandas as pd
import pandas_market_calendars as mcal
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

class HolidayService:
    """Service for checking market holidays and trading days."""

    def __init__(self, exchange: str = 'NYSE'):
        """
        Initialize holiday service.

        Args:
            exchange: Exchange calendar to use (default: NYSE)
        """
        self.exchange = exchange
        self.calendar = mcal.get_calendar(exchange)
        self._holidays_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[datetime] = None

    def _is_cache_valid(self) -> bool:
        """Check if cached holidays are still valid (< 24 hours old)."""
        if not self._cache_timestamp or not self._holidays_cache:
            return False
        return datetime.now() - self._cache_timestamp < timedelta(hours=24)

    def get_upcoming_holidays(self, force_refresh: bool = False, days_ahead: int = 365) -> List[Dict]:
        """
        Get upcoming market holidays.

        Args:
            force_refresh: Force refresh of cached data
            days_ahead: Number of days to look ahead (default: 365)

        Returns:
            List of holiday dictionaries with date and name
        """
        if not force_refresh and self._is_cache_valid():
            return self._holidays_cache

        try:
            today = datetime.now()
            end_date = today + timedelta(days=days_ahead)

            # Get valid trading days in the range
            schedule = self.calendar.schedule(start_date=today, end_date=end_date)

            # Get all days in range and find non-trading weekdays (holidays)
            all_days = set(pd.date_range(today, end_date, freq='B'))  # Business days only
            trading_days = set(schedule.index)
            holidays = all_days - trading_days

            # Format as list of dictionaries
            holiday_list = [
                {
                    'date': holiday_date.strftime('%Y-%m-%d'),
                    'name': self._get_holiday_name(holiday_date),
                    'status': 'closed',
                    'exchange': self.exchange
                }
                for holiday_date in sorted(holidays)
            ]

            self._holidays_cache = holiday_list
            self._cache_timestamp = datetime.now()

            return holiday_list

        except Exception as e:
            print(f"WARNING: Failed to fetch holidays: {e}")
            return []

    def _get_holiday_name(self, holiday_date: datetime) -> str:
        """Get holiday name for a given date."""
        # Common US market holidays
        holiday_names = {
            (1, 1): "New Year's Day",
            (1, 15): "Martin Luther King Jr. Day",
            (2, 19): "Presidents Day",
            (5, 27): "Memorial Day",
            (6, 19): "Juneteenth",
            (7, 4): "Independence Day",
            (9, 2): "Labor Day",
            (11, 28): "Thanksgiving",
            (12, 25): "Christmas"
        }

        key = (holiday_date.month, holiday_date.day)
        return holiday_names.get(key, "Market Holiday")

    def get_next_holiday(self) -> Optional[Dict]:
        """Get the next upcoming market holiday."""
        holidays = self.get_upcoming_holidays()
        if not holidays:
            return None

        today = date.today()
        for holiday in holidays:
            try:
                holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d').date()
                if holiday_date >= today:
                    return holiday
            except ValueError:
                continue

        return None

    def get_holidays_in_range(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Get holidays within a date range.

        Args:
            start_date: Range start date
            end_date: Range end date

        Returns:
            List of holidays in the range
        """
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
        """
        Check if a given date is a trading day.

        Args:
            check_date: Date to check

        Returns:
            True if trading day, False otherwise
        """
        # Check if weekend
        if check_date.weekday() >= 5:
            return False

        # Check if holiday
        holidays = self.get_upcoming_holidays()
        for holiday in holidays:
            try:
                holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d').date()
                if holiday_date == check_date:
                    return False
            except ValueError:
                continue

        return True


# Global singleton instance
_holiday_service = None


def get_holiday_service(exchange: str = 'NYSE') -> HolidayService:
    """Get or create the global holiday service instance."""
    global _holiday_service
    if _holiday_service is None:
        _holiday_service = HolidayService(exchange=exchange)
    return _holiday_service


def get_upcoming_holidays(exchange: str = 'NYSE') -> List[Dict]:
    """Convenience function to get upcoming holidays."""
    service = get_holiday_service(exchange)
    return service.get_upcoming_holidays()


def get_next_holiday(exchange: str = 'NYSE') -> Optional[Dict]:
    """Convenience function to get next holiday."""
    service = get_holiday_service(exchange)
    return service.get_next_holiday()


def is_trading_day(check_date: date, exchange: str = 'NYSE') -> bool:
    """Convenience function to check if a date is a trading day."""
    service = get_holiday_service(exchange)
    return service.is_trading_day(check_date)
