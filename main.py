from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.api import users, admin, prediction, trades, backtest, terminal, quotes, news, flights
from app.services.websocket_manager import ws_manager
from app.services.news_service import news_service as _news_svc
from contextlib import asynccontextmanager
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize Beanie and MongoDB
        await init_db()
        print("MongoDB Connected Successfully!")
        # Start WebSocket Manager
        await ws_manager.start()
        print("WebSocket Manager Started!")
        # Pre-warm news cache in background so first request is instant
        asyncio.create_task(_news_svc.get_feed())
        print("News cache warming started...")
    except Exception as e:
        print(f"Startup Error: {str(e)}")
    yield
    # Shutdown logic
    await ws_manager.stop()
    print("WebSocket Manager Stopped.")

app = FastAPI(
    title="Stock Market Dashboard API",
    lifespan=lifespan
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import logging
    logging.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# CORS Configuration
# Include both localhost and 127.0.0.1 to prevent mismatches
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://0.0.0.0:5173",
    "http://0.0.0.0:5174",
    "http://0.0.0.0:5175",
]

# Allow additional origins from environment variable
env_origins = os.getenv("CORS_ORIGINS")
if env_origins:
    if env_origins == "*":
        origins = ["*"]
    else:
        origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional diagnostic middleware to log headers in dev
@app.middleware("http")
async def log_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin:
        import logging
        logging.info(f"Incoming Request Origin: {origin}")
    response = await call_next(request)
    return response

# Include Routers
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(prediction.router) # Now /api/v1/predict
app.include_router(trades.router)
app.include_router(backtest.router) # Now /api/v1/backtest
app.include_router(terminal.router)
app.include_router(quotes.router)
app.include_router(news.router)
app.include_router(flights.router)

@app.get("/")
def read_root():
    return {"message": "Stock Market Dashboard API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
