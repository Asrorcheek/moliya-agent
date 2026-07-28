FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests

RUN PYTHONPATH=src python -m unittest discover -s tests -v \
    && pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 moliya \
    && mkdir -p /app/data \
    && chown -R moliya:moliya /app

USER moliya

ENV ENVIRONMENT=development \
    MOLIYA_BIND_HOST=0.0.0.0 \
    MOLIYA_BIND_PORT=8088 \
    MOLIYA_PARSER_MODE=rule \
    MOLIYA_SHEET_MODE=memory \
    MOLIYA_DB_PATH=/app/data/moliya.db

EXPOSE 8088
VOLUME ["/app/data"]

CMD ["moliya-api"]
