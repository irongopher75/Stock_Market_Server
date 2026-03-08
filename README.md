# AXIOM Terminal: Backend (Server)

The **AXIOM Server** is a high-performance FastAPI backend designed to normalize and broadcast global intelligence streams.

## 🚀 Tech Stack
- **Framework**: FastAPI (Python)
- **Database**: MongoDB + Beanie ODM
- **Async I/O**: Httpx + Asyncio (Parallel scraping)
- **Real-time**: Custom WebSocket Manager for mass broadcasting.

## 📡 Intelligence Services
- **AISService**: Normalizes complex AISStream WebSocket data into flattened geospatial markers.
- **AviationService**: Integrates FlightRadar24 ADS-B streams.
- **NewsIntelligenceService**: Parallel scraper for Finnhub and GDELT with automated severity ranking.
- **MLEngine**: Prediction service calculating market regimes and trade signals.

## 🛠️ Configuration
Required environment variables in `.env`:
```env
FINNHUB_API_KEY=your_key
AISSTREAM_API_KEY=your_key
SECRET_KEY=your_jwt_secret
CORS_ORIGINS=http://localhost:5173,*
```

## 🏃 Running Locally
```bash
pip install -r requirements.txt
python main.py
```
