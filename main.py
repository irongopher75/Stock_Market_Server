from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.db.database import init_db
from app.api import users, admin, prediction, trades, backtest, terminal, quotes, news, flights, search, ai
from app.core.limiter import limiter
from app.services.websocket_manager import ws_manager
from app.services.news_service import news_service as _news_svc
from contextlib import asynccontextmanager
import asyncio
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Global Rate Limiter
# (Imported from app.core.limiter)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        await ws_manager.start()
        asyncio.create_task(_news_svc.get_feed())
    except Exception as e:
        logger.error(f"Startup Error: {str(e)}")
    yield
    await ws_manager.stop()

app = FastAPI(
    title="AXIOM",
    description="Quantitative Intelligence Terminal",
    version="3.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Global Production Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"UNHANDLED EXCEPTION: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error (Production Hardening Engaged). Please check server logs."}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error in request parameters."}
    )

# 2. Tightened CORS for Production
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
]
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 3. Health Check Endpoint
@app.get("/health")
async def health_check():
    """Liveness probe for production monitoring."""
    return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}

# Include Routers
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(prediction.router)
app.include_router(trades.router)
app.include_router(backtest.router)
app.include_router(terminal.router)
app.include_router(quotes.router)
app.include_router(news.router)
app.include_router(flights.router)
app.include_router(search.router)
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])

@app.get("/")
def read_root():
    return {"message": "AXIOM API is running."}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
