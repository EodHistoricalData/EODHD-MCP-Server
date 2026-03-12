# Build stage
FROM python:3.10-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runtime stage
FROM python:3.10-slim AS runtime

RUN groupadd --gid 1000 app && useradd --uid 1000 --gid 1000 --no-create-home app

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import app.config" || exit 1

EXPOSE 8000

CMD ["python", "server.py"]
