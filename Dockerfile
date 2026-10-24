FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN groupadd --gid 1000 labuser && useradd --uid 1000 --gid labuser --create-home labuser

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project

COPY config ./config
COPY src ./src
COPY prompts ./prompts
COPY data ./data
COPY tests ./tests
RUN uv sync --frozen

RUN mkdir -p /app/results && chown -R labuser:labuser /app

USER labuser

ENTRYPOINT ["uv", "run", "lab-runner"]
CMD ["--help"]
