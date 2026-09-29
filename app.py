import os
import sys
import json
import glob
import time
import asyncio
from pathlib import Path
from typing import List, Optional
from threading import Thread

# Garante suporte a UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    BASE_DIR,
    DATA_DIR,
    KB_TEXT_FILE,
    LATEST_DATA_FILE,
    PREVIOUS_DATA_FILE,
    CHANGELOG_FILE,
    TELEFONE_LOGIN,
    SENHA_LOGIN,
    GEMINI_API_KEY,
    BASE_URL,
)
from atendente import responder_duvida
from detector_mudancas import comparar_versoes
from scraper import integrar_manuais_locais

# Estado global da sincronização/varredura
sync_state = {
    "is_running": False,
    "status": "idle", # idle, running, success, error
    "logs": [],
    "last_sync": None
}

app = FastAPI(title="Assistente IA - Vinícola Uvva", version="2.0.0")

# CORS para permitir flexibilidade
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta arquivos estáticos
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True, parents=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Assistente IA Carregando...</h1>")

class ChatRequest(BaseModel):
    question: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")
    
    try:
        # Chama a função oficial do atendente
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, responder_duvida, question)
        return {"success": True, "answer": answer}
    except Exception as e:
        return {"success": False, "answer": f"Erro interno ao processar a dúvida: {str(e)}"}

