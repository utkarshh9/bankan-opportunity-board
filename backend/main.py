from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title="Bankan Opportunity Board API",
    description="Production-grade task management platform",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {
        "message": "Bankan Opportunity Board API is running 🚀",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}