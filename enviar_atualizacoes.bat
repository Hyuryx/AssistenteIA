@echo off
chcp 65001 > nul
title Enviar Atualizações - GitHub & Vercel
cd /d "%~dp0"

echo ==============================================================
echo    ASSISTENTE IA - ENVIAR ATUALIZACOES PARA GITHUB E VERCEL
echo ==============================================================
echo.

echo [1/4] Verificando arquivos alterados...
git status -s
echo.

set /p msg="Digite a descricao das mudancas (ou aperte Enter para padrao): "
if "%msg%"=="" (
    set msg=Atualizacao do projeto em %date% %time%
)

echo.
echo [2/4] Preparando arquivos alterados...
git add .

echo [3/4] Gravando alteracoes: "%msg%"...
git commit -m "%msg%"

echo.
echo [4/4] Enviando para o GitHub (https://github.com/Hyuryx/AssistenteIA)...
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
