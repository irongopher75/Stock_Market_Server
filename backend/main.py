from fastapi import FastAPI
from . import models, database
from .routers import users, admin, prediction
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

import os
from dotenv import load_dotenv

load_dotenv()

# Allow CORS for React Frontend
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(admin.router)
app.include_router(prediction.router)

@app.get("/")
def read_root():
    return {"message": "Stock Market Dashboard API is running"}

@app.get("/api/status")
def get_status():
    return {"status": "ok", "version": "1.0.0"}
