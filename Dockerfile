# ------------------------------------------------------------------ #
# Stage 1 — Build React frontend                                     #
# ------------------------------------------------------------------ #
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --frozen-lockfile 2>/dev/null || npm install

COPY frontend/ .
RUN npm run build


# ------------------------------------------------------------------ #
# Stage 2 — Python backend                                           #
# ------------------------------------------------------------------ #
FROM python:3.12-slim AS backend

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ .

# React build → backend/static (served by FastAPI catch-all)
COPY --from=frontend-build /app/frontend/dist ./static

# Non-root user
RUN adduser --disabled-password --gecos "" lumina
USER lumina

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
