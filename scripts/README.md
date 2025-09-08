# Scripts Directory

**Essential maintenance and diagnostic scripts for RapidTrader**

## **Current Scripts**

### **Database Maintenance**

#### **`update_database.py`** - *Unified Database Maintenance*
**Purpose**: Single script for all database update operations
```bash
# Complete database rebuild
python scripts/update_database.py --all

# Quick maintenance update
python scripts/update_database.py --quick

# Individual components
python scripts/update_database.py --symbols   # Update S&P 500 symbols
python scripts/update_database.py --sectors   # Update sector classifications  
python scripts/update_database.py --sic       # Update SIC codes from SEC
python scripts/update_database.py --cleanup   # Clean up orphaned sector_cache entries
```
---

### **Database Setup**

#### **`apply_db_extensions.py`** - *Database Schema Extensions*
**Purpose**: Apply kill switch and reliability features to database
```bash
python scripts/apply_db_extensions.py
```
**Creates**: `system_state` and `exec_fills` tables

#### **`setup_db_extensions.sql`** - *SQL Schema Definitions*
**Purpose**: SQL definitions for reliability features

**Usage**: Applied automatically by `apply_db_extensions.py`

---

### **Diagnostic Tools**

#### **`diagnose_db_connection.py`** - *Database Connection Diagnostics*
**Purpose**: Comprehensive database connection troubleshooting
```bash
python scripts/diagnose_db_connection.py
```
**Tests**: DNS resolution, connectivity, authentication, query execution

#### **`test_alpaca_connection.py`** - *Alpaca API Testing*
**Purpose**: Test Alpaca paper trading API connection and permissions
```bash
python scripts/test_alpaca_connection.py
```
**Tests**: API authentication, account info, market data access

#### **`cleanup_sector_cache.py`** - *Sector Cache Cleanup*
**Purpose**: Remove orphaned symbols from sector_cache table
```bash
python scripts/cleanup_sector_cache.py
```
**Removes**: Symbols not in active symbols table (prevents sector_cache bloat)

---

## **Usage Patterns**

### **Initial Setup**
```bash
# 1. Setup database extensions
python scripts/apply_db_extensions.py

# 2. Populate database with symbols and sectors
python scripts/update_database.py --all
```

### **Regular Maintenance**
```bash
# Weekly: Quick update of symbols and sectors
python scripts/update_database.py --quick

# Monthly: Full refresh including SIC codes
python scripts/update_database.py --all
```

### **Troubleshooting**
```bash
# Database connection issues
python scripts/diagnose_db_connection.py

# Alpaca API issues  
python scripts/test_alpaca_connection.py

# Sector cache has too many symbols
python scripts/cleanup_sector_cache.py
```