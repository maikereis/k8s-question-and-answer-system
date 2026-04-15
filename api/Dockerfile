# ============================================================
# Stage 1 — Dependency builder
# ============================================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ARG TORCH_VARIANT=cpu

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_HTTP_TIMEOUT=600

# Copy dependency manifests — uv.lock is required for --frozen
COPY pyproject.toml uv.lock ./

# Install dependencies for the requested Torch variant.
# --no-install-project skips installing the local package itself (no src layout needed).
# --index only accepts a URL on the CLI; named indexes belong in pyproject.toml.
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$TORCH_VARIANT" = "cpu" ]; then \
        uv sync --frozen --no-dev --no-install-project \
            --index "https://download.pytorch.org/whl/cpu" \
            --index-strategy unsafe-best-match; \
    else \
        uv sync --frozen --no-dev --no-install-project \
            --index "https://download.pytorch.org/whl/${TORCH_VARIANT}" \
            --index-strategy unsafe-best-match; \
    fi

# ============================================================
# Stage 2 — Runtime image
# ============================================================
FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app

ENV HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/torch/sentence_transformers \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy the virtualenv from the builder and the application source
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app main.py ./

# Create model/HuggingFace cache directories and ensure full ownership
RUN mkdir -p /app/.cache/huggingface /app/.cache/torch/sentence_transformers \
    && chown -R app:app /app

EXPOSE 8000
USER app
ENTRYPOINT ["python", "main.py"]
