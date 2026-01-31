import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rapidtrader.data.sp500_api import iSharesClient, get_sp500_symbols
from rapidtrader.core.db import get_engine
from sqlalchemy import text


def main():
    parser = argparse.ArgumentParser(description="Fetch S&P 500 constituents from iShares")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--export", choices=["csv", "json"])
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    print("=" * 80)
    print("S&P 500 Constituents Fetcher (iShares Core S&P 500 ETF)")
    print("=" * 80)
    print()

    print("Method 1: Simple API")
    print("-" * 80)
    try:
        symbols = get_sp500_symbols(force_refresh=args.force_refresh)
        print(f"Fetched {len(symbols)} constituents\n")
        print("Sample (first 10):")
        for symbol, sector in symbols[:10]:
            print(f"  {symbol:6} - {sector}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        return 1

    print("Method 2: Advanced API with DataFrame")
    print("-" * 80)
    try:
        client = iSharesClient()
        df = client.get_constituents_with_cache(force_refresh=args.force_refresh)
        print(f"Loaded {len(df)} constituents\n")

        eng = get_engine()
        with eng.begin() as conn:
            cache_info = conn.execute(text("""
                SELECT COUNT(*) as total, MAX(last_updated) as last_update,
                       COUNT(DISTINCT sector) as sectors
                FROM sp500_constituents
            """)).first()

            if cache_info and cache_info[0] > 0:
                total, last_update, sectors = cache_info
                print(f"Cache: {total} symbols, last updated {last_update} ({(date.today() - last_update).days} days old)")
                print(f"Sectors: {sectors}\n")

        print(f"Top {args.top} by Weight:")
        print("-" * 80)
        print(f"{'Rank':<6} {'Symbol':<8} {'Sector':<30} {'Weight %':>10}")
        print("-" * 80)
        for idx, row in df.head(args.top).iterrows():
            print(f"{idx+1:<6} {row['symbol']:<8} {row['sector']:<30} {row['weight']:>10.2f}%")
        print()

        print("Sector Breakdown:")
        print("-" * 80)
        sector_summary = df.groupby('sector').agg({'symbol': 'count', 'weight': 'sum'}).sort_values('weight', ascending=False)
        print(f"{'Sector':<30} {'Count':>8} {'Total Weight %':>15}")
        print("-" * 80)
        for sector, row in sector_summary.iterrows():
            print(f"{sector:<30} {int(row['symbol']):>8} {row['weight']:>14.2f}%")
        print()

        if args.export:
            timestamp = date.today().strftime("%Y%m%d")
            filename = f"sp500_constituents_{timestamp}.{args.export}"
            if args.export == "csv":
                df.to_csv(filename, index=False)
            elif args.export == "json":
                df.to_json(filename, orient="records", indent=2)
            print(f"Exported to {filename}\n")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    print("=" * 80)
    print("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
