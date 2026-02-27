FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

COPY pyproject.toml uv.lock /app/

RUN pip install --no-cache-dir uv \
    && uv sync --frozen

COPY main.py README.md /app/

EXPOSE 8000

CMD ["uv", "run", "main.py"]
