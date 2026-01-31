"""Daily Paper Trading Job for RapidTrader."""

import argparse
from datetime import date

# Import orchestration components
from rapidtrader.data.data_utils import get_missing_trading_days
from rapidtrader.data.ingest import get_last_trading_session, validate_data_completeness
from rapidtrader.core.system_tracking import (
    create_system_runs_table_if_not_exists,
    mark_run_completion
)
from rapidtrader.jobs.summary_utils import print_daily_summary
from rapidtrader.jobs.eod_ingest import main as ingest_main
from rapidtrader.jobs.eod_trade import main as trade_main
from rapidtrader.jobs.daily_report import generate_and_save_daily_report

# Load environment variables if running directly
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, environment variables should be set elsewhere


def main():
    """Main entry point for the daily paper trading job."""
    parser = argparse.ArgumentParser(
        description="RapidTrader Daily Paper Trading Job",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This job orchestrates the complete daily trading workflow:
1. Smart data ingestion (automatically detects if fresh data is needed)
2. Signal generation with risk filtering  
3. Paper order creation
4. Detailed report generation

The system automatically determines if data ingestion is needed based on:
- Current time vs market close (4 PM ET)
- Freshness of existing data
- Whether today is a trading day

Typical usage:
  python -m rapidtrader.jobs.paper_daily          # Full workflow with auto-detection
  python -m rapidtrader.jobs.paper_daily --dry-run  # Validate only
  python -m rapidtrader.jobs.paper_daily --skip-ingest  # Force skip ingestion
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate workflow without creating orders"
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true", 
        help="Force skip data ingestion (overrides automatic detection)"
    )
    parser.add_argument(
        "--signals-only",
        action="store_true",
        help="Generate signals only, don't create orders"
    )
    parser.add_argument(
        "--report-dir",
        default="reports",
        help="Directory to save detailed reports (default: reports)"
    )
    
    args = parser.parse_args()
    
    try:
        print("=" * 60)
        print("Starting RapidTrader Daily Paper Trading Job")
        print("=" * 60)
        
        create_system_runs_table_if_not_exists()
        
        print("\nStep 1: Data Ingestion")
        print("-" * 30)
        
        if args.skip_ingest:
            print("Data ingestion manually skipped via --skip-ingest flag")
            missing_days = []
        else:
            missing_days = get_missing_trading_days()
        
        if missing_days:
            print(f"Ingesting data for {len(missing_days)} missing trading days...")
            print(f"Missing dates: {[str(d) for d in missing_days]}")
            
            # Calculate how many days back we need to go from today to cover all gaps
            oldest_missing = min(missing_days)
            days_back = (date.today() - oldest_missing).days + 5  # Add buffer
            
            # Run data ingestion with enough days to cover all gaps
            import sys
            original_argv = sys.argv[:]
            try:
                sys.argv = ["eod_ingest.py", "--days", str(days_back)]
                ingest_result = ingest_main()
            finally:
                sys.argv = original_argv
            if ingest_result != 0:
                print("ERROR: Data ingestion failed!")
                return 1
            
            print("SUCCESS: Data ingestion completed")
            
            remaining_gaps = get_missing_trading_days()
            if remaining_gaps:
                print(f"WARNING: Some gaps remain after ingestion: {[str(d) for d in remaining_gaps]}")
            else:
                print("SUCCESS: All data gaps have been filled")
        else:
            print("Data ingestion not needed - using existing data")
        
        # Get the latest trading session
        trade_date = get_last_trading_session()
        if not trade_date:
            print("ERROR: No trading data found in database")
            return 1
        
        print(f"Processing trading date: {trade_date}")
        
        print("\nStep 2: Data Validation")
        print("-" * 30)
        if not validate_data_completeness(trade_date):
            print("ERROR: Data validation failed - insufficient data for trading")
            return 1
        
        print("SUCCESS: Data validation passed")
        
        # Step 3: Signal Generation & Order Creation
        print("\nStep 3: Signal Generation & Trading")
        print("-" * 30)
        print("Generating signals and creating orders...")
        
        # Run trading job (this will generate signals and optionally create orders)
        import sys
        original_argv = sys.argv[:]
        try:
            trade_args = ["eod_trade.py", "--mode", "dry_run"]
            if args.signals_only or args.dry_run:
                trade_args.append("--signals-only")
            sys.argv = trade_args
            trade_result = trade_main()
        finally:
            sys.argv = original_argv
        if trade_result != 0:
            print("ERROR: Trading job failed!")
            return 1
        
        print("SUCCESS: Signal generation and trading completed")
        
        print("\nStep 4: Completion & Summary")
        print("-" * 30)
        
        if not args.dry_run:
            mark_run_completion(trade_date)
        
        print("\nGenerating detailed trading report...")
        try:
            json_path, text_path = generate_and_save_daily_report(trade_date, args.report_dir)
            print(f"SUCCESS: Detailed reports generated successfully")
            print(f"  JSON: {json_path}")
            print(f"  Text: {text_path}")
            print(f"INFO: Detailed reports saved to {args.report_dir}/")
        except Exception as e:
            print(f"WARNING: Failed to generate detailed report: {e}")
            print("INFO: Continuing with basic summary...")
        
        print_daily_summary(trade_date)
        
        print("\nSUCCESS: Daily Paper Trading Job completed successfully!")
        
        if args.dry_run:
            print("INFO: This was a dry-run - no orders were created")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: Daily Paper Trading Job failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())