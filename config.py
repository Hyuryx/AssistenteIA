import os
from pathlib import Path
from dotenv import load_dotenv

import sys

# Garante suporte a emojis e UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Define BASE_DIR dependendo se está rodando via script ou .exe
if getattr(sys, 'frozen', False):
    # Se for executável, usa o diretório onde o .exe está
    BASE_DIR = Path(sys.executable).parent
else:
    # Se for script, usa o diretório do arquivo config.py
    BASE_DIR = Path(__file__).resolve().parent

# Carrega variáveis do arquivo .env
load_dotenv(BASE_DIR / ".env")

# URLs da Plataforma
BASE_URL = "https://vinicolauvva.com"
LOGIN_URL = f"{BASE_URL}/login"

# Credenciais
TELEFONE_LOGIN = os.getenv("TELEFONE_LOGIN", "").strip()
SENHA_LOGIN = os.getenv("SENHA_LOGIN", "").strip()
GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_KEY")
    or os.getenv("CHAVE_GEMINI")
    or os.getenv("CHAVE_IA")
    or os.getenv("API_KEY")
    or ""
).strip()

# Diretórios e Arquivos de Armazenamento
DATA_DIR = BASE_DIR / "dados_plataforma"
DATA_DIR.mkdir(exist_ok=True, parents=True)

SESSION_FILE = BASE_DIR / "sessao_uvva.json"
LATEST_DATA_FILE = DATA_DIR / "conteudo_recente.json"
PREVIOUS_DATA_FILE = DATA_DIR / "conteudo_anterior.json"
KB_TEXT_FILE = DATA_DIR / "base_conhecimento.txt"
CHANGELOG_FILE = DATA_DIR / "historico_alteracoes.log"
