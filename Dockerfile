FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY qa_assistant ./qa_assistant
COPY data ./data

EXPOSE 5000

WORKDIR /app/qa_assistant

CMD ["sh", "-c", "uv run python db_prep.py && uv run gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 app:app"]