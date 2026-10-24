# Crew server: web app, graph view, tap pages and the MCP endpoint. Needs FalkorDB (see docker-compose.yml).
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    CREW_HOME=/app CREW_HOST=0.0.0.0 CREW_PORT=8765

COPY pyproject.toml README.md ./
COPY crew ./crew
RUN pip install .

COPY web ./web
COPY data ./data
COPY prompts ./prompts
RUN useradd --create-home crew && mkdir -p .cache && chown -R crew /app
USER crew

EXPOSE 8765
CMD ["crew", "serve"]
