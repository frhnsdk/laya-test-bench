# Laya test bench (Docker)

A local web page for trying **Laya**, a small, fast decision model. You type a sentence (or drop a CSV
of sentences) and it answers questions such as "which department?", "is this urgent?" and
"how frustrated?" with probabilities, in about 25 ms on a GPU. It does not generate text.

Everything is inside one Docker image (`laya-testbench`): Python, PyTorch, Laya and all three model
checkpoints. **Nothing is downloaded when it runs**, and nothing leaves the computer. The page is only
reachable from the same PC (`127.0.0.1`).

## For the person or AI setting this up

### What you receive
- `laya-testbench.tar` - the Docker image, about 5 GB (or the image name on Docker Hub, see below).
- This folder: `run.bat`, `stop.bat`, `README.md`.

### Requirements
- Windows with **Docker Desktop** installed and running (WSL2 backend, the default).
- About 15 GB free disk space (5 GB for the file, about 8 GB for the loaded image; the file can be deleted after loading).
- **Optional:** an NVIDIA GPU with a recent driver, for speed. Without one it runs on the CPU.
  AMD and Intel GPUs are not supported by this image.

### Quick start (Windows)
1. Start Docker Desktop and wait until it says the engine is running.
2. Put `laya-testbench.tar` in this folder, next to `run.bat`.
3. Double-click **`run.bat`**.
   - First time only: it loads the image (a few minutes).
   - It uses the GPU if Docker can provide one, otherwise the CPU, and tells you which.
   - When the server is ready (about 10 seconds), the page opens at **http://127.0.0.1:8000**.
4. To stop: `stop.bat`. To start again: `run.bat`.

### Doing it by hand (any OS with Docker)
```
docker load -i laya-testbench.tar

# With an NVIDIA GPU:
docker run -d --name laya -p 127.0.0.1:8000:8000 --restart unless-stopped --gpus all laya-testbench

# Without a GPU (CPU):
docker run -d --name laya -p 127.0.0.1:8000:8000 --restart unless-stopped laya-testbench
```
Then open http://127.0.0.1:8000. Later: `docker stop laya` / `docker start laya`.

To keep the feedback file on the host, add `-v "<folder>:/app/data"` to the `docker run` command.

### If the image is on Docker Hub instead of a file
```
docker pull YOURNAME/laya-testbench:1.0
docker tag YOURNAME/laya-testbench:1.0 laya-testbench
```
Then run `run.bat` (it finds the image, so it skips the load step).

### Check that it works
```
curl http://127.0.0.1:8000/api/status
```
Expect `"ready":true`, and `"kind":"cuda"` (GPU) or `"kind":"cpu"`. The page shows the same in the coloured
pill at the top ("ready - NVIDIA GeForce ..." or "ready - CPU").

## Using the page
- **Sentence box:** type a sentence, press **Analyse** (or Ctrl+Enter). Edit the questions on the left,
  or add your own choice, yes/no and score questions.
- **Bulk CSV:** drop a CSV onto the dashed box (one sentence per row; a column named `text`, `sentence`
  or `message` is picked automatically), then click **Analyse all**. Download the results as CSV.
  There is a sample under "Download a sample CSV".
- **Run on: GPU | CPU** switch: moves the models to the other device in a few seconds. The GPU button is
  greyed out when no GPU is available.
- **Threshold slider:** answers below it are marked "needs human".
- **Thumbs up/down:** saves the sentence and the correct label to `data/feedback.jsonl` (in the `data` folder
  next to `run.bat` when started with `run.bat`).

## Troubleshooting
| Problem | What to do |
|---|---|
| "Docker Desktop is not running" | Start Docker Desktop, wait for "Engine running", run again. |
| `run.bat` says no GPU and uses the CPU, but there is an NVIDIA GPU | Update the NVIDIA driver. Test GPU access in Docker: `docker run --rm --gpus all ubuntu nvidia-smi`. If that fails, in Docker Desktop turn on Settings > General > "Use the WSL 2 based engine", restart Docker, and try again. |
| Port 8000 already in use | `set LAYA_PORT=8001` then run `run.bat`, and open http://127.0.0.1:8001. Or stop whatever uses 8000. |
| "container name is already in use" | `docker start laya` (it already exists), or `set LAYA_NAME=laya2` and run again. |
| `docker load` fails or the image is missing | Make sure the whole 5 GB file copied (compare file sizes with the sender). Free disk space. Load again. |
| Page shows an error instead of "ready" | `docker logs laya` and read the last lines. |
| Slow first request after a pause | Normal: the GPU warms up. Later requests take about 25 ms (GPU) or about 250 ms (CPU). |
| Want to start over | `docker stop laya`, then remove the container in Docker Desktop (Containers, bin icon), then run `run.bat` again. The image stays. |

## Expected speed (RTX 3060 Ti vs CPU, for reference)
| | GPU | CPU |
|---|---|---|
| one sentence | about 25 ms | about 250 ms |
| 40-row CSV | about 0.3 s | about 9 s |

## Notes
- The models are English, multilingual (100+ languages) and typed-decisions checkpoints of
  `convaiinnovations/laya` (Apache-2.0). Out of the box they make mistakes on custom categories; they are
  meant to be fine-tuned. Use the thumbs buttons to collect corrections.
- PyTorch and the NVIDIA CUDA libraries inside the image have their own licences.
- Uninstall: stop and remove the container, then `docker rmi laya-testbench`.
