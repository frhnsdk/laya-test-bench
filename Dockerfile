# syntax=docker/dockerfile:1
# Laya test bench, fully self-contained: Python, PyTorch (CUDA), Laya AND the three model
# checkpoints are inside the image. Run it anywhere Docker runs; nothing is downloaded at runtime.
# Layer order is heaviest and least-changing first, so editing app.py/index.html rebuilds in seconds.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/models \
    LAYA_HOST=0.0.0.0

# The pip cache mount keeps downloaded wheels if a build is interrupted, so a retry resumes fast.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124 --extra-index-url https://pypi.org/simple

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "laya[serve]==0.3.10"

# Model weights (Apache-2.0, convaiinnovations/laya): english, multilingual, typed-decisions.
COPY model-bundle/ /models/

WORKDIR /app
COPY app.py index.html ./
COPY samples/ ./samples/

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/status', timeout=4)" || exit 1
CMD ["python", "app.py"]
