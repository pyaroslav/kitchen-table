#!/usr/bin/env sh
# One command: check Ollama, fetch the model if needed, install, start, show the pairing QR code.
#   ./start.sh                 # gemma4:e4b (laptop-friendly, also hears voice)
#   KT_MODEL=gemma4:26b ./start.sh
set -e
cd "$(dirname "$0")"
MODEL="${KT_MODEL:-gemma4:e4b}"
EAR="${KT_EAR_MODEL:-gemma4:e4b}"

command -v ollama >/dev/null 2>&1 || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }
ollama list >/dev/null 2>&1 || { echo "Ollama isn't running. Start it (e.g. 'ollama serve') and try again."; exit 1; }
for m in "$MODEL" "$EAR"; do
  ollama show "$m" >/dev/null 2>&1 || { echo "Downloading $m (one time)..."; ollama pull "$m"; }
done

if [ ! -x .venv/bin/python ]; then
  echo "Setting up Python environment (one time)..."
  if command -v uv >/dev/null 2>&1; then uv venv -q .venv && uv pip install -q --python .venv/bin/python -e .
  else python3 -m venv .venv && .venv/bin/pip install -q -e .; fi
fi
KT_MODEL="$MODEL" KT_EAR_MODEL="$EAR" exec .venv/bin/python -m kitchen_table "$@"
