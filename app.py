r"""Laya test bench: a tiny local server + web page for trying Laya out of the box.

Docker (models are inside the image):  start_docker.bat, or docker run -p 8000:8000 laya-testbench
Windows venv:  .venv\Scripts\python.exe download_models.py --all  (once), then start.bat

Models load from disk only (no internet check), and are warmed up at startup.
"""

import os

os.environ["HF_HUB_OFFLINE"] = "1"  # never contact the hub at runtime; download_models.py does that
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import json
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

ROOT = Path(__file__).parent
FEEDBACK = ROOT / "data" / "feedback.jsonl"
FEEDBACK.parent.mkdir(exist_ok=True)
REPO = "convaiinnovations/laya"
PRELOAD = ["english", "multilingual"]  # typed-decisions loads on first use (~2 s from disk)

app = FastAPI(title="Laya test bench")
state = {"router": None, "device": None, "models": {}, "status": {}, "error": None}


SUBDIRS = {"english": "", "multilingual": "multilingual", "typed-decisions": "typed-decisions"}


def local_checkpoints():
    """Find each fully downloaded checkpoint on disk, newest snapshot first.

    Missing ones are not offered; they appear once download_models.py finishes them.
    """
    from huggingface_hub.constants import HF_HUB_CACHE

    snaps = Path(HF_HUB_CACHE) / ("models--" + REPO.replace("/", "--")) / "snapshots"
    dirs = sorted(snaps.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True) if snaps.exists() else []
    found = {}
    for name, sub in SUBDIRS.items():
        for root in dirs:
            d = root / sub if sub else root
            if all((d / f).exists() for f in ("model.safetensors", "rl_agent_config.json", "tokenizer", "encoder")):
                found[name] = str(d)
                break
    return found


def refresh_checkpoints():
    """Pick up checkpoints that finished downloading while the server was running."""
    new = {k: v for k, v in local_checkpoints().items() if k not in state["models"]}
    if new and state["router"] is not None:
        state["router"].models.update(new)
        state["models"].update(new)
        for name in new:
            state["status"][name] = "on disk"


load_lock = threading.Lock()  # one model (re)load at a time


def gpu_info():
    import torch

    ok = torch.cuda.is_available()
    return ok, (torch.cuda.get_device_name(0) if ok else None)


def load_models(kind=None):
    """(Re)build the router on 'cuda' or 'cpu'. kind=None means LAYA_DEVICE, else GPU if there is one."""
    if not load_lock.acquire(blocking=False):
        return
    try:
        t0 = time.perf_counter()
        import gc

        import torch
        from laya import Router

        old, state["router"], state["error"] = state["router"], None, None
        if old is not None:  # free the previous device's memory before loading the new one
            old.unload()
            del old
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        state["gpu"], state["gpu_name"] = gpu_info()
        kind = kind or os.environ.get("LAYA_DEVICE", "").lower() or "cuda"
        device = "cuda" if kind == "cuda" and state["gpu"] else "cpu"
        state["kind"] = device
        state["device"] = state["gpu_name"] if device == "cuda" else "CPU"
        models = local_checkpoints()
        if not models:
            raise RuntimeError("No models found on disk. In Docker they are built into the image; "
                               "with the Windows venv run download_models.py --all first.")
        state["models"] = models
        state["status"] = {name: "on disk" for name in models}
        router = Router(models=models, device=device, max_loaded=3)
        for name in SUBDIRS:  # never let the router fall back to downloading
            if name not in models:
                router.models.pop(name, None)
        for name in PRELOAD:
            if name in models:
                state["status"][name] = "loading"
                t = time.perf_counter()
                router.load(name).system_one({"body": "warm up"}, {"q": {"type": "noul", "instructions": "Is this a test?"}})
                state["status"][name] = f"ready ({time.perf_counter() - t:.1f}s)"
        state["router"] = router
        print(f"[laya] ready on {state['device']} in {time.perf_counter() - t0:.1f}s: {state['status']}", flush=True)
    except Exception as e:
        state["error"] = f"{type(e).__name__}: {e}"
        print(f"[laya] failed: {state['error']}", flush=True)
    finally:
        load_lock.release()


class Predict(BaseModel):
    text: str
    questions: dict
    model: str | None = None  # english | multilingual | typed-decisions | None = auto-route


class Feedback(BaseModel):
    text: str
    question: str
    predicted: str
    correct: str | None = None
    verdict: str  # "up" | "down"
    model: str | None = None


