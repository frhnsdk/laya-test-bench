"""One-time download of the Laya checkpoints. After this, app.py starts offline from disk.

Run:  .venv\Scripts\python.exe download_models.py            (english + multilingual)
      .venv\Scripts\python.exe download_models.py --all      (also typed-decisions)
Interrupted downloads resume where they stopped.
"""

import sys

from huggingface_hub import snapshot_download

REPO = "convaiinnovations/laya"
FILES = ("rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*")
CHECKPOINTS = {"english": "", "multilingual": "multilingual/", "typed-decisions": "typed-decisions/"}

wanted = list(CHECKPOINTS) if "--all" in sys.argv else ["english", "multilingual"]
patterns = [CHECKPOINTS[name] + f for name in wanted for f in FILES]
print(f"Downloading {', '.join(wanted)} from {REPO} ...", flush=True)
path = snapshot_download(REPO, allow_patterns=patterns)
print(f"Done. Saved under {path}", flush=True)
