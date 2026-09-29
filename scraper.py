import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pathlib import Path

from config import (
    BASE_URL,
    LOGIN_URL,
    TELEFONE_LOGIN,
    SENHA_LOGIN,
    SESSION_FILE,
    LATEST_DATA_FILE,
    PREVIOUS_DATA_FILE,
    KB_TEXT_FILE,
    DATA_DIR
)

def extrair_texto_limpo(html_content: str) -> str:
    """Limpa scripts, tags desnecessárias e retorna texto legível."""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    
    linhas = [linha.strip() for linha in soup.get_text(separator="\n").split("\n")]
    linhas_validas = [l for l in linhas if l]
    return "\n".join(linhas_validas)

def extrair_tabelas_e_cartoes(soup: BeautifulSoup) -> list:
    """Extrai informações estruturadas de tabelas e listas de itens."""
    dados_estruturados = []
    
    # Extrair tabelas convencionais
    for tabela in soup.find_all("table"):
        linhas_tabela = []
        for tr in tabela.find_all("tr"):
            celulas = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if celulas:
                linhas_tabela.append(" | ".join(celulas))
        if linhas_tabela:
            dados_estruturados.append("\n".join(linhas_tabela))
            
    return dados_estruturados

def fechar_modais_e_popups(page):
    """Fecha anúncios, caps, avisos promocionais e modais que cobrem a tela."""
    seletores = [
        "button[aria-label='Close']", ".modal-close", ".btn-close",
        ".close", "#closeModal", "button:has-text('Fechar')",
        "button:has-text('Entendi')", "button:has-text('Confirmar')",
        "button:has-text('OK')", ".popup-close", ".van-popup__close-icon",
        ".layui-layer-close", ".alert-close", ".dialog-close"
    ]
    for sel in seletores:
        try:
            elem = page.locator(sel).first
            if elem.is_visible(timeout=400):
                elem.click(timeout=1000)
                time.sleep(0.5)
        except Exception:
            pass

