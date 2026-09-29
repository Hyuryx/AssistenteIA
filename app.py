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
    obter_gemini_api_key,
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

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Assistente IA Carregando...</h1>")

@app.get("/style.css")
async def get_css():
    return FileResponse(BASE_DIR / "style.css", media_type="text/css")

@app.get("/app.js")
async def get_js():
    return FileResponse(BASE_DIR / "app.js", media_type="application/javascript")

class ChatRequest(BaseModel):
    question: str
    attendant: Optional[str] = "Heitor"

def carregar_metricas_ia() -> dict:
    metricas_file = DATA_DIR / "metricas_ia.json"
    if metricas_file.exists():
        try:
            with open(metricas_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"perguntas_respondidas": 0}

def salvar_metricas_ia(metricas: dict):
    metricas_file = DATA_DIR / "metricas_ia.json"
    try:
        with open(metricas_file, "w", encoding="utf-8") as f:
            json.dump(metricas, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

@app.post("/api/chat")
@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    question = req.question.strip()
    attendant = (req.attendant or "Heitor").strip()
    if not question:
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")
    
    try:
        # Chama a função oficial do atendente
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, responder_duvida, question, attendant)
        
        # Incrementa contador de aprendizado da IA
        m = carregar_metricas_ia()
        m["perguntas_respondidas"] = m.get("perguntas_respondidas", 0) + 1
        salvar_metricas_ia(m)
        
        return {"success": True, "answer": answer}
    except Exception as e:
        return {"success": False, "answer": f"Erro interno ao processar a dúvida: {str(e)}"}

