@echo off
chcp 65001 > nul
title Assistente IA - Servidor Local (Vinicola Uvva)
cd /d "%~dp0"

echo ==============================================================
echo       INICIANDO SERVIDOR LOCAL DO ASSISTENTE IA UVVA
echo ==============================================================
echo.

:: Detecta se existe ambiente virtual
set "PYTHON_CMD=python"
if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=venv\Scripts\python.exe"
    echo [OK] Usando ambiente virtual venv.
)

:: Abre o navegador automaticamente apos 2 segundos
start "" cmd /c "timeout /t 2 /nobreak > nul & start http://localhost:8000"

echo [OK] Abrindo navegador em http://localhost:8000 ...
echo [OK] Para encerrar o servidor, feche esta janela.
echo.
echo ==============================================================

%PYTHON_CMD% -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

pause
