FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock /app/

RUN pip install --no-cache-dir uv \
    && uv sync --frozen

COPY main.py README.md /app/
COPY src /app/src

EXPOSE 8000

CMD ["uv", "run", "main.py"]
