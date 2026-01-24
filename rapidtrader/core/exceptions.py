"""Custom exception classes for RapidTrader.

Provides a hierarchy of exceptions for proper error handling and debugging.
"""


class RapidTraderError(Exception):
    """Base exception for all RapidTrader errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# Data Errors
class DataError(RapidTraderError):
    """Base class for data-related errors."""
    pass


class DataFetchError(DataError):
    """Error fetching data from external source."""

    def __init__(self, source: str, symbol: str | None = None, message: str = ""):
        details = {"source": source}
        if symbol:
            details["symbol"] = symbol
        super().__init__(
            message=message or f"Failed to fetch data from {source}",
            details=details
        )


class DataValidationError(DataError):
    """Error validating data integrity."""

    def __init__(self, field: str, value: any, reason: str):
        super().__init__(
            message=f"Validation failed for {field}: {reason}",
            details={"field": field, "value": str(value), "reason": reason}
        )


class InsufficientDataError(DataError):
    """Not enough data points for calculation."""

    def __init__(self, required: int, available: int, context: str = ""):
        super().__init__(
            message=f"Insufficient data: need {required}, have {available}",
            details={"required": required, "available": available, "context": context}
        )


# API Errors
class APIError(RapidTraderError):
    """Base class for API-related errors."""
    pass


class AlpacaAPIError(APIError):
    """Error from Alpaca Markets API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(
            message=f"Alpaca API error: {message}",
            details={"status_code": status_code} if status_code else {}
        )


class RateLimitError(APIError):
    """API rate limit exceeded."""

    def __init__(self, api_name: str, retry_after: int | None = None):
        super().__init__(
            message=f"Rate limit exceeded for {api_name}",
            details={"api": api_name, "retry_after": retry_after}
        )


# Database Errors
class DatabaseError(RapidTraderError):
    """Base class for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Database connection error."""

    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message=message)


class QueryError(DatabaseError):
    """Database query execution error."""

    def __init__(self, query: str, error: str):
        super().__init__(
            message=f"Query execution failed: {error}",
            details={"query_preview": query[:200] if len(query) > 200 else query}
        )


# Trading Errors
class TradingError(RapidTraderError):
    """Base class for trading-related errors."""
    pass


class RiskLimitExceeded(TradingError):
    """Trading blocked due to risk limit."""

    def __init__(self, limit_type: str, current_value: float, limit_value: float):
        super().__init__(
            message=f"Risk limit exceeded: {limit_type}",
            details={
                "limit_type": limit_type,
                "current_value": current_value,
                "limit_value": limit_value
            }
        )


class KillSwitchActive(TradingError):
    """Trading blocked due to kill switch activation."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Kill switch active: {reason}",
            details={"reason": reason}
        )


class InsufficientFunds(TradingError):
    """Insufficient funds for trade."""

    def __init__(self, required: float, available: float):
        super().__init__(
            message=f"Insufficient funds: need ${required:,.2f}, have ${available:,.2f}",
            details={"required": required, "available": available}
        )


class InvalidOrderError(TradingError):
    """Invalid order parameters."""

    def __init__(self, symbol: str, reason: str):
        super().__init__(
            message=f"Invalid order for {symbol}: {reason}",
            details={"symbol": symbol, "reason": reason}
        )


# Configuration Errors
class ConfigurationError(RapidTraderError):
    """Configuration error."""

    def __init__(self, setting: str, message: str):
        super().__init__(
            message=f"Configuration error for {setting}: {message}",
            details={"setting": setting}
        )


class MissingCredentialsError(ConfigurationError):
    """Missing required API credentials."""

    def __init__(self, service: str):
        super().__init__(
            setting=f"{service}_credentials",
            message=f"Missing credentials for {service}"
        )
