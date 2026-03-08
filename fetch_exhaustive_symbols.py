import json
import os
import requests
import pandas as pd
import io
import urllib3
import zipfile
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
data_dir = os.path.join(os.path.dirname(__file__), "data")
headers = {'User-Agent': 'Mozilla/5.0'}

def fetch_nse():
    print("Fetching NSE...")
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        df = pd.read_csv(io.StringIO(res.text))
        
        symbols = []
        for _, row in df.iterrows():
            clean_row = {str(k).strip(): v for k, v in row.items()}
            if clean_row.get('SERIES') == 'EQ' and pd.notna(clean_row.get('SYMBOL')):
                symbols.append({
                    "symbol": str(clean_row['SYMBOL']).strip(),
                    "name": str(clean_row.get('NAME OF COMPANY', '')).strip().title(),
                    "sector": "Equity"
                })
                
        with open(os.path.join(data_dir, "nse_symbols.json"), "w") as f:
            json.dump(symbols, f, indent=4)
        print(f"Saved {len(symbols)} NSE symbols.")
    except Exception as e:
        print(f"Error fetching NSE: {e}")

def fetch_bse():
    print("Fetching BSE Bhavcopy...")
    success = False
    for i in range(1, 10):
        dt = datetime.now() - timedelta(days=i)
        if dt.weekday() > 4: continue
        
        date_str = dt.strftime("%d%m%y")
        url = f"https://www.bseindia.com/download/BhavCopy/Equity/EQ{date_str}_CSV.ZIP"
        try:
            res = requests.get(url, headers=headers, verify=False, timeout=10)
            if res.status_code == 200 and len(res.content) > 1000:
                print(f"Found BSE Bhavcopy for {date_str}")
                with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                    csv_filename = z.namelist()[0]
                    with z.open(csv_filename) as f:
                        df = pd.read_csv(f)
                        
                symbols = []
                for _, row in df.iterrows():
                    clean_row = {str(k).strip(): v for k, v in row.items()}
                    if str(clean_row.get('SC_TYPE', '')).strip() == 'Q':
                        sc_code = str(clean_row.get('SC_CODE', '')).strip()
                        sc_name = str(clean_row.get('SC_NAME', '')).strip().title()
                        symbols.append({
                            "symbol": f"{sc_code}.BO",
                            "name": sc_name,
                            "sector": "Equity"
                        })
                
                if symbols:
                    with open(os.path.join(data_dir, "bse_symbols.json"), "w") as f:
                        json.dump(symbols, f, indent=4)
                    print(f"Saved {len(symbols)} BSE symbols.")
                    success = True
                    break
        except Exception as e:
            pass
    if not success:
        print("Could not fetch BSE Bhavcopy.")

def fetch_us():
    print("Fetching US (NASDAQ + NYSE/Other)...")
    try:
        # NASDAQ
        nasdaq_url = "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed.csv"
        nasdaq_res = requests.get(nasdaq_url, timeout=15)
        df_nasdaq = pd.read_csv(io.StringIO(nasdaq_res.text))
        
        # NYSE/Other
        nyse_url = "https://datahub.io/core/nyse-other-listings/r/other-listed.csv"
        nyse_res = requests.get(nyse_url, timeout=15)
        df_nyse = pd.read_csv(io.StringIO(nyse_res.text))
        
        symbols = []
        # Process NASDAQ - Format usually Ticker, Name
        for _, row in df_nasdaq.iterrows():
            sym = str(row.get('Symbol', '')).strip()
            if sym:
                symbols.append({
                    "symbol": sym,
                    "name": str(row.get('Name', '')).strip().title(),
                    "sector": "US Equity"
                })
        
        # Process NYSE/Other
        for _, row in df_nyse.iterrows():
            sym = str(row.get('ACT Symbol', '')).strip()
            if sym:
                symbols.append({
                    "symbol": sym,
                    "name": str(row.get('Company Name', '')).strip().title(),
                    "sector": "US Equity"
                })
                
        # Deduplicate
        seen = set()
        unique_symbols = []
        for s in symbols:
            if s['symbol'] not in seen:
                unique_symbols.append(s)
                seen.add(s['symbol'])
                
        with open(os.path.join(data_dir, "us_symbols.json"), "w") as f:
            json.dump(unique_symbols, f, indent=4)
        print(f"Saved {len(unique_symbols)} US symbols.")
    except Exception as e:
        print(f"Error fetching US symbols: {e}")

def fetch_japan():
    print("Fetching Japan (TYO)...")
    try:
        # Using a reliable Github source for TYO symbols
        url = "https://raw.githubusercontent.com/derekbanas/Python4Finance/master/Tokyo.csv"
        res = requests.get(url, timeout=15)
        df = pd.read_csv(io.StringIO(res.text))
        
        symbols = []
        for _, row in df.iterrows():
            # CSV format: Symbol,Name,Sector
            sym = str(row.iloc[0]).strip()
            name = str(row.iloc[1]).strip().title()
            sector = str(row.iloc[2]).strip()
            
            if sym:
                # Ensure .T suffix
                ticker = sym if sym.endswith('.T') else f"{sym}.T"
                symbols.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector
                })
                
        with open(os.path.join(data_dir, "japan_symbols.json"), "w") as f:
            json.dump(symbols, f, indent=4)
        print(f"Saved {len(symbols)} Japan symbols.")
    except Exception as e:
        print(f"Error fetching Japan symbols: {e}")

def fetch_uk():
    print("Fetching UK (LSE/FTSE)...")
    try:
        # Using a curated FTSE list from a reliable source
        url = "https://raw.githubusercontent.com/derekbanas/Python4Finance/master/FTSE.csv"
        res = requests.get(url, timeout=15)
        df = pd.read_csv(io.StringIO(res.text))
        
        symbols = []
        for _, row in df.iterrows():
            # Format: Symbol,Name
            sym = str(row.iloc[0]).strip()
            name = str(row.iloc[1]).strip().title()
            
            if sym:
                # Ensure .L suffix for LSE
                ticker = sym if sym.endswith('.L') else f"{sym}.L"
                symbols.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": "UK Equity"
                })
                
        with open(os.path.join(data_dir, "uk_symbols.json"), "w") as f:
            json.dump(symbols, f, indent=4)
        print(f"Saved {len(symbols)} UK symbols.")
    except Exception as e:
        print(f"Error fetching UK symbols: {e}")

if __name__ == "__main__":
    fetch_nse()
    fetch_bse()
    fetch_us()
    fetch_japan()
    fetch_uk()
