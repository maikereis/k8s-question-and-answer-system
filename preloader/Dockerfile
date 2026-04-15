# ============================================================
# Stage 1 — Dependency builder
# ============================================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install CPU-only torch first, before sentence-transformers, so the latter's
# dependency resolver accepts it instead of pulling the default CUDA wheel.
# The CPU wheel is ~250 MB vs ~2.5 GB for the CUDA variant.
RUN pip install --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# ============================================================
# Stage 2 — Runtime image
# ============================================================
FROM python:3.13-slim

# Set non-root user for security best practices
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

WORKDIR /app

# Copy only the installed site-packages from the builder — no pip, no build cache
COPY --from=builder /usr/local/lib/python3.13/site-packages \
                    /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Enable hf_transfer by default
ENV HF_HUB_ENABLE_HF_TRANSFER=1

COPY main.py .
RUN chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["python", "main.py"]
