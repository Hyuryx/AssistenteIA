@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title Assistente Vinicola Uvva
cd /d "%~dp0"
call .\venv\Scripts\activate.bat
python main.py
pause
