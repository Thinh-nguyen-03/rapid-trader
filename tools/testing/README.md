# Testing and Development Tools

This directory contains development and testing scripts used during the setup and validation of the RapidTrader system.

## Scripts

### API Testing
- `test_polygon_api.py` - Comprehensive Polygon.io API integration tests
- `test_database_connection.py` - Database connectivity and schema validation tests  
- `verify_polygon_integration.py` - End-to-end Polygon integration verification

## Usage

These scripts are primarily used during development and can be run standalone to test specific components:

```bash
# Test Polygon API integration
python tools/testing/test_polygon_api.py

# Test database connectivity
python tools/testing/test_database_connection.py

# Verify full Polygon integration
python tools/testing/verify_polygon_integration.py
```

## Note

These scripts are development tools and are not part of the main trading system runtime.