@app.on_event("startup")
def startup():
    threading.Thread(target=load_models, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(ROOT / "index.html")


@app.get("/sample.csv")
def sample_csv():
    """A ready-made CSV for the bulk box (shipped inside the app, so it works in any container)."""
    return FileResponse(ROOT / "samples" / "sample_messages.csv", media_type="text/csv",
                        filename="sample_messages.csv")


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/api/status")
def status():
    refresh_checkpoints()
    return {
        "ready": state["router"] is not None,
        "error": state["error"],
        "device": state["device"],
        "kind": state.get("kind"),  # "cuda" | "cpu"
        "gpu_available": state.get("gpu", False),
        "gpu_name": state.get("gpu_name"),
        "loading": load_lock.locked(),
        "models": state["status"],
    }


class Device(BaseModel):
    device: str  # "cuda" | "cpu"


@app.post("/api/device")
def set_device(req: Device):
    """Switch between GPU and CPU. Models are reloaded on the new device in the background."""
    if req.device not in ("cuda", "cpu"):
        raise HTTPException(400, "device must be 'cuda' or 'cpu'")
    if req.device == "cuda" and not state.get("gpu"):
        raise HTTPException(400, "No GPU is available to this server.")
    if load_lock.locked():
        raise HTTPException(409, "Still loading, try again in a moment.")
    if req.device == state.get("kind") and state["router"] is not None:
        return {"switching": False}
    threading.Thread(target=load_models, args=(req.device,), daemon=True).start()
    return {"switching": True}


@app.post("/api/predict")
def predict(req: Predict):
    router = state["router"]
    if router is None:
        raise HTTPException(503, state["error"] or "Model is still loading, try again in a few seconds.")
    if not req.text.strip():
        raise HTTPException(400, "Empty text")
    if req.model and req.model not in state["models"]:
        raise HTTPException(400, f"Checkpoint '{req.model}' is not downloaded. Run download_models.py --all")
    refresh_checkpoints()
    note = None
    model = req.model
    if not model:  # auto-route, but only to a checkpoint that is on disk
        wanted = router.route({"body": req.text}, req.questions).model
        if wanted not in state["models"]:
            model = "english"
            note = f"'{wanted}' checkpoint is still downloading, so this used 'english'."
    kwargs = {"model": model} if model else {}
    started = time.perf_counter()
    try:
        result = router.predict({"body": req.text}, req.questions, **kwargs)
        if note:
            result["note"] = note
    except Exception as e:  # surface Laya's own validation messages to the page
        raise HTTPException(400, f"{type(e).__name__}: {e}")
    name = result.get("routing", {}).get("model")
    if name and not str(state["status"].get(name, "")).startswith("ready"):
        state["status"][name] = "ready"
    return {"result": result, "wall_ms": round((time.perf_counter() - started) * 1000, 1), "device": state["device"]}


class Batch(BaseModel):
    texts: list[str]
    questions: dict
    model: str | None = None


def flatten(answer):
    """One flat, CSV-friendly summary of a single answer: (label, confidence)."""
    kind = answer.get("type")
    if kind == "choice":
        return answer.get("choice"), answer.get("confidence")
    if kind == "noul":
        p = answer.get("noul")
        return ("yes" if p >= 0.5 else "no"), (max(p, 1 - p) if p is not None else None)
    return answer.get("score"), answer.get("confidence")


@app.post("/api/batch")
def batch(req: Batch):
    """Analyse many sentences. Texts are grouped by checkpoint and scored in shared forward passes."""
    router = state["router"]
    if router is None:
        raise HTTPException(503, state["error"] or "Model is still loading, try again in a few seconds.")
    if not req.texts:
        raise HTTPException(400, "No sentences")
    if len(req.texts) > 500:
        raise HTTPException(400, "Send at most 500 sentences per request")
    refresh_checkpoints()
    started = time.perf_counter()
    rows = [None] * len(req.texts)
    groups = {}  # checkpoint name -> [indices]
    for i, text in enumerate(req.texts):
        if not text.strip():
            rows[i] = {"model": None, "error": "empty", "answers": {}}
            continue
        name = req.model or router.route({"body": text}, req.questions).model
        if name not in state["models"]:
            name = "english"
        groups.setdefault(name, []).append(i)
    try:
        for name, idx in groups.items():
            agent = router.load(name)
            results = agent.predict_batch([{"body": req.texts[i]} for i in idx], req.questions, batch_size=32)
            for i, res in zip(idx, results):
                rows[i] = {"model": name, "answers": {
                    q: dict(zip(("label", "confidence"), flatten(a))) for q, a in res["answers"].items()}}
    except Exception as e:
        raise HTTPException(400, f"{type(e).__name__}: {e}")
    return {"rows": rows, "ms": round((time.perf_counter() - started) * 1000, 1), "device": state["device"]}


@app.post("/api/feedback")
def feedback(fb: Feedback):
    with FEEDBACK.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**fb.model_dump(), "ts": time.time()}, ensure_ascii=False) + "\n")
    return {"saved": True}


if __name__ == "__main__":
    # Docker sets LAYA_HOST=0.0.0.0 (compose still publishes the port on 127.0.0.1 only).
    uvicorn.run(app, host=os.environ.get("LAYA_HOST", "127.0.0.1"), port=8000, log_level="warning")
