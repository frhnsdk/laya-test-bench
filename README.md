# Laya Test Bench

A self-contained local web app for trying out the [Laya](https://huggingface.co/convaiinnovations/laya) NLP model — no internet required at runtime. Supports single-text analysis, bulk CSV processing, GPU/CPU switching, and thumbs-up/down feedback collection, all through a clean browser UI.

---

## What it does

Laya is a multi-checkpoint NLP router that classifies text against structured questions. This test bench wraps it in a minimal FastAPI server and a single-page frontend so you can:

- **Analyse a single message** — type or paste text, define questions (yes/no, multiple choice, or scored), and see labelled results with confidence bars.
- **Bulk-process a CSV** — upload a file of sentences (or grab the built-in `sample.csv`) and download the results as a CSV.
- **Switch between GPU and CPU** on the fly; the model reloads in the background.
- **Choose a checkpoint** — `english`, `multilingual`, or `typed-decisions` (auto-routing picks the best one).
- **Leave feedback** — thumbs up/down on any result is saved to `data/feedback.jsonl` for later review.

---

## Quick start (Docker — recommended)

Docker bundles Python, PyTorch, all three model checkpoints, and the app itself. Nothing is downloaded at runtime.

```bat
REM Windows – uses the included compose file
start_docker.bat          # pulls/builds, starts on http://127.0.0.1:8000
stop_docker.bat           # stops and removes the container
```

Or manually:
```bash
docker compose up -d      # GPU
docker compose -f docker-compose.gpu.yml up -d   # explicit GPU compose
```

Open **http://127.0.0.1:8000**

> To persist the feedback file outside the container, add `-v "%cd%\data:/app/data"` to the `docker run` call.

---

## Quick start (Windows venv — no Docker)

```bat
python -m venv .venv
.venv\Scripts\pip install "laya[serve]==0.3.10"
.venv\Scripts\python download_models.py --all   # ~5 GB, one-time download
start.bat                                        # GPU (needs CUDA)
start_cpu.bat                                    # CPU only
```

---

## Sharing the image

The Docker image is self-contained (~5 GB). To give it to someone else:

```bat
REM already built: dist\laya-testbench.tar
docker save laya-testbench -o laya-testbench.tar
```

On the receiving PC (needs Docker Desktop; GPU is optional):
```bash
docker load -i laya-testbench.tar
docker run -d --name laya -p 127.0.0.1:8000:8000 --gpus all laya-testbench   # GPU
docker run -d --name laya -p 127.0.0.1:8000:8000 laya-testbench              # CPU
```

---

## Project layout

```
app.py               FastAPI server — /api/predict, /api/batch, /api/feedback, /api/status, /api/device
index.html           Single-page frontend (no framework, plain JS)
download_models.py   One-time checkpoint downloader (uses huggingface_hub)
Dockerfile           Self-contained image (Python 3.12, PyTorch CUDA 12.4, Laya 0.3.10)
docker-compose.yml   Standard compose (GPU)
docker-compose.gpu.yml   Explicit GPU compose
start.bat / start_cpu.bat / start_docker.bat / stop_docker.bat
samples/             sample_messages.csv — bundled CSV for the bulk box
data/                feedback.jsonl — saved thumbs-up/down records (created on first use)
model-bundle/        Model weights baked into the Docker image (not in git)
dist/                Pre-built Docker tar export (not in git)
```

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Serve the UI |
| `GET`  | `/api/status` | Model readiness, device, per-checkpoint status |
| `POST` | `/api/device` | Switch GPU ↔ CPU (`{"device": "cuda"\|"cpu"}`) |
| `POST` | `/api/predict` | Single text prediction |
| `POST` | `/api/batch` | Batch prediction (up to 500 texts) |
| `POST` | `/api/feedback` | Save a thumbs-up/down record |
| `GET`  | `/sample.csv` | Download the built-in sample CSV |

### Example — single prediction

```json
POST /api/predict
{
  "text": "I need help with my order",
  "questions": {
    "intent": {"type": "choice", "choices": ["support", "sales", "other"]}
  }
}
```

### Example — batch

```json
POST /api/batch
{
  "texts": ["sentence one", "sentence two"],
  "questions": {
    "urgent": {"type": "noul", "instructions": "Is this urgent?"}
  }
}
```

---

## Checkpoints

| Name | Best for |
|------|----------|
| `english` | English text (default) |
| `multilingual` | Non-English or mixed-language text |
| `typed-decisions` | Structured typed questions (loads on first use) |

Model weights: [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya) — Apache-2.0 licence.

---

## Licence

Apache-2.0 (model weights). The test bench code in this repo is provided as-is for evaluation use.
