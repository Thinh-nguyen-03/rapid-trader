import sys
import os
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rapidtrader.core.db import get_engine
from sqlalchemy import text

@dataclass
class SICEntry:
    code: int
    office: str
    description: str
    gics_sector: str

class SICMapper:
    SECTOR_RANGES = {
        "Information Technology": [
            (3570, 3579), (3600, 3699), (3661, 3674), 
            (7370, 7379), (3823, 3825)
        ],
        "Health Care": [
            (2830, 2836), (3841, 3851), (8000, 8099)
        ],
        "Financials": [
            (6000, 6099), (6200, 6299), (6300, 6399), (6700, 6799)
        ],
        "Consumer Discretionary": [
            (2300, 2399), (3700, 3799), (5000, 5099), (5200, 5899), 
            (7000, 7099)
        ],
        "Consumer Staples": [
            (2000, 2099), (2100, 2199), (2800, 2829)
        ],
        "Energy": [
            (1300, 1399), (2900, 2999)
        ],
        "Materials": [
            (1000, 1099), (1400, 1499), (2600, 2699), 
            (2800, 2899), (3300, 3399)
        ],
        "Industrials": [
            (1500, 1799), (3400, 3569), (3580, 3599), 
            (3800, 3899), (4000, 4799)
        ],
        "Utilities": [
            (4900, 4999)
        ],
        "Communication Services": [
            (4800, 4899), (7310, 7319), (7800, 7899)
        ],
        "Real Estate": [
            (6500, 6599)
        ]
    }
    
    def __init__(self):
        self._code_to_sector = {}
        for sector, ranges in self.SECTOR_RANGES.items():
            for start, end in ranges:
                for code in range(start, end + 1):
                    self._code_to_sector[code] = sector
    
    def map_code(self, sic_code: int) -> str:
        return self._code_to_sector.get(sic_code, "Unknown")

class SECScraper:
    URL = "https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; RapidTrader/1.0) Contact: admin@rapidtrader.com"
    }
    
    def fetch_sic_data(self) -> List[Tuple[int, str, str]]:
        print("INFO: Fetching SIC codes from SEC website")
        
        response = requests.get(self.URL, headers=self.HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select_one("table.list tbody") or soup.select_one("table.list")
        
        if not table:
            raise RuntimeError("SIC table not found on SEC page")
        
        entries = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
                
            code_text = cells[0].get_text(strip=True)
            if not re.match(r'^\d{3,4}$', code_text):
                continue
                
            entries.append((
                int(code_text),
                cells[1].get_text(" ", strip=True),
                cells[2].get_text(" ", strip=True)
            ))
        
        unique_entries = sorted(set(entries), key=lambda x: x[0])
        print(f"INFO: Retrieved {len(unique_entries)} SIC codes")
        return unique_entries

class SICDatabase:
    def __init__(self):
        self.engine = get_engine()
    
    def create_table(self):
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sic_codes (
                    sic_code INTEGER PRIMARY KEY,
                    sec_office TEXT NOT NULL,
                    sic_description TEXT NOT NULL,
                    gics_sector TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_sic_gics ON sic_codes(gics_sector);
                CREATE INDEX IF NOT EXISTS idx_sic_desc ON sic_codes(sic_description);
            """))
    
    def populate(self, entries: List[SICEntry]) -> bool:
        try:
            # Use raw SQL with string formatting to avoid prepared statement issues with Supabase
            with self.engine.begin() as conn:
                # Clear existing data
                conn.execute(text("TRUNCATE TABLE sic_codes"))
                
                # Build a single INSERT statement with multiple VALUES
                values_list = []
                for entry in entries:
                    # Escape single quotes in text fields
                    office = entry.office.replace("'", "''")
                    description = entry.description.replace("'", "''")
                    sector = entry.gics_sector.replace("'", "''")
                    
                    values_list.append(f"({entry.code}, '{office}', '{description}', '{sector}')")
                
                # Execute single INSERT with all values
                insert_sql = f"""
                    INSERT INTO sic_codes (sic_code, sec_office, sic_description, gics_sector)
                    VALUES {', '.join(values_list)}
                """
                
                conn.execute(text(insert_sql))
                
                count = conn.execute(text("SELECT COUNT(*) FROM sic_codes")).scalar()
                
            print(f"SUCCESS: Inserted {count} SIC codes")
            return True
            
        except Exception as e:
            print(f"ERROR: Database population failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        with self.engine.begin() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM sic_codes")).scalar()
            
            sectors = conn.execute(text("""
                SELECT gics_sector, COUNT(*) 
                FROM sic_codes 
                GROUP BY gics_sector 
                ORDER BY COUNT(*) DESC
            """)).fetchall()
            
        return {"total": total, "sectors": dict(sectors)}

def main() -> int:
    try:
        print("INFO: Starting SIC database rebuild")
        
        scraper = SECScraper()
        mapper = SICMapper()
        database = SICDatabase()
        
        database.create_table()
        
        raw_data = scraper.fetch_sic_data()
        
        entries = [
            SICEntry(code, office, desc, mapper.map_code(code))
            for code, office, desc in raw_data
        ]
        
        if not database.populate(entries):
            return 1
        
        stats = database.get_stats()
        print(f"INFO: Database contains {stats['total']} SIC codes")

        print("SUCCESS: SIC database rebuild completed")
        return 0
        
    except Exception as e:
        print(f"ERROR: SIC rebuild failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