@app.get("/api/stats")
async def stats_endpoint():
    total_docs = len(list(DATA_DIR.glob("*.*")))
    kb_size = KB_TEXT_FILE.stat().st_size if KB_TEXT_FILE.exists() else 0
    kb_lines = 0
    if KB_TEXT_FILE.exists():
        try:
            with open(KB_TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
                kb_lines = sum(1 for _ in f)
        except Exception:
            pass

    total_pages = 0
    if LATEST_DATA_FILE.exists():
        try:
            with open(LATEST_DATA_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                total_pages = len(dados)
        except Exception:
            pass

    return {
        "total_documents": total_docs,
        "kb_size_kb": round(kb_size / 1024, 1),
        "kb_lines": kb_lines,
        "total_pages": total_pages,
        "has_api_key": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "has_credentials": bool(os.getenv("TELEFONE_LOGIN", "").strip() and os.getenv("SENHA_LOGIN", "").strip()),
        "sync_state": sync_state
    }

@app.get("/api/documents")
async def get_documents():
    docs = []
    for file_path in DATA_DIR.glob("*.*"):
        if file_path.name in ["conteudo_recente.json", "conteudo_anterior.json", "historico_alteracoes.log"]:
            continue
        docs.append({
            "name": file_path.name,
            "size_kb": round(file_path.stat().st_size / 1024, 1),
            "extension": file_path.suffix.lower(),
            "modified": time.strftime('%d/%m/%Y %H:%M', time.localtime(file_path.stat().st_mtime)),
            "is_main_kb": file_path.name == "base_conhecimento.txt"
        })
    return {"documents": sorted(docs, key=lambda x: (not x["is_main_kb"], x["name"]))}

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename
    ext = Path(filename).suffix.lower()
    save_path = DATA_DIR / filename

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    extracted_text = ""
    # Processa de acordo com a extensão
    try:
        if ext == ".pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(str(save_path))
            for page in reader.pages:
                txt = page.extract_text()
                if txt: extracted_text += txt + "\n"
        elif ext in [".docx", ".doc"]:
            from docx import Document
            doc = Document(str(save_path))
            for para in doc.paragraphs:
                if para.text.strip(): extracted_text += para.text + "\n"
        elif ext in [".txt", ".md", ".csv", ".json", ".log"]:
            extracted_text = content.decode("utf-8", errors="ignore")
        else:
            extracted_text = content.decode("utf-8", errors="ignore")

        # Injeta na base de conhecimento se houver texto
        if extracted_text.strip():
            with open(KB_TEXT_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*50}\n")
                f.write(f"DOCUMENTO ADICIONADO VIA WEB: {filename}\n")
                f.write(f"{'='*50}\n")
                f.write(extracted_text.strip() + "\n")

        return {
            "success": True,
            "message": f"Arquivo '{filename}' processado e incorporado à base de conhecimento com sucesso!",
            "characters_extracted": len(extracted_text)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Arquivo salvo, mas ocorreu um erro na extração de texto: {str(e)}"
        }

@app.get("/api/knowledge-base")
async def get_knowledge_base():
    if not KB_TEXT_FILE.exists():
        return {"content": "Base de conhecimento vazia."}
    try:
        with open(KB_TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {"content": content, "size_chars": len(content)}
    except Exception as e:
        return {"content": f"Erro ao ler base: {str(e)}"}

class KBUpdateRequest(BaseModel):
    content: str
    mode: str = "append" # "append" ou "replace"

@app.post("/api/knowledge-base")
async def update_knowledge_base(req: KBUpdateRequest):
    try:
        if req.mode == "replace":
            with open(KB_TEXT_FILE, "w", encoding="utf-8") as f:
                f.write(req.content)
        else:
            with open(KB_TEXT_FILE, "a", encoding="utf-8") as f:
                f.write("\n\n" + req.content.strip() + "\n")
        return {"success": True, "message": "Base de conhecimento atualizada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _run_scraper_worker(headless: bool):
    global sync_state
    sync_state["is_running"] = True
    sync_state["status"] = "running"
    sync_state["logs"] = ["Iniciando conexão e varredura da plataforma..."]
    try:
        from scraper import executar_varredura
        paginas = executar_varredura(headless=headless)
        sync_state["logs"].append(f"Varredura concluída! {len(paginas or {})} páginas capturadas.")
        
        # Compara mudanças
        from detector_mudancas import comparar_versoes
        mudancas = comparar_versoes()
        sync_state["logs"].extend(mudancas)
        
        # Atualiza arquivos locais com IA
        try:
            from atualizador_arquivos import atualizar_arquivos_locais
            atualizar_arquivos_locais(mudancas)
        except Exception as err:
            sync_state["logs"].append(f"Aviso atualização de arquivos: {err}")
            
        sync_state["status"] = "success"
        sync_state["last_sync"] = time.strftime('%d/%m/%Y %H:%M:%S')
    except Exception as e:
        sync_state["status"] = "error"
        sync_state["logs"].append(f"Erro durante varredura: {str(e)}")
    finally:
        sync_state["is_running"] = False

@app.post("/api/sync")
async def trigger_sync(background_tasks: BackgroundTasks, headless: bool = True):
    global sync_state
    if sync_state["is_running"]:
        return {"success": False, "message": "Uma varredura já está em andamento!"}
    
    background_tasks.add_task(_run_scraper_worker, headless)
    return {"success": True, "message": "Varredura iniciada em segundo plano!"}

@app.get("/api/sync/status")
async def get_sync_status():
    return sync_state

@app.get("/api/changelog")
async def get_changelog():
    try:
        mudancas = comparar_versoes()
        return {"success": True, "changelog": mudancas}
    except Exception as e:
        return {"success": False, "error": str(e), "changelog": []}

@app.get("/api/pages")
async def get_pages():
    if not LATEST_DATA_FILE.exists():
        return {"pages": []}
    try:
        with open(LATEST_DATA_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        pages = []
        for url, info in dados.items():
            pages.append({
                "url": url,
                "title": info.get("titulo", "Sem título"),
                "text_snippet": info.get("texto", "")[:200] + "...",
                "tables_count": len(info.get("tabelas", []))
            })
        return {"pages": pages}
    except Exception as e:
        return {"pages": [], "error": str(e)}

class ConfigUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    telefone_login: Optional[str] = None
    senha_login: Optional[str] = None

@app.get("/api/config")
async def get_config():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else ("Configurada" if api_key else "")
    tel = os.getenv("TELEFONE_LOGIN", "").strip()
    return {
        "gemini_api_key_configured": bool(api_key),
        "gemini_api_key_masked": masked_key,
        "telefone_login": tel,
        "base_url": BASE_URL
    }

@app.post("/api/config")
async def update_config(conf: ConfigUpdate):
    env_file = BASE_DIR / ".env"
    env_vars = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()

    if conf.gemini_api_key is not None and conf.gemini_api_key.strip():
        env_vars["GEMINI_API_KEY"] = conf.gemini_api_key.strip()
        os.environ["GEMINI_API_KEY"] = conf.gemini_api_key.strip()

    if conf.telefone_login is not None and conf.telefone_login.strip():
        env_vars["TELEFONE_LOGIN"] = conf.telefone_login.strip()
        os.environ["TELEFONE_LOGIN"] = conf.telefone_login.strip()

    if conf.senha_login is not None and conf.senha_login.strip():
        env_vars["SENHA_LOGIN"] = conf.senha_login.strip()
        os.environ["SENHA_LOGIN"] = conf.senha_login.strip()

    with open(env_file, "w", encoding="utf-8") as f:
        f.write("# Configurações de Acesso - Vinícola Uvva\n")
        f.write(f"TELEFONE_LOGIN={env_vars.get('TELEFONE_LOGIN', '')}\n")
        f.write(f"SENHA_LOGIN={env_vars.get('SENHA_LOGIN', '')}\n\n")
        f.write("# Chave de API da IA (Google AI Studio - Gratuita)\n")
        f.write(f"GEMINI_API_KEY={env_vars.get('GEMINI_API_KEY', '')}\n")

    return {"success": True, "message": "Configurações atualizadas com sucesso!"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print(" INICIANDO ASSISTENTE IA UVVA - SERVIDOR WEB LOCAL")
    print(" Acesse no navegador: http://localhost:8000")
    print("=" * 60 + "\n")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
