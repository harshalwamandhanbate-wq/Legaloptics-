@echo off
REM One-click launcher for Windows: sets up Python packages, checks Ollama, starts LegalLens.
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo Python is not installed. Get it from https://www.python.org/downloads/ & pause & exit /b 1)
where ollama >nul 2>nul || (echo Ollama is not installed. Get it from https://ollama.com/download & pause & exit /b 1)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate

echo Installing Python packages...
pip install -q -r requirements.txt

REM Start Ollama in the background if it is not answering yet
ollama list >nul 2>nul || (start "" /b ollama serve & timeout /t 4 >nul)

ollama list | findstr /i "gemma2:2b" >nul || (echo Downloading the gemma2:2b model, this can take a few minutes... & ollama pull gemma2:2b)

if not exist datasets\open_india_law echo Tip: add laws and judgments with: python fetch_open_india_law.py --help

echo Starting LegalLens...
python -m streamlit run app.py
