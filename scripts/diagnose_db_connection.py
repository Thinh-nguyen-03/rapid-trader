"""Database Connection Diagnostic Script

This script helps diagnose database connection issues by testing various
aspects of the connection to your Supabase database.
"""

import os
import sys
import socket
import subprocess
from urllib.parse import urlparse
import psycopg
from sqlalchemy import create_engine, text

# Add the parent directory to the path so we can import rapidtrader modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rapidtrader.core.config import settings


def test_dns_resolution(hostname: str) -> bool:
    """Test if we can resolve the hostname to an IP address."""
    print(f"Testing DNS resolution for {hostname}...")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"SUCCESS: DNS resolution successful: {hostname} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"ERROR: DNS resolution failed: {e}")
        return False


def test_tcp_connection(hostname: str, port: int) -> bool:
    """Test if we can establish a TCP connection to the host:port."""
    print(f"Testing TCP connection to {hostname}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(10)  # 10 second timeout
            result = sock.connect_ex((hostname, port))
            if result == 0:
                print(f"SUCCESS: TCP connection successful to {hostname}:{port}")
                return True
            else:
                print(f"ERROR: TCP connection failed to {hostname}:{port} (error code: {result})")
                return False
    except Exception as e:
        print(f"ERROR: TCP connection error: {e}")
        return False


def test_ping(hostname: str) -> bool:
    """Test basic network connectivity using ping."""
    print(f"Testing ping to {hostname}...")
    try:
        # Windows ping command
        result = subprocess.run(
            ["ping", "-n", "4", hostname], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        if result.returncode == 0:
            print(f"SUCCESS: Ping successful to {hostname}")
            return True
        else:
            print(f"ERROR: Ping failed to {hostname}")
            print(f"Output: {result.stdout}")
            return False
    except Exception as e:
        print(f"ERROR: Ping error: {e}")
        return False


def test_raw_psycopg_connection(db_url: str) -> bool:
    """Test direct psycopg connection without SQLAlchemy."""
    print("Testing raw psycopg connection...")
    try:
        # Parse the URL to extract components
        parsed = urlparse(db_url)
        
        # Convert to psycopg format (remove the +psycopg part)
        psycopg_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        
        with psycopg.connect(psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                print(f"SUCCESS: Raw psycopg connection successful")
                print(f"PostgreSQL version: {version}")
                return True
    except Exception as e:
        print(f"ERROR: Raw psycopg connection failed: {e}")
        return False


def test_sqlalchemy_connection(db_url: str) -> bool:
    """Test SQLAlchemy connection."""
    print("Testing SQLAlchemy connection...")
    try:
        engine = create_engine(db_url, echo=False)
        with engine.begin() as conn:
            result = conn.execute(text("SELECT version()")).scalar()
            print(f"SUCCESS: SQLAlchemy connection successful")
            print(f"PostgreSQL version: {result}")
            return True
    except Exception as e:
        print(f"ERROR: SQLAlchemy connection failed: {e}")
        return False


def test_rapidtrader_db() -> bool:
    """Test the RapidTrader database connection."""
    print("Testing RapidTrader database connection...")
    try:
        from rapidtrader.core.db import get_engine
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables")).scalar()
            print(f"SUCCESS: RapidTrader database connection successful")
            print(f"Found {result} tables in database")
            return True
    except Exception as e:
        print(f"ERROR: RapidTrader database connection failed: {e}")
        return False


def check_environment():
    """Check environment configuration."""
    print("Checking environment configuration...")
    
    db_url = settings.RT_DB_URL
    print(f"Database URL: {db_url}")
    
    # Parse URL components
    parsed = urlparse(db_url)
    print(f"Scheme: {parsed.scheme}")
    print(f"Username: {parsed.username}")
    print(f"Password: {'*' * len(parsed.password) if parsed.password else 'None'}")
    print(f"Hostname: {parsed.hostname}")
    print(f"Port: {parsed.port}")
    print(f"Database: {parsed.path.lstrip('/')}")
    
    return parsed


def main():
    """Run all diagnostic tests."""
    print("=" * 60)
    print("RapidTrader Database Connection Diagnostics")
    print("=" * 60)
    
    # Check environment
    print("\nEnvironment Configuration")
    print("-" * 30)
    parsed_url = check_environment()
    
    if not parsed_url.hostname:
        print("ERROR: Invalid database URL - no hostname found")
        return 1
    
    # Test network connectivity
    print("\nNetwork Connectivity Tests")
    print("-" * 30)
    
    hostname = parsed_url.hostname
    port = parsed_url.port or 5432
    
    # Test DNS resolution
    dns_ok = test_dns_resolution(hostname)
    
    # Test ping
    ping_ok = test_ping(hostname)
    
    # Test TCP connection
    tcp_ok = test_tcp_connection(hostname, port)
    
    # Test database connections
    print("\nDatabase Connection Tests")
    print("-" * 30)
    
    db_url = settings.RT_DB_URL
    
    # Test raw psycopg connection
    psycopg_ok = test_raw_psycopg_connection(db_url)
    
    # Test SQLAlchemy connection
    sqlalchemy_ok = test_sqlalchemy_connection(db_url)
    
    # Test RapidTrader database connection
    rapidtrader_ok = test_rapidtrader_db()
    
    # Summary
    print("\nDiagnostic Summary")
    print("-" * 30)
    print(f"DNS Resolution: {'PASS' if dns_ok else 'FAIL'}")
    print(f"Ping Test: {'PASS' if ping_ok else 'FAIL'}")
    print(f"TCP Connection: {'PASS' if tcp_ok else 'FAIL'}")
    print(f"Raw psycopg: {'PASS' if psycopg_ok else 'FAIL'}")
    print(f"SQLAlchemy: {'PASS' if sqlalchemy_ok else 'FAIL'}")
    print(f"RapidTrader DB: {'PASS' if rapidtrader_ok else 'FAIL'}")
    
    # Provide recommendations
    print("\nRecommendations")
    print("-" * 30)
    
    if not dns_ok:
        print("- DNS resolution failed - check your internet connection")
        print("- Try using a different DNS server (8.8.8.8, 1.1.1.1)")
        print("- Check if your firewall is blocking DNS queries")
    
    if dns_ok and not ping_ok:
        print("- DNS works but ping fails - this might be normal (Supabase may block ICMP)")
    
    if dns_ok and not tcp_ok:
        print("- DNS works but TCP connection fails:")
        print("  - Check your firewall settings")
        print("  - Verify the port number (should be 5432)")
        print("  - Your ISP might be blocking the connection")
        print("  - Supabase instance might be paused or down")
    
    if tcp_ok and not psycopg_ok:
        print("- Network connectivity is good but database connection fails:")
        print("  - Check your database credentials")
        print("  - Verify the database name")
        print("  - Check if your Supabase project is active")
    
    if all([dns_ok, tcp_ok, psycopg_ok, sqlalchemy_ok, rapidtrader_ok]):
        print("- All tests passed! Your database connection is working properly.")
        print("- The issue might be intermittent or related to the specific operation.")
    
    print("\n" + "=" * 60)
    
    # Return appropriate exit code
    if rapidtrader_ok:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
