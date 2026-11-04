FROM node:22-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY inventory/ ./inventory/
COPY --from=frontend /app/dist ./frontend/dist
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DNA_CONFIG=/config/config.json
EXPOSE 18160
CMD ["python", "-m", "inventory"]