@app.get("/api/stats")
@app.get("/stats")
async def stats_endpoint():
    import atendente
    api_key_val = obter_gemini_api_key()
    
    # 1. Status da API Key (Ativa [verde], Esgotada [laranja], Offline [vermelho])
    if not api_key_val:
        api_status = "offline"
        api_label = "Offline"
        api_color = "red"
        api_desc = "Sem chave configurada no servidor"
    elif getattr(atendente, "ULTIMO_ERRO_QUOTA", False):
        api_status = "exhausted"
        api_label = "Esgotada"
        api_color = "orange"
        api_desc = "Limite de requisições excedido temporariamente"
    else:
        api_status = "active"
        api_label = "Ativa"
        api_color = "green"
        api_desc = "Conectada ao Gemini 2.5 Flash"

    # 2. Status da Base de Dados (Ativa [verde], Em Manutenção [laranja], Offline [vermelho])
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

    metricas = carregar_metricas_ia()
    perguntas_feitas = metricas.get("perguntas_respondidas", 0)

    # 3. Cálculo do Nível de Inteligência (0% a 100%)
    if not KB_TEXT_FILE.exists() or kb_size == 0:
        score_inteligencia = 0
        nivel_classificacao = "Base Vazia (0%)"
    else:
        # Páginas oficiais (até 45 pts)
        pts_paginas = min(45, int((total_pages / 50) * 45)) if total_pages > 0 else 30
        # Documentos e manuais locais integrados (até 35 pts)
        pts_docs = min(35, total_docs * 15)
        # Volume de dados e regras em KB (até 10 pts)
        pts_volume = min(10, int((kb_size / (140 * 1024)) * 10))
        # Histórico de aprendizado de perguntas atendidas (até 10 pts adicionais)
        pts_aprendizado = min(10, perguntas_feitas)
        
        score_inteligencia = min(100, max(15, pts_paginas + pts_docs + pts_volume + pts_aprendizado))
        
        if score_inteligencia >= 90:
            nivel_classificacao = "Nível Especialista (Alta Precisão)"
        elif score_inteligencia >= 70:
            nivel_classificacao = "Nível Avançado"
        elif score_inteligencia >= 45:
            nivel_classificacao = "Nível Intermediário"
        else:
            nivel_classificacao = "Nível Básico"

    if sync_state.get("is_running"):
        kb_status = "maintenance"
        kb_label = "Em Manutenção"
        kb_color = "orange"
        kb_desc = "Varrendo novas informações..."
    elif not KB_TEXT_FILE.exists() or kb_size == 0:
        kb_status = "offline"
        kb_label = "Offline"
        kb_color = "red"
        kb_desc = "Base de dados vazia ou não encontrada"
    else:
        kb_status = "active"
        kb_label = f"Ativa ({total_pages} Páginas)" if total_pages > 0 else "Ativa"
        kb_color = "green"
        kb_desc = f"{round(kb_size / 1024, 1)} KB • {kb_lines} linhas"

    return {
        "api_key": {
            "status": api_status,
            "label": api_label,
            "color": api_color,
            "desc": api_desc
        },
        "knowledge_base": {
            "status": kb_status,
            "label": kb_label,
            "color": kb_color,
            "desc": kb_desc,
            "total_documents": total_docs,
            "kb_size_kb": round(kb_size / 1024, 1),
            "kb_lines": kb_lines,
            "total_pages": total_pages,
            "intelligence_score": score_inteligencia,
            "intelligence_level": nivel_classificacao,
            "questions_answered": perguntas_feitas
        },
        "intelligence_score": score_inteligencia,
        "intelligence_level": nivel_classificacao,
        "questions_answered": perguntas_feitas,
        "total_documents": total_docs,
        "kb_size_kb": round(kb_size / 1024, 1),
        "kb_lines": kb_lines,
        "total_pages": total_pages,
        "has_api_key": bool(api_key_val)
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
        elif ext in [".xlsx", ".xls"]:
            import openpyxl
            wb = openpyxl.load_workbook(str(save_path), data_only=True)
            for sheetname in wb.sheetnames:
                ws = wb[sheetname]
                extracted_text += f"\n--- Planilha: {sheetname} ---\n"
                for row in ws.iter_rows(values_only=True):
                    row_txt = " | ".join([str(c) for c in row if c is not None])
                    if row_txt.strip():
                        extracted_text += row_txt + "\n"
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

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    target = DATA_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    try:
        target.unlink()
        return {"success": True, "message": f"Arquivo '{filename}' removido com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover arquivo: {str(e)}")

@app.post("/api/documents/reset")
async def reset_platform_data():
    """Limpa todos os arquivos de dados_plataforma para recomeçar do zero."""
    erros = []
    removidos = []
    for item in DATA_DIR.glob("*"):
        try:
            if item.is_file():
                item.unlink()
                removidos.append(item.name)
        except Exception as e:
            erros.append(f"{item.name}: {str(e)}")
            
    # Cria uma base_conhecimento.txt limpa inicial
    with open(KB_TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== BASE OFICIAL DE DADOS DA PLATAFORMA (VINICOLA UVVA) ===\n")
        f.write(f"Iniciada do zero em: {time.strftime('%d/%m/%Y às %H:%M:%S')}\n\n")

    return {
        "success": True,
        "message": f"Pasta dados_plataforma limpa com sucesso! {len(removidos)} arquivos apagados.",
        "removidos": removidos,
        "erros": erros
    }

@app.post("/api/rebuild-knowledge-base")
async def rebuild_knowledge_base():
    """Recompila base_conhecimento.txt a partir de conteudo_recente.json e documentos da pasta."""
    try:
        from scraper import integrar_manuais_locais
        
        paginas_coletadas = {}
        if LATEST_DATA_FILE.exists():
            with open(LATEST_DATA_FILE, "r", encoding="utf-8") as f:
                paginas_coletadas = json.load(f)

        with open(KB_TEXT_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== BASE OFICIAL DE DADOS DA PLATAFORMA (VINICOLA UVVA) ===\n")
            f.write(f"Última compilação: {time.strftime('%d/%m/%Y às %H:%M:%S')}\n\n")
            for url, info in paginas_coletadas.items():
                f.write(f"\n{'='*50}\n")
                f.write(f"PÁGINA: {info.get('titulo', 'Sem título')}\n")
                f.write(f"URL: {url}\n")
                f.write(f"{'='*50}\n")
                f.write(info.get('texto', ''))
                f.write("\n\n")
                if info.get('tabelas'):
                    f.write("--- DADOS ESTRUTURADOS / TABELAS ---\n")
                    for tab in info['tabelas']:
                        f.write(tab + "\n")
                    f.write("\n")

        integrar_manuais_locais()
        return {"success": True, "message": "Base de conhecimento recompilada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao recompilar base: {str(e)}")

@app.get("/api/knowledge-base")
@app.get("/knowledge-base")
async def get_knowledge_base():
    stats = await stats_endpoint()
    content = ""
    if KB_TEXT_FILE.exists():
        try:
            with open(KB_TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            content = f"Erro ao ler base: {str(e)}"
    else:
        content = "Base de conhecimento vazia ou ainda não compilada."

    return {
        "content": content,
        "size_chars": len(content),
        "intelligence_score": stats.get("intelligence_score", 0),
        "intelligence_level": stats.get("intelligence_level", "Básico"),
        "total_pages": stats.get("total_pages", 0),
        "total_documents": stats.get("total_documents", 0),
        "kb_size_kb": stats.get("kb_size_kb", 0),
        "questions_answered": stats.get("questions_answered", 0)
    }

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
    
    # Verifica se está rodando na Vercel (onde Chrome/Playwright não tem tela/navegador)
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return {
            "success": False,
            "message": "Atenção: A varredura com navegador (Playwright/Chrome) deve ser executada no seu computador para abrir a janela, fazer login e mapear o site. No seu computador, execute a varredura e depois pressione Ctrl+Shift+B para enviar os dados atualizados para a Vercel!"
        }

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
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip()
        except Exception:
            pass

    import config

    if conf.gemini_api_key is not None and conf.gemini_api_key.strip():
        val = conf.gemini_api_key.strip()
        env_vars["GEMINI_API_KEY"] = val
        os.environ["GEMINI_API_KEY"] = val
        config.GEMINI_API_KEY = val

    if conf.telefone_login is not None and conf.telefone_login.strip():
        val = conf.telefone_login.strip()
        env_vars["TELEFONE_LOGIN"] = val
        os.environ["TELEFONE_LOGIN"] = val
        config.TELEFONE_LOGIN = val

    if conf.senha_login is not None and conf.senha_login.strip():
        val = conf.senha_login.strip()
        env_vars["SENHA_LOGIN"] = val
        os.environ["SENHA_LOGIN"] = val
        config.SENHA_LOGIN = val

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("# Configurações de Acesso - Vinícola Uvva\n")
            f.write(f"TELEFONE_LOGIN={env_vars.get('TELEFONE_LOGIN', '')}\n")
            f.write(f"SENHA_LOGIN={env_vars.get('SENHA_LOGIN', '')}\n\n")
            f.write("# Chave de API da IA (Google AI Studio - Gratuita)\n")
            f.write(f"GEMINI_API_KEY={env_vars.get('GEMINI_API_KEY', '')}\n")
    except OSError:
        # Em ambientes serverless (Vercel), gravação em disco pode ser restrita
        pass

    return {"success": True, "message": "Configurações salvas e aplicadas com sucesso!"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print(" INICIANDO ASSISTENTE IA UVVA - SERVIDOR WEB LOCAL")
    print(" Acesse no navegador: http://localhost:8000")
    print("=" * 60 + "\n")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
