FROM python:3.12-slim

# 安全默认值:生产环境禁止默认 SECRET_KEY 启动
ENV APP_ENV=production \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/app/ ./app/

# Copy frontend build artifacts
COPY frontend/dist/ ./frontend/dist/

# Create data directories + non-root user
RUN mkdir -p /data/uploads /data/db \
    && groupadd -r app && useradd -r -g app -d /app -s /usr/sbin/nologin app \
    && chown -R app:app /app /data

USER app

EXPOSE 8000

# Healthcheck via /health endpoint (curl not available in slim image — use python)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status==200 else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
