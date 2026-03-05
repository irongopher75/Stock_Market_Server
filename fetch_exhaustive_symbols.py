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
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    res = requests.get(url, headers=headers, verify=False, timeout=15)
    df = pd.read_csv(io.StringIO(res.text))
    
    symbols = []
    for _, row in df.iterrows():
        # Clean column names just in case
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

def fetch_bse():
    print("Fetching BSE Bhavcopy...")
    # Try the last 5 days until we find a valid Bhavcopy
    success = False
    for i in range(1, 10):
        dt = datetime.now() - timedelta(days=i)
        if dt.weekday() > 4: continue # Skip weekends
        
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
                    # Filter for pure equity (SC_TYPE == 'Q')
                    if str(clean_row.get('SC_TYPE', '')).strip() == 'Q':
                        sc_code = str(clean_row.get('SC_CODE', '')).strip()
                        sc_name = str(clean_row.get('SC_NAME', '')).strip().title()
                        
                        symbols.append({
                            "symbol": f"{sc_code}.BO", # BSE symbols for yfinance use script code + .BO
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

if __name__ == "__main__":
    fetch_nse()
    fetch_bse()
