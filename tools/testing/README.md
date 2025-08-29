# Testing and Development Tools

This directory contains essential testing scripts for validating core RapidTrader system components.

## Scripts

### Core System Validation
- `test_database_connection.py` - Database connectivity and schema validation tests
- `test_indicator_accuracy.py` - Technical indicator calculation accuracy validation

## Usage

These scripts validate critical system components and can be run standalone:

```bash
# Test database connectivity and schema
python tools/testing/test_database_connection.py

# Validate indicator calculations against real market data
python tools/testing/test_indicator_accuracy.py
```

## Note

These scripts are development tools and are not part of the main trading system runtime.
