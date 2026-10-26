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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

from auth.routes import router as auth_router
from canvas.routes import router as canvas_router
from chat.routes import router as chat_router
from cal.routes import router as calendar_router
from materials.routes import router as materials_router
from mindmap.routes import router as mindmap_router
from studyplan.routes import router as studyplan_router
from quiz.routes import router as quiz_router
from admin.routes import router as admin_router
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# httpx logs every outgoing request URL at INFO. Keep that out of the logs: the
# Gemini embeddings call carries the API key as ?key=..., iCal feed URLs are
# capability links to a student's calendar, and Supabase filter URLs carry user ids.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


# ------------------------------------------------------------------ #
# Lifespan                                                           #
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
    description="AI-powered Socratic tutor for Canvas students",
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
# Unhandled-error fallback                                            #
# ------------------------------------------------------------------ #
# FastAPI's HTTPException still gets its own (more specific) handler --
# this only catches what would otherwise be a bare, undiagnosable 500,
# most commonly a Supabase connection timeout when the project is paused
# (2026-09-17 incident: frontend just showed "Request failed" with no way
# to tell a dead DB apart from any other server bug). Full traceback still
# goes to Railway's logs via logger.exception; the client only sees a
# message pointing at the actual likely cause.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service temporarily unavailable — the database may be "
                      "paused or restarting. Check /health, then try again in a minute."
        },
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
app.include_router(studyplan_router)
app.include_router(quiz_router)
app.include_router(admin_router)


# ------------------------------------------------------------------ #
# Health check                                                        #
# ------------------------------------------------------------------ #

@app.get("/health", tags=["platform"])
async def health():
    """
    Reports AI provider config (always) and DB reachability (actually probed).
    Previously this only checked the AI provider, so a fully-paused Supabase
    project (2026-09-17 incident — every auth route 500ing) still showed
    "status": "ok" here, giving no signal that the DB was the problem.
    """
    import asyncio
    from providers.ai import get_active_config
    from db.client import get_supabase

    provider, model = get_active_config()

    def _ping():
        get_supabase().table("schools").select("id").limit(1).execute()

    try:
        await asyncio.wait_for(asyncio.to_thread(_ping), timeout=5.0)
        db_status = "ok"
    except Exception as e:
        db_status = f"unreachable: {e}"[:200]

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "provider": provider,
        "model": model,
        "db": db_status,
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
        "https://generativelanguage.googleapis.com/v1beta/openai/models"                    if config.AI_PROVIDER == "gemini"      else
        "https://api.anthropic.com/v1/models"                                              if config.AI_PROVIDER == "anthropic"   else
        None
    )
    if not url:
        return {"provider": config.AI_PROVIDER, "skipped": True, "reason": "no ping url for this provider"}
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=headers)
        elapsed = time.monotonic() - t
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        # For Gemini, extract model ids so we know what's available
        models = None
        if config.AI_PROVIDER == "gemini" and r.status_code == 200:
            models = [m.get("id") for m in body.get("data", [])]
        return {"provider": config.AI_PROVIDER, "status": r.status_code, "elapsed_ms": round(elapsed * 1000), "models": models}
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
