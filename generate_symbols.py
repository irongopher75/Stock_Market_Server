import json
import os

bse_companies = [
    {"symbol": "RELIANCE.BO", "name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "HDFCBANK.BO", "name": "HDFC Bank", "sector": "Banking"},
    {"symbol": "BHARTIARTL.BO", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "SBIN.BO", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "ICICIBANK.BO", "name": "ICICI Bank", "sector": "Banking"},
    {"symbol": "TCS.BO", "name": "TCS (Tata Consultancy Services)", "sector": "IT"},
    {"symbol": "BAJFINANCE.BO", "name": "Bajaj Finance", "sector": "Finance"},
    {"symbol": "LT.BO", "name": "Larsen & Toubro", "sector": "Engineering"},
    {"symbol": "HINDUNILVR.BO", "name": "Hindustan Unilever", "sector": "Consumer Goods"},
    {"symbol": "INFY.BO", "name": "Infosys", "sector": "IT"},
    {"symbol": "LICI.BO", "name": "Life Insurance Corporation of India", "sector": "Insurance"},
    {"symbol": "MARUTI.BO", "name": "Maruti Suzuki", "sector": "Automobile"},
    {"symbol": "SUNPHARMA.BO", "name": "Sun Pharmaceutical Industries", "sector": "Healthcare"},
    {"symbol": "AXISBANK.BO", "name": "Axis Bank", "sector": "Banking"},
    {"symbol": "M&M.BO", "name": "Mahindra & Mahindra", "sector": "Automobile"},
    {"symbol": "KOTAKBANK.BO", "name": "Kotak Mahindra Bank", "sector": "Banking"},
    {"symbol": "NESTLEIND.BO", "name": "Nestle India", "sector": "Consumer Goods"},
    {"symbol": "ITC.BO", "name": "ITC", "sector": "Consumer Goods"},
    {"symbol": "TITAN.BO", "name": "Titan Company", "sector": "Consumer Goods"},
    {"symbol": "NTPC.BO", "name": "NTPC", "sector": "Energy"},
    {"symbol": "ULTRACEMCO.BO", "name": "UltraTech Cement", "sector": "Materials"},
    {"symbol": "ONGC.BO", "name": "Oil & Natural Gas Corporation", "sector": "Energy"},
    {"symbol": "ADANIPORTS.BO", "name": "Adani Ports", "sector": "Infrastructure"},
    {"symbol": "BEL.BO", "name": "Bharat Electronics", "sector": "Defense"},
    {"symbol": "BAJAJFINSV.BO", "name": "Bajaj Finserv", "sector": "Finance"},
    {"symbol": "ASIANPAINT.BO", "name": "Asian Paints", "sector": "Consumer Goods"},
    {"symbol": "HCLTECH.BO", "name": "HCL Technologies", "sector": "IT"},
    {"symbol": "WIPRO.BO", "name": "Wipro", "sector": "IT"},
    {"symbol": "COALINDIA.BO", "name": "Coal India", "sector": "Energy"},
    {"symbol": "POWERGRID.BO", "name": "Power Grid Corporation of India", "sector": "Energy"},
    {"symbol": "INDUSINDBK.BO", "name": "IndusInd Bank", "sector": "Banking"},
    {"symbol": "ZOMATO.BO", "name": "Zomato", "sector": "Consumer Tech"},
    {"symbol": "GRASIM.BO", "name": "Grasim Industries", "sector": "Materials"},
    {"symbol": "BAJAJ-AUTO.BO", "name": "Bajaj Auto", "sector": "Automobile"},
    {"symbol": "DABUR.BO", "name": "Dabur India", "sector": "Consumer Goods"},
    {"symbol": "NYKAA.BO", "name": "FSN E-Commerce Ventures (Nykaa)", "sector": "Consumer Tech"},
    {"symbol": "PIDILITIND.BO", "name": "Pidilite Industries", "sector": "Materials"},
    {"symbol": "GODREJCP.BO", "name": "Godrej Consumer Products", "sector": "Consumer Goods"},
    {"symbol": "SIEMENS.BO", "name": "Siemens India", "sector": "Engineering"},
    {"symbol": "BRITANNIA.BO", "name": "Britannia Industries", "sector": "Consumer Goods"},
    {"symbol": "DMART.BO", "name": "Avenue Supermarts (DMart)", "sector": "Retail"},
    {"symbol": "DRREDDY.BO", "name": "Dr. Reddy's Laboratories", "sector": "Healthcare"},
    {"symbol": "HEROMOTOCO.BO", "name": "Hero MotoCorp", "sector": "Automobile"}
]

us_companies = [
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
    {"symbol": "AMZN", "name": "Amazon.com, Inc.", "sector": "Consumer Cyclical"},
    {"symbol": "META", "name": "Meta Platforms, Inc.", "sector": "Technology"},
    {"symbol": "TSM", "name": "Taiwan Semiconductor", "sector": "Technology"},
    {"symbol": "TSLA", "name": "Tesla, Inc.", "sector": "Automobile"},
    {"symbol": "AVGO", "name": "Broadcom Inc.", "sector": "Technology"},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc.", "sector": "Financials"},
    {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Retail"},
    {"symbol": "LLY", "name": "Eli Lilly and Company", "sector": "Healthcare"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials"},
    {"symbol": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy"},
    {"symbol": "V", "name": "Visa Inc.", "sector": "Financials"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"symbol": "ASML", "name": "ASML Holding N.V.", "sector": "Technology"},
    {"symbol": "MA", "name": "Mastercard Incorporated", "sector": "Financials"},
    {"symbol": "MU", "name": "Micron Technology, Inc.", "sector": "Technology"},
    {"symbol": "COST", "name": "Costco Wholesale Corporation", "sector": "Retail"},
    {"symbol": "UNH", "name": "UnitedHealth Group Incorporated", "sector": "Healthcare"},
    {"symbol": "PG", "name": "Procter & Gamble Company", "sector": "Consumer Goods"},
    {"symbol": "ORCL", "name": "Oracle Corporation", "sector": "Technology"},
    {"symbol": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare"},
    {"symbol": "BAC", "name": "Bank of America Corporation", "sector": "Financials"},
    {"symbol": "HD", "name": "Home Depot, Inc.", "sector": "Retail"},
    {"symbol": "CVX", "name": "Chevron Corporation", "sector": "Energy"},
    {"symbol": "KO", "name": "Coca-Cola Company", "sector": "Consumer Goods"},
    {"symbol": "CRM", "name": "Salesforce, Inc.", "sector": "Technology"},
    {"symbol": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare"},
    {"symbol": "PEP", "name": "PepsiCo, Inc.", "sector": "Consumer Goods"},
    {"symbol": "MRK", "name": "Merck & Co., Inc.", "sector": "Healthcare"},
    {"symbol": "NFLX", "name": "Netflix, Inc.", "sector": "Technology"},
    {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology"},
    {"symbol": "CSCO", "name": "Cisco Systems, Inc.", "sector": "Technology"},
    {"symbol": "CMCSA", "name": "Comcast Corporation", "sector": "Telecom"},
    {"symbol": "DIS", "name": "Walt Disney Company", "sector": "Entertainment"},
    {"symbol": "WFC", "name": "Wells Fargo & Company", "sector": "Financials"},
    {"symbol": "VZ", "name": "Verizon Communications Inc.", "sector": "Telecom"},
    {"symbol": "T", "name": "AT&T Inc.", "sector": "Telecom"},
    {"symbol": "INTC", "name": "Intel Corporation", "sector": "Technology"},
    {"symbol": "QCOM", "name": "QUALCOMM Incorporated", "sector": "Technology"},
    {"symbol": "MCD", "name": "McDonald's Corporation", "sector": "Consumer Cyclical"}
]

japan_companies = [
    {"symbol": "7203.T", "name": "Toyota Motor", "sector": "Automobile"},
    {"symbol": "8306.T", "name": "Mitsubishi UFJ Financial", "sector": "Financials"},
    {"symbol": "6758.T", "name": "Sony Group", "sector": "Technology"},
    {"symbol": "6861.T", "name": "Keyence", "sector": "Technology"},
    {"symbol": "9432.T", "name": "Nippon Telegraph and Telephone", "sector": "Telecom"},
    {"symbol": "9984.T", "name": "SoftBank Group", "sector": "Telecom"},
    {"symbol": "8035.T", "name": "Tokyo Electron", "sector": "Technology"},
    {"symbol": "8058.T", "name": "Mitsubishi Corp", "sector": "Conglomerate"},
    {"symbol": "9983.T", "name": "Fast Retailing", "sector": "Retail"},
    {"symbol": "6869.T", "name": "Sysmex", "sector": "Healthcare"},
    {"symbol": "4063.T", "name": "Shin-Etsu Chemical", "sector": "Materials"},
    {"symbol": "8316.T", "name": "Sumitomo Mitsui Financial", "sector": "Financials"},
    {"symbol": "7974.T", "name": "Nintendo", "sector": "Entertainment"},
    {"symbol": "7267.T", "name": "Honda Motor", "sector": "Automobile"},
    {"symbol": "4502.T", "name": "Takeda Pharmaceutical", "sector": "Healthcare"},
    {"symbol": "8001.T", "name": "ITOCHU", "sector": "Conglomerate"},
    {"symbol": "6098.T", "name": "Recruit Holdings", "sector": "Services"},
    {"symbol": "6501.T", "name": "Hitachi", "sector": "Engineering"},
    {"symbol": "6902.T", "name": "Denso", "sector": "Automobile"},
    {"symbol": "8031.T", "name": "Mitsui & Co", "sector": "Conglomerate"}
]

data_dir = os.path.join(os.path.dirname(__file__), "data")

with open(os.path.join(data_dir, "bse_symbols.json"), "w") as f:
    json.dump(bse_companies, f, indent=4)

with open(os.path.join(data_dir, "us_symbols.json"), "w") as f:
    json.dump(us_companies, f, indent=4)

with open(os.path.join(data_dir, "japan_symbols.json"), "w") as f:
    json.dump(japan_companies, f, indent=4)

print("Symbol datasets generated successfully.")
