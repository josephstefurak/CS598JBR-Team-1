#!/bin/bash

set -e

# Remove conflicting PyTorch / bitsandbytes installations
pip uninstall -y torch torchvision torchaudio bitsandbytes

# Install PyTorch with CUDA 12.8
pip install --no-cache-dir \
    torch==2.9.0 \
    torchvision==0.24.0 \
    torchaudio==2.9.0 \
    --index-url https://download.pytorch.org/whl/cu128

# Install bitsandbytes + project dependencies
pip install --no-cache-dir \
    bitsandbytes==0.47.0 \
    transformers==4.55.4 \
    peft==0.4.0 \
    accelerate==1.10.1 \
    einops==0.6.1 \
    evaluate==0.4.0 \
    sentencepiece==0.1.99 \
    jsonlines \
    pytest-cov

# Verify CUDA / PyTorch / bitsandbytes
python - <<'PY'
import torch
import bitsandbytes as bnb

print("PyTorch:", torch.__version__)
print("PyTorch CUDA:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
print("bitsandbytes:", bnb.__version__)

assert torch.version.cuda == "12.8", \
    f"Expected PyTorch CUDA 12.8, got {torch.version.cuda}"
assert torch.cuda.is_available(), "CUDA is not available"
PY