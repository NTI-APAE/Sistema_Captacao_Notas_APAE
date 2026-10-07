@echo off
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=..\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Ambiente virtual nao encontrado.
    echo Execute: python -m venv .venv
    echo Depois: .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
"%PYTHON%" "main.py"
pause
