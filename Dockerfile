# ── Stage 1 : dépendances ───────────────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2 : image finale ───────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app

COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY src/ ./src/
COPY tests/ ./tests/

# Utilisateur non-root avec droits sur /app (fix coverage.xml write)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
