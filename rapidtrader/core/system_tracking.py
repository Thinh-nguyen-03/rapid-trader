"""Tracking of daily job executions to monitor
system reliability and execution history.
"""

from datetime import date, datetime
from sqlalchemy import text
from rapidtrader.core.db import get_engine

def create_system_runs_table_if_not_exists():
    try:
        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_runs (
                    trade_date DATE PRIMARY KEY,
                    run_timestamp TIMESTAMP NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("INFO: System runs table ready")
    except Exception as e:
        print(f"WARNING: Could not create system_runs table ({e})")

def mark_run_completion(trade_date: date):
    try:
        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(text("""
                INSERT INTO system_runs (trade_date, run_timestamp, status)
                VALUES (:trade_date, :run_timestamp, 'completed')
                ON CONFLICT (trade_date) DO UPDATE SET
                    run_timestamp = :run_timestamp,
                    status = 'completed'
            """), {
                "trade_date": trade_date,
                "run_timestamp": datetime.now()
            })
            print(f"INFO: Marked run completion for {trade_date}")
    except Exception as e:
        print(f"WARNING: Could not mark run completion ({e})")

def get_last_successful_run() -> date:
    try:
        eng = get_engine()
        with eng.begin() as conn:
            result = conn.execute(text("""
                SELECT trade_date 
                FROM system_runs 
                WHERE status = 'completed'
                ORDER BY trade_date DESC 
                LIMIT 1
            """)).scalar_one_or_none()
            
            return result
    except Exception as e:
        print(f"WARNING: Could not check last successful run ({e})")
        return None

def get_system_run_history(limit: int = 30) -> list[dict]:
    try:
        eng = get_engine()
        with eng.begin() as conn:
            results = conn.execute(text("""
                SELECT trade_date, run_timestamp, status 
                FROM system_runs 
                ORDER BY trade_date DESC 
                LIMIT :limit
            """), {"limit": limit}).all()
            
            return [
                {
                    "trade_date": row.trade_date,
                    "run_timestamp": row.run_timestamp,
                    "status": row.status
                }
                for row in results
            ]
    except Exception as e:
        print(f"WARNING: Could not get system run history ({e})")
        return []
