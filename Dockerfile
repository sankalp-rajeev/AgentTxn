FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.10.2
COPY . .
RUN uv sync --locked --no-dev --python /usr/local/bin/python
CMD ["python", "-m", "experiments.week1_semantic_conflict", "--seed", "42", "--baseline", "all"]
