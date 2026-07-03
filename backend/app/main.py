import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.logger import app_logger
from app.routers import auth_router, triage_router, doctors_router, appointments_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CareThread API",
    description="Healthcare appointment scheduling system with triage engine",
    version="1.0.0"
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5500")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(triage_router.router)
app.include_router(doctors_router.router)
app.include_router(appointments_router.router)


@app.get("/")
def health_check():
    app_logger.info("Health check endpoint called")
    return {"status": "ok", "service": "CareThread API"}