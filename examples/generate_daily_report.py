import sys
import os
from datetime import date, timedelta

# Add parent directory to path to import rapidtrader modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rapidtrader.jobs.daily_report import generate_and_save_daily_report


def main():
    print("Generate detailed report for the most recent trading day.")
    
    # Can specify a specific date or use the most recent trading day
    target_date = date.today()
    
    # If it's weekend, go back to Friday
    while target_date.weekday() > 4:  # 0=Monday, 4=Friday
        target_date -= timedelta(days=1)
    
    print(f"Generating detailed trading report for {target_date}")
    
    try:
        # Generate reports in the reports/ directory
        json_path, text_path = generate_and_save_daily_report(target_date, "reports")
        
        print("\nReport generation completed successfully!")
        print(f"JSON Report: {json_path}")
        print(f"Text Report: {text_path}")
        
    except Exception as e:
        print(f"ERROR: Failed to generate report: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
