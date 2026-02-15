from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import users, admin, prediction
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize Beanie and MongoDB
        await init_db()
        print("MongoDB Connected Successfully!")
    except Exception as e:
        print(f"Startup Error: {str(e)}")
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="Stock Market Dashboard API",
    lifespan=lifespan
)

# CORS Configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:5175").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(prediction.router)

@app.get("/")
def read_root():
    return {"message": "Stock Market Dashboard API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
