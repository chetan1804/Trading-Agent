FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY alembic.ini ./
COPY migrations ./migrations
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=10
RUN pip install --no-cache-dir --timeout 300 --retries 10 .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
