from fastapi import FastAPI
from app.core.config import settings
from app.auth.router import router as auth_router
from app.users.router import router as users_router
import uvicorn

app = FastAPI(
    title="Bankan Opportunity Board API",
    description="Production-grade task management platform",
    version="0.1.0"
)

# ✅ Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )