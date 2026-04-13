# CUDA Setup for Tavern TTS — RTX 5070 Ti on Windows

One-time setup to enable GPU-accelerated TTS with Chatterbox and Dia.

---

## Prerequisites

- NVIDIA RTX 5070 Ti (or any Ampere/Ada/Blackwell GPU)
- Windows 10/11 (64-bit)
- Python 3.10–3.12
- NVIDIA Driver ≥ 560 (supports CUDA 12.6)

---

## Step 1 — Install the NVIDIA CUDA Toolkit

Download and install **CUDA Toolkit 12.6** from NVIDIA:

```
https://developer.nvidia.com/cuda-downloads
```

Choose: Windows → x86_64 → 10/11 → exe (local)

After install, verify:
```bash
nvcc --version
# Should show: release 12.6
```

---

## Step 2 — Install PyTorch with CUDA 12.6

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

Verify GPU detection:
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# Expected: True  NVIDIA GeForce RTX 5070 Ti
```

---

## Step 3 — Install TTS dependencies

```bash
pip install -r requirements_tts.txt
```

This installs Chatterbox, Dia, and Kokoro-ONNX.

---

## Step 4 — First-run model download

On first startup, models will be auto-downloaded from HuggingFace:

| Engine      | Model ID              | Size (approx) |
|-------------|------------------------|---------------|
| Chatterbox  | resemble-ai/chatterbox | ~3 GB         |
| Dia         | nari-labs/Dia-1.6B     | ~3.5 GB       |
| Kokoro      | kokoro-v1.0.onnx + voices-v1.0.bin | ~300 MB       |

**Set HuggingFace cache location** (optional, to control where models land):
```bash
set HF_HOME=D:\models\huggingface
```

Ensure you have at least **8 GB** free on the target drive.

---

## Step 5 — Verify VRAM budget

RTX 5070 Ti has **16 GB VRAM** (sufficient for both GPU models simultaneously).

Expected VRAM usage at runtime:
- Chatterbox: ~3–4 GB
- Dia-1.6B:   ~3–4 GB
- Total:       ~6–8 GB (well within 16 GB)

Monitor during startup:
```bash
nvidia-smi -l 1
```

---

## Step 6 — Environment variables (optional)

Add to your `.env` or Windows environment:

```
# Optional: override Kokoro model file locations if they are not in the
# current working directory.
KOKORO_ONNX_PATH=C:\path\to\kokoro-v1.0.onnx
KOKORO_VOICES_PATH=C:\path\to\voices-v1.0.bin
```

---

## Troubleshooting

### "CUDA not available" at startup
- Verify driver ≥ 560: `nvidia-smi`
- Verify CUDA toolkit: `nvcc --version`
- Reinstall PyTorch with the exact CUDA 12.6 URL above

### "Out of memory" during model load
- RTX 5070 Ti has 16 GB VRAM — both models should fit easily
- If you see OOM: close other GPU processes (games, other ML apps)
- Check with `nvidia-smi` for GPU memory usage

### Chatterbox load fails
```bash
pip install --upgrade chatterbox-tts
```

### Dia load fails
```bash
pip install --upgrade dia-tts
```

### Kokoro ONNX not found
```bash
pip install --upgrade kokoro-onnx
python -c "from kokoro_onnx import Kokoro; print('kokoro-onnx import ok')"
```

---

## Quick verification script

Run this after completing setup:
```bash
python - <<'EOF'
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    props = torch.cuda.get_device_properties(0)
    print(f"VRAM: {props.total_memory // 1_048_576} MB")
print("Checking Chatterbox...", end=" ")
from chatterbox.tts import ChatterboxTTS; print("OK")
print("Checking Dia...", end=" ")
from dia.model import Dia; print("OK")
print("Checking Kokoro...", end=" ")
from kokoro_onnx import Kokoro; print("OK")
print("\nAll TTS engines importable. Ready to start Tavern TTS.")
EOF
```
