FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/documents \
    && chown -R appuser:appuser /app /data/documents
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && if [ \"$ENVIRONMENT\" != \"production\" ]; then python -m app.seed; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
