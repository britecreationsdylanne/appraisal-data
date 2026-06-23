# Single-container build for Cloud Run: build the frontend, then serve it +
# the API from one FastAPI process.

# --- Stage 1: build the React frontend -> static files ---
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build            # outputs /fe/dist

# --- Stage 2: Python backend, serving the built frontend ---
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# The built frontend goes where main.py looks for it (backend/static).
COPY --from=frontend /fe/dist ./static

# Production defaults — the real appraisal DB is read-only, so no seeding/migrations
# run against it. Provide DATABASE_URL, APP_DATABASE_URL, ANTHROPIC_API_KEY at deploy.
ENV APP_ENV=production \
    PYTHONUNBUFFERED=1

# Cloud Run provides $PORT (default 8080).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
