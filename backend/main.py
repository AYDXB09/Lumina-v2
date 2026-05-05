"""
Lumina Backend — FastAPI application entry point.

Routes:
  /auth/*          — Canvas API key login, session management
  /api/canvas/*    — Canvas course/assignment/announcement data
  /api/chat/*      — AI chat (SSE streaming)
  /api/quiz/*      — Adaptive quiz generation
  /api/materials/* — Student file uploads
  /health          — Health check
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from auth.routes import router as auth_router
from canvas.routes import router as canvas_router
from chat.routes import router as chat_router
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Lifespan                                                            #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lumina backend starting — provider: %s", config.AI_PROVIDER)
    yield
    logger.info("Lumina backend shutting down")


# ------------------------------------------------------------------ #
# App                                                                 #
# ------------------------------------------------------------------ #

app = FastAPI(
    title="Lumina API",
    version="2.0.0",
    description="AI-powered Socratic tutoring platform for Canvas LMS students",
    lifespan=lifespan,
)

# CORS — tighten in production to actual frontend domain
origins = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",
    "https://lumina.school",
    "https://www.lumina.school",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,     # needed for httpOnly refresh cookie
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Routers                                                             #
# ------------------------------------------------------------------ #

app.include_router(auth_router)
app.include_router(canvas_router)
app.include_router(chat_router)


# ------------------------------------------------------------------ #
# Health check                                                        #
# ------------------------------------------------------------------ #

@app.get("/health", tags=["platform"])
async def health():
    return {
        "status": "ok",
        "provider": config.AI_PROVIDER,
    }


# ------------------------------------------------------------------ #
# Serve React frontend (production Docker build)                     #
# Static files are copied into /app/static by Dockerfile             #
# ------------------------------------------------------------------ #

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(STATIC_DIR):
    # Serve all static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all — return React index.html for client-side routing."""
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return {"error": "Frontend not built"}
else:
    logger.info("No static/ directory — running API-only mode (dev)")


# ------------------------------------------------------------------ #
# Dev entry point                                                     #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
