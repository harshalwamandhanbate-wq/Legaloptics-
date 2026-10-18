#!/usr/bin/env bash
# One-click launcher for macOS / Linux: sets up Python packages, checks Ollama, starts LegalLens.
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "Python 3 is not installed."; exit 1; }
command -v ollama  >/dev/null || { echo "Ollama is not installed. Get it from https://ollama.com/download"; exit 1; }

[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# Start Ollama in the background if it is not answering yet
if ! ollama list >/dev/null 2>&1; then
  (ollama serve >/dev/null 2>&1 &)
  sleep 4
fi

ollama list | grep -q "gemma2:2b" || { echo "Downloading gemma2:2b (a few minutes)..."; ollama pull gemma2:2b; }

[ -d datasets/open_india_law ] || echo "Tip: add laws and judgments with: python fetch_open_india_law.py --help"

python -m streamlit run app.py
