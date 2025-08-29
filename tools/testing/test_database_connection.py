#!/usr/bin/env python3
"""
Test database connection for RapidTrader.
This script verifies database connectivity and shows connection details.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rapidtrader.core.config import settings
from rapidtrader.core.db import get_engine
from sqlalchemy import text
import traceback


def test_database_connection():
    """Test database connection and show details."""
    print("🔍 Testing Database Connection")
    print("=" * 50)
    
    # Show configuration
    db_url = settings.RT_DB_URL
    print(f"Database URL: {db_url}")
    
    # Parse URL to show connection details
    if "://" in db_url:
        try:
            # Parse basic components
            protocol = db_url.split("://")[0]
            rest = db_url.split("://")[1]
            
            if "@" in rest:
                auth_part = rest.split("@")[0]
                host_part = rest.split("@")[1]
                
                if ":" in auth_part:
                    username = auth_part.split(":")[0]
                    password = auth_part.split(":")[1]
                else:
                    username = auth_part
                    password = ""
                
                if "/" in host_part:
                    host_port = host_part.split("/")[0]
                    database = host_part.split("/")[1]
                else:
                    host_port = host_part
                    database = ""
                
                if ":" in host_port:
                    host = host_port.split(":")[0]
                    port = host_port.split(":")[1]
                else:
                    host = host_port
                    port = "5432"  # Default PostgreSQL port
            else:
                host_part = rest
                username = ""
                password = ""
                if "/" in host_part:
                    host_port = host_part.split("/")[0]
                    database = host_part.split("/")[1]
                else:
                    host_port = host_part
                    database = ""
                
                if ":" in host_port:
                    host = host_port.split(":")[0]
                    port = host_port.split(":")[1]
                else:
                    host = host_port
                    port = "5432"
            
            print(f"\nConnection Details:")
            print(f"  Protocol: {protocol}")
            print(f"  Host: {host}")
            print(f"  Port: {port}")
            print(f"  Database: {database}")
            print(f"  Username: {username}")
            print(f"  Password: {'*' * len(password) if password else 'Not set'}")
            
        except Exception as e:
            print(f"Could not parse URL: {e}")
    
    print("\n" + "─" * 50)
    
    # Test connection
    try:
        print("Testing connection...")
        engine = get_engine()
        
        with engine.connect() as conn:
            print("✅ Successfully connected to database!")
            
            # Test basic query
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            if result and result[0] == 1:
                print("✅ Basic query test passed")
            
            # Check database version
            try:
                version_result = conn.execute(text("SELECT version()")).fetchone()
                if version_result:
                    version = version_result[0]
                    print(f"✅ Database version: {version.split(',')[0]}")
            except Exception as e:
                print(f"⚠️  Could not get database version: {e}")
            
            # Check if tables exist
            print(f"\n📋 Checking RapidTrader tables...")
            
            tables_to_check = [
                'symbols',
                'bars_daily', 
                'signals_daily',
                'orders_eod',
                'positions',
                'market_state',
                'symbol_events'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table in tables_to_check:
                try:
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    """)).fetchone()
                    
                    if result and result[0] > 0:
                        existing_tables.append(table)
                        
                        # Get row count
                        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                        row_count = count_result[0] if count_result else 0
                        print(f"  ✅ {table}: {row_count} rows")
                    else:
                        missing_tables.append(table)
                        print(f"  ❌ {table}: Missing")
                        
                except Exception as e:
                    missing_tables.append(table)
                    print(f"  ❌ {table}: Error - {e}")
            
            # Summary
            print(f"\n📊 Table Summary:")
            print(f"  Existing: {len(existing_tables)}/{len(tables_to_check)} tables")
            print(f"  Missing: {len(missing_tables)} tables")
            
            if missing_tables:
                print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
                print(f"💡 Run database setup script: scripts/setup_db.sql")
            else:
                print(f"\n🎉 All RapidTrader tables are present!")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed!")
        print(f"Error: {str(e)}")
        
        # More detailed error information
        error_type = type(e).__name__
        print(f"Error type: {error_type}")
        
        if "getaddrinfo failed" in str(e):
            print("\n🔧 Troubleshooting:")
            print("  • Check if the database host is correct")
            print("  • Verify network connectivity")
            print("  • Ensure database server is running")
            
        elif "password authentication failed" in str(e):
            print("\n🔧 Troubleshooting:")
            print("  • Check username and password")
            print("  • Verify database credentials")
            
        elif "database" in str(e) and "does not exist" in str(e):
            print("\n🔧 Troubleshooting:")
            print("  • Create the database first")
            print("  • Check database name spelling")
            
        elif "refused" in str(e):
            print("\n🔧 Troubleshooting:")
            print("  • Check if PostgreSQL is running")
            print("  • Verify the port number")
            print("  • Check firewall settings")
        
        return False


def show_connection_options():
    """Show different database connection options."""
    print("\n" + "=" * 50)
    print("🔧 Database Connection Options")
    print("=" * 50)
    
    print("\n1️⃣ **Local PostgreSQL**")
    print("   RT_DB_URL=postgresql+psycopg://postgres:password@localhost:5432/rapidtrader")
    print("   • Install PostgreSQL locally")
    print("   • Create 'rapidtrader' database")
    print("   • Run scripts/setup_db.sql")
    
    print("\n2️⃣ **Supabase (Recommended)**")
    print("   RT_DB_URL=postgresql+psycopg://user:pass@host:5432/postgres")
    print("   • Sign up at supabase.com")
    print("   • Create new project")
    print("   • Use connection string from Settings > Database")
    
    print("\n3️⃣ **Docker PostgreSQL**")
    print("   docker run -d --name rapidtrader-db \\")
    print("     -e POSTGRES_PASSWORD=postgres \\")
    print("     -e POSTGRES_DB=rapidtrader \\")
    print("     -p 5432:5432 postgres:15")
    
    print("\n4️⃣ **Cloud PostgreSQL**")
    print("   • AWS RDS, Google Cloud SQL, Azure Database")
    print("   • Use provider's connection string")
    
    print(f"\n💡 Current configuration (in .env file):")
    print(f"   RT_DB_URL={settings.RT_DB_URL}")


def main():
    """Main function."""
    success = test_database_connection()
    
    if not success:
        show_connection_options()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
