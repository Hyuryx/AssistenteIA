@echo off
chcp 65001 > nul
set "PATH=C:\Program Files\Git\cmd;C:\Program Files\Git\bin;%PATH%"
title Assistente IA - Escanear Plataforma e Atualizar Vercel
cd /d "%~dp0"

echo ==============================================================
echo    ASSISTENTE IA - ESCANEAR SITE E ATUALIZAR VERCEL / GITHUB
echo ==============================================================
echo.

echo [1/3] Iniciando o robo de varredura no site da Vinicola Uvva...
echo (O navegador vai fazer login, fechar popups, mapear 50 abas
echo  e integrar todos os PDFs/DOCs da pasta dados_plataforma)
echo.

if exist ".\venv\Scripts\python.exe" (
    .\venv\Scripts\python.exe scraper.py
) else (
    python scraper.py
)

if %errorlevel% neq 0 (
    echo.
    echo ==============================================================
    echo  [ERRO] Ocorreu uma falha durante a varredura.
    echo  Verifique se o site esta acessivel e suas credenciais no .env.
    echo ==============================================================
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo ==============================================================
echo  [SUCESSO] Varredura concluida e base_conhecimento.txt atualizada!
echo ==============================================================
echo.
echo [2/3] Preparando atualizacoes para o GitHub e Vercel...
git add .
git commit -m "feat: atualizacao da base de conhecimento via scan automatico [%date% %time%]"

echo.
echo [3/3] Enviando nova base para a Vercel (https://github.com/Hyuryx/AssistenteIA)...
git pull --rebase origin main
git push origin main

echo.
if %errorlevel% equ 0 (
    echo ==============================================================
    echo  [PARABENS!] Nova base de conhecimento enviada com sucesso!
    echo  O site na Vercel ja esta atualizado e respondendo com as
    echo  regras e dados mais recentes da plataforma.
    echo ==============================================================
) else (
    echo ==============================================================
    echo  [AVISO] A base foi gerada localmente, mas nao foi possivel
    echo  enviar para o GitHub. Verifique sua conexao com a internet.
    echo ==============================================================
)

echo.
pause
