import json
import os
import requests
import pandas as pd
import io

data_dir = os.path.join(os.path.dirname(__file__), "data")
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_nse_symbols():
    try:
        print("Fetching NSE symbols...")
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        
        symbols = []
        for index, row in df.iterrows():
            if pd.notna(row['SYMBOL']) and row['SERIES'] == 'EQ':
                symbols.append({
                    "symbol": f"{row['SYMBOL']}",
                    "name": str(row.get('NAME OF COMPANY', '')).title(),
                    "sector": "Equity"
                })
        
        with open(os.path.join(data_dir, "nse_symbols.json"), "w") as f:
            json.dump(symbols, f, indent=4)
        print(f"Successfully saved {len(symbols)} NSE symbols.")
    except Exception as e:
        print("Error fetching NSE symbols:", e)

def fetch_bse_symbols():
    try:
        print("Fetching BSE symbols...")
        # A known github repo that maintains all active BSE/NSE stocks, or try BSE directly
        # For simplicity, bypassing BSE complex auth, using a fallback or trying standard URL
        bse_url = "https://raw.githubusercontent.com/rsm22/indian-stock-market-data/master/bse_stocks.csv"
        response = requests.get(bse_url, timeout=10)
        
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            symbols = []
            for index, row in df.iterrows():
                # Format: "symbol", "company_name"
                if 'Symbol' in df.columns:
                    sym = str(row['Symbol'])
                    name = str(row.get('Company Name', sym))
                elif 'Security Id' in df.columns:
                    sym = str(row['Security Id'])
                    name = str(row.get('Security Name', sym))
                else:
                    sym = str(row.iloc[0])
                    name = str(row.iloc[1])
                
                if sym and str(sym).lower() != 'nan':
                    symbols.append({
                        "symbol": f"{sym}.BO",
                        "name": name.title(),
                        "sector": "Equity"
                    })
                    
            with open(os.path.join(data_dir, "bse_symbols.json"), "w") as f:
                json.dump(symbols, f, indent=4)
            print(f"Successfully saved {len(symbols)} BSE symbols.")
        else:
            print(f"Failed to fetch BSE symbols from Github: {response.status_code}")
            
    except Exception as e:
        print("Error fetching BSE symbols:", e)

if __name__ == "__main__":
    fetch_nse_symbols()
    fetch_bse_symbols()
