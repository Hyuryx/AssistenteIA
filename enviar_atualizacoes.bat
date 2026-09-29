@echo off
chcp 65001 > nul
set "PATH=C:\Program Files\Git\cmd;C:\Program Files\Git\bin;%PATH%"
title Assistente IA - GitHub e Vercel
cd /d "%~dp0"

echo ==============================================================
echo    ASSISTENTE IA - ENVIAR ATUALIZACOES PARA GITHUB E VERCEL
echo ==============================================================
echo.

echo [1/6] Sincronizando alteracoes em documentos e recompilando base...
if exist ".\venv\Scripts\python.exe" (
    .\venv\Scripts\python.exe -c "from app import rebuild_knowledge_base; import asyncio; asyncio.run(rebuild_knowledge_base())"
) else (
    python -c "from app import rebuild_knowledge_base; import asyncio; asyncio.run(rebuild_knowledge_base())" 2>nul
)

echo.
echo [2/6] Verificando arquivos alterados...
git status -s
echo.

set /p msg="Digite a descricao das mudancas (ou aperte Enter para padrao): "
if "%msg%"=="" (
    set msg=Atualizacao do projeto em %date% %time%
)

echo.
echo [3/6] Preparando arquivos alterados...
git add .

echo.
echo [4/6] Gravando alteracoes: "%msg%"...
git commit -m "%msg%"

echo.
echo [5/6] Sincronizando com o GitHub...
git pull --rebase origin main

echo.
echo [6/6] Enviando para o GitHub (https://github.com/Hyuryx/AssistenteIA)...
git push origin main

echo.
if %errorlevel% equ 0 (
    echo ==============================================================
    echo  [SUCESSO] Atualizacoes enviadas para o GitHub com sucesso!
    echo  A Vercel ira atualizar o site automaticamente em instantes.
    echo ==============================================================
) else (
    echo ==============================================================
    echo  [AVISO] Nao foi possivel concluir o envio.
    echo  Verifique sua conexao ou se precisa fazer login no GitHub.
    echo ==============================================================
)
echo.
pause
