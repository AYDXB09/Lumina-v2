"""
Lumina Backend — FastAPI application entry point.

Routes:
  /auth/*                  — Canvas API key login, session management
  /api/canvas/*            — Canvas course/assignment/announcement data
  /api/chat/*              — AI chat (SSE streaming)
  /api/calendar/*          — iCal calendar sources + events
  /api/materials/*         — Student PDF/file uploads + RAG indexing
  /api/mindmap/*           — Course mind map (generate + store)
  /api/admin/materials/*   — Admin knowledge base upload + management
  /health                  — Health check
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
from cal.routes import router as calendar_router
from materials.routes import router as materials_router
from mindmap.routes import router as mindmap_router
from admin.routes import router as admin_router
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

    # Pre-warm the embedding model so the first sign-in (which triggers
    # background indexing) doesn't pay the 2-3 s cold-start cost on the
    # hot path.  Runs in a thread so it doesn't block the event loop.
    import asyncio
    import concurrent.futures

    def _warm_embedder():
        try:
            from rag.embedder import embed
            embed(["warmup"])
            logger.info("Embedding model pre-warmed ✓")
        except Exception as e:
            logger.warning("Embedder warmup failed (non-fatal): %s", e)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(concurrent.futures.ThreadPoolExecutor(max_workers=1), _warm_embedder)

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
app.include_router(calendar_router)
app.include_router(materials_router)
app.include_router(mindmap_router)
app.include_router(admin_router)


# ------------------------------------------------------------------ #
# Health check                                                        #
# ------------------------------------------------------------------ #

@app.get("/health", tags=["platform"])
async def health():
    model = (
        config.NVIDIA_MODEL     if config.AI_PROVIDER == "nvidia"     else
        config.ANTHROPIC_MODEL  if config.AI_PROVIDER == "anthropic"  else
        config.OPENROUTER_MODEL if config.AI_PROVIDER == "openrouter" else
        config.GROQ_MODEL       if config.AI_PROVIDER == "groq"       else
        config.GEMINI_MODEL     if config.AI_PROVIDER == "gemini"     else
        config.K2_MODEL
    )
    return {
        "status": "ok",
        "provider": config.AI_PROVIDER,
        "model": model,
    }


@app.get("/api/debug/ai-ping", tags=["platform"])
async def ai_ping():
    """Test connectivity from this server to the configured AI provider. Never cached."""
    import asyncio, time, httpx
    t = time.monotonic()
    api_key = (
        config.GROQ_API_KEY       if config.AI_PROVIDER == "groq"        else
        config.NVIDIA_API_KEY     if config.AI_PROVIDER == "nvidia"      else
        config.OPENROUTER_API_KEY if config.AI_PROVIDER == "openrouter"  else
        config.GEMINI_API_KEY     if config.AI_PROVIDER == "gemini"      else
        config.ANTHROPIC_API_KEY  if config.AI_PROVIDER == "anthropic"   else
        ""
    )
    url = (
        "https://api.groq.com/openai/v1/models"                                            if config.AI_PROVIDER == "groq"        else
        "https://integrate.api.nvidia.com/v1/models"                                       if config.AI_PROVIDER == "nvidia"      else
        "https://openrouter.ai/api/v1/models"                                              if config.AI_PROVIDER == "openrouter"  else
        f"https://generativelanguage.googleapis.com/v1beta/openai/models?key={api_key}"    if config.AI_PROVIDER == "gemini"      else
        "https://api.anthropic.com/v1/models"                                              if config.AI_PROVIDER == "anthropic"   else
        None
    )
    if not url:
        return {"provider": config.AI_PROVIDER, "skipped": True, "reason": "no ping url for this provider"}
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if config.AI_PROVIDER != "gemini" else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=headers)
        elapsed = time.monotonic() - t
        return {"provider": config.AI_PROVIDER, "status": r.status_code, "elapsed_ms": round(elapsed * 1000)}
    except Exception as e:
        elapsed = time.monotonic() - t
        return {"provider": config.AI_PROVIDER, "error": str(e), "elapsed_ms": round(elapsed * 1000)}


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
