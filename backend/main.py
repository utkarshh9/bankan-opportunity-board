from fastapi import FastAPI
from app.core.config import settings
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.teams.router import router as teams_router
from app.boards.router import router as boards_router
from app.columns.router import router as columns_router
from app.tasks.router import router as tasks_router
from app.comments.router import router as comments_router
from app.notifications.router import router as notifications_router
from app.activities.router import router as activities_router
from app.websocket.router import router as websocket_router
import uvicorn

app = FastAPI(
    title="Bankan Opportunity Board API",
    description="Production-grade task management platform with real-time updates",
    version="0.1.0"
)

# Include HTTP routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(boards_router, prefix="/api/v1")
app.include_router(columns_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(comments_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(activities_router, prefix="/api/v1")
app.include_router(websocket_router)

@app.get("/")
async def root():
    return {
        "message": "Bankan Opportunity Board API is running 🚀",
        "docs": "/docs",
        "redoc": "/redoc",
        "websocket": {
            "board": "ws://localhost:8000/ws/board/{board_id}?token={jwt_token}",
            "notifications": "ws://localhost:8000/ws/notifications?token={jwt_token}"
        }
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