#!/usr/bin/env python3
"""Standalone script to run the daily paper trading job.

This script can be run directly without module import issues.
It's a convenience wrapper around the main paper_daily job.
"""

import sys
import os
import subprocess

def main():
    """Run the daily paper trading job with proper module imports."""
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the project directory
    os.chdir(script_dir)
    
    # Build the command to run the module
    cmd = [sys.executable, "-m", "rapidtrader.jobs.paper_daily"]
    
    # Pass through any command line arguments
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    print("Running RapidTrader Daily Paper Trading Job...")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        # Run the command and stream output
        result = subprocess.run(cmd, check=True)
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Daily job failed with exit code {e.returncode}")
        return e.returncode
        
    except KeyboardInterrupt:
        print("\nJob interrupted by user")
        return 1
        
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
