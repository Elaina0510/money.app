FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/app/ ./app/

# Copy frontend build artifacts
COPY frontend/dist/ ./frontend/dist/

# Create data directories (will be mounted as volumes in production)
RUN mkdir -p /data/uploads /data/db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
