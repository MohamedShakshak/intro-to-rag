FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version .env ./
RUN uv sync --locked

COPY Module-5-Monotoring/ .

ENV PYTHONPATH="/app"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]