FROM python:3.12-slim-bookworm

# Prevent Python from buffering stdout/stderr (useful for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies for WeasyPrint (cairo, pango) and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (fast Python package manager).
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# Install Python dependencies into /app/.venv (layer cached on lockfile changes)
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
# `rapora-mcp` is an editable path dep (`../mcp_server`) pulled in by the `mcp`
# extra. Copy the source so `uv sync --extra mcp` can install it editable — this
# is what lets crm.asgi mount the Rapora MCP server at /mcp under ASGI.
COPY mcp_server /mcp_server
RUN uv sync --frozen --no-install-project --extra mcp

# Copy backend source
COPY backend/ .

# Put the venv's binaries on PATH so `python`, `gunicorn`, `celery` etc. resolve.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
