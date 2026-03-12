"""
FastAPI backend entry point for music-organizer services.
"""

from fastapi import FastAPI
from .routes import router as api_router

app = FastAPI(
    title="Music Organizer API",
    description="Backend services for DJ-grade music library organization",
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "music-organizer-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
