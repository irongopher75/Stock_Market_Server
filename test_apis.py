import pandas as pd
import requests
import io
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

print("Testing NSE...")
url_nse = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
try:
    res = requests.get(url_nse, headers=headers, verify=False, timeout=10)
    df = pd.read_csv(io.StringIO(res.text))
    print("NSE Columns:", df.columns.tolist())
    print("NSE Count:", len(df))
except Exception as e:
    print("NSE error:", e)

print("\nTesting BSE...")
url_bse = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
try:
    res2 = requests.get(url_bse, headers=headers, verify=False, timeout=10)
    print("BSE response code:", res2.status_code)
    data = res2.json()
    if isinstance(data, list) and len(data) > 0:
        print("BSE Sample keys:", list(data[0].keys()))
        print("BSE Count:", len(data))
except Exception as e:
    print("BSE error:", e)