def executar_varredura(headless: bool = False):
    """
    Inicia o navegador, realiza o login (ou reutiliza sessão) e
    percorre todas as abas e páginas internas disponíveis.
    """
    if not TELEFONE_LOGIN or not SENHA_LOGIN:
        print("\n[ERRO] Credenciais de login não configuradas no arquivo .env!")
        print("Por favor, preencha TELEFONE_LOGIN e SENHA_LOGIN no arquivo .env.\n")
        return None

    # Rotaciona arquivos para detecção de mudanças futuras
    if LATEST_DATA_FILE.exists():
        if PREVIOUS_DATA_FILE.exists():
            PREVIOUS_DATA_FILE.unlink()
        LATEST_DATA_FILE.rename(PREVIOUS_DATA_FILE)

    print("\n" + "=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando robô de varredura...")
    print("=" * 60)

    paginas_coletadas = {}
    urls_para_visitar = set()
    urls_visitadas = set()

    with sync_playwright() as p:
        # Abre o navegador (Chrome/Chromium) do próprio sistema para não depender dos binários do Playwright no .exe
        try:
            browser = p.chromium.launch(headless=headless, channel="chrome")
        except Exception:
            try:
                browser = p.chromium.launch(headless=headless, channel="msedge")
            except Exception:
                print("\n[ERRO] Não foi possível encontrar Google Chrome ou Microsoft Edge no seu sistema.")
                print("O assistente precisa de um desses navegadores instalados para varrer o site.")
                import sys
                sys.exit(1)
        
        # Carrega sessão prévia se existir
        if SESSION_FILE.exists():
            print("Carregando sessão salva anteriormente...")
            try:
                context = browser.new_context(storage_state=str(SESSION_FILE))
            except Exception:
                context = browser.new_context()
        else:
            context = browser.new_context()

        page = context.new_page()

        def coletar_links_pagina():
            links = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            for link in links:
                if not link or "javascript" in link or "#" in link:
                    continue
                # Filtra apenas links do próprio domínio
                if link.startswith(BASE_URL) or link.startswith("/"):
                    # Ignora rotas de deslogar
                    if not any(ign in link.lower() for ign in ["logout", "sair", "signout"]):
                        urls_para_visitar.add(link)

        # 1. Analisa páginas públicas (Login, Recuperar Senha, Cadastro, etc)
        print("Analisando páginas de acesso públicas antes do login...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        urls_para_visitar.add(page.url)
        coletar_links_pagina()
        
        # Filtra apenas as que parecem ser públicas a partir do login
        paginas_publicas = list(urls_para_visitar)
        for url_pub in paginas_publicas:
            if url_pub in urls_visitadas: continue
            urls_visitadas.add(url_pub)
            print(f"-> Extraindo página pública: {url_pub}")
            try:
                page.goto(url_pub, wait_until="domcontentloaded", timeout=20000)
                time.sleep(1)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                titulo = page.title() or soup.find("h1") or "Sem título"
                if hasattr(titulo, "get_text"): titulo = titulo.get_text(strip=True)
                
                paginas_coletadas[url_pub] = {
                    "url": url_pub,
                    "titulo": str(titulo),
                    "texto": extrair_texto_limpo(html),
                    "tabelas": extrair_tabelas_e_cartoes(soup),
                    "data_extracao": datetime.now().isoformat()
                }
            except Exception as e:
                print(f"   [Aviso] Falha ao extrair {url_pub}: {e}")

        # Limpa fila para focar nas internas agora
        urls_para_visitar.clear()

        # 2. Verifica se já está logado e efetua login
        print(f"\nAcessando {BASE_URL} para iniciar sessão...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        fechar_modais_e_popups(page)

        if "login" in page.url.lower():
            print("Sessão não autenticada. Efetuando login...")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)
            fechar_modais_e_popups(page)
            
            # Preenche formulário de login
            page.wait_for_selector("#identificador", timeout=10000)
            page.fill("#identificador", TELEFONE_LOGIN)
            page.fill("#senha", SENHA_LOGIN)
            
            # Marca lembrar conta se existir
            if page.locator("#rememberAccount").count() > 0:
                page.check("#rememberAccount")

            print("Enviando credenciais...")
            page.click("button[type='submit']")

            # Aguarda redirecionamento pós-login
            try:
                page.wait_for_url(lambda u: "login" not in u.lower(), timeout=15000)
                print("[SUCESSO] Login realizado com êxito!")
                fechar_modais_e_popups(page)
            except Exception:
                print("[AVISO] Aguardando confirmação de login... se houver verificação na tela, por favor conclua no navegador.")
                time.sleep(5)
                fechar_modais_e_popups(page)

            # Salva o estado da sessão (cookies/tokens) para evitar logins repetidos
            context.storage_state(path=str(SESSION_FILE))
            print(f"Estado de login salvo em: {SESSION_FILE.name}")
        else:
            print("[INFO] Sessão ativa reconhecida. Não precisou relogar!")
            fechar_modais_e_popups(page)

        # 3. Mapeamento de links e abas internas
        print("\nMapeando abas e rotas internas disponíveis na plataforma...")
        urls_para_visitar.add(page.url)
        coletar_links_pagina()

        # 3. Visita as páginas internas para extração minuciosa
        while urls_para_visitar:
            url_atual = urls_para_visitar.pop()
            if url_atual in urls_visitadas:
                continue

            urls_visitadas.add(url_atual)
            print(f"-> Analisando: {url_atual}")

            try:
                page.goto(url_atual, wait_until="domcontentloaded", timeout=20000)
                time.sleep(1)
                fechar_modais_e_popups(page)
                time.sleep(1)  # Permite scripts assíncronos carregarem tabelas/valores

                # Clicar em eventuais abas secundárias dentro da página (subtabs como VIP 1, VIP 2, etc.)
                sub_tabs = page.locator(".tab, [role='tab'], .nav-link, button.tab-btn").all()
                for tab in sub_tabs[:5]:  # Interage com até 5 abas internas por página se houver
                    try:
                        if tab.is_visible():
                            tab.click(timeout=1000)
                            time.sleep(0.8)
                    except Exception:
                        pass

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                titulo = page.title() or soup.find("h1") or "Sem título"
                if hasattr(titulo, "get_text"):
                    titulo = titulo.get_text(strip=True)

                texto_limpo = extrair_texto_limpo(html)
                tabelas = extrair_tabelas_e_cartoes(soup)

                paginas_coletadas[url_atual] = {
                    "url": url_atual,
                    "titulo": str(titulo),
                    "texto": texto_limpo,
                    "tabelas": tabelas,
                    "data_extracao": datetime.now().isoformat()
                }

                # Descobre novos links navegando
                coletar_links_pagina()

            except Exception as e:
                print(f"   [Aviso] Falha ao processar {url_atual}: {e}")

        browser.close()

    # 4. Salva a base estruturada
    print("\nFinalizando processamento e gravação dos dados...")
    with open(LATEST_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(paginas_coletadas, f, ensure_ascii=False, indent=2)

    # 5. Gera arquivo de texto consolidado para consulta da IA
    with open(KB_TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== BASE OFICIAL DE DADOS DA PLATAFORMA (VINICOLA UVVA) ===\n")
        f.write(f"Última atualização: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n\n")
        for url, info in paginas_coletadas.items():
            f.write(f"\n{'='*50}\n")
            f.write(f"PÁGINA: {info['titulo']}\n")
            f.write(f"URL: {url}\n")
            f.write(f"{'='*50}\n")
            f.write(info['texto'])
            f.write("\n\n")
            if info['tabelas']:
                f.write("--- DADOS ESTRUTURADOS / TABELAS ---\n")
                for tab in info['tabelas']:
                    f.write(tab + "\n")
                f.write("\n")

    print(f"[CONCLUÍDO] {len(paginas_coletadas)} páginas mapeadas e salvas com sucesso!")
    
    # 6. Adiciona conteúdo de PDFs e DOCXs locais na base de conhecimento
    integrar_manuais_locais()

    print(f"Base de conhecimento gerada em: {KB_TEXT_FILE.name}\n")
    return paginas_coletadas

def integrar_manuais_locais():
    """Adiciona conteúdo de PDFs, DOCXs e TXTs locais na base de conhecimento."""
    print("\nProcurando manuais locais (PDF/DOCX) para adicionar à base...")
    import glob
    try:
        from PyPDF2 import PdfReader
        from docx import Document
        
        pdf_files = glob.glob(str(DATA_DIR / "*.pdf"))
        docx_files = glob.glob(str(DATA_DIR / "*.docx"))
        txt_files = glob.glob(str(DATA_DIR / "*.txt"))
        
        with open(KB_TEXT_FILE, "a", encoding="utf-8") as f:
            for pdf_file in pdf_files:
                nome = Path(pdf_file).name
                print(f" -> Extraindo: {nome}")
                f.write(f"\n\n{'='*50}\n")
                f.write(f"DOCUMENTO DE SUPORTE OFICIAL: {nome}\n")
                f.write(f"{'='*50}\n")
                reader = PdfReader(pdf_file)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        f.write(text + "\n")
                        
            for docx_file in docx_files:
                nome = Path(docx_file).name
                print(f" -> Extraindo: {nome}")
                f.write(f"\n\n{'='*50}\n")
                f.write(f"DOCUMENTO DE SUPORTE OFICIAL: {nome}\n")
                f.write(f"{'='*50}\n")
                doc = Document(docx_file)
                for para in doc.paragraphs:
                    if para.text.strip():
                        f.write(para.text + "\n")
                        
            for txt_file in txt_files:
                nome = Path(txt_file).name
                if "base_conhecimento" in nome:
                    continue
                print(f" -> Extraindo: {nome}")
                f.write(f"\n\n{'='*50}\n")
                f.write(f"DOCUMENTO DE SUPORTE OFICIAL: {nome}\n")
                f.write(f"{'='*50}\n")
                with open(txt_file, "r", encoding="utf-8") as tf:
                    f.write(tf.read() + "\n")

            # Processa planilhas Excel (XLSX, XLS)
            excel_files = glob.glob(str(DATA_DIR / "*.xlsx")) + glob.glob(str(DATA_DIR / "*.xls"))
            for excel_file in excel_files:
                nome = Path(excel_file).name
                print(f" -> Extraindo Planilha Excel: {nome}")
                f.write(f"\n\n{'='*50}\n")
                f.write(f"DOCUMENTO DE SUPORTE OFICIAL (PLANILHA EXCEL): {nome}\n")
                f.write(f"{'='*50}\n")
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(excel_file, data_only=True)
                    for sheetname in wb.sheetnames:
                        sheet = wb[sheetname]
                        f.write(f"\n--- Aba: {sheetname} ---\n")
                        for row in sheet.iter_rows(values_only=True):
                            linha_texto = " | ".join([str(celula) for celula in row if celula is not None])
                            if linha_texto.strip():
                                f.write(linha_texto + "\n")
                except Exception as ex_err:
                    print(f"Erro ao extrair Excel {nome}: {ex_err}")
                        
        if pdf_files or docx_files or txt_files or excel_files:
            print("[SUCESSO] Manuais e planilhas locais integrados à inteligência do robô!")
    except Exception as e:
        print(f"[AVISO] Não foi possível processar manuais locais: {e}")

if __name__ == "__main__":
    executar_varredura(headless=False)
