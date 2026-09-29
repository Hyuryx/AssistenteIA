@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title Assistente IA Vinicola Uvva - Web App
cd /d "%~dp0"
echo ==============================================================
echo    ASSISTENTE DE SUPORTE - VINICOLA UVVA (MODO WEB APP)
echo ==============================================================
echo.
echo Iniciando servidor web local em http://localhost:8000...
echo O navegador abrira automaticamente.
echo.
start "" http://localhost:8000
.\venv\Scripts\python.exe app.py
pause
