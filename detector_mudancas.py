import json
import difflib
from datetime import datetime
from config import LATEST_DATA_FILE, PREVIOUS_DATA_FILE, CHANGELOG_FILE

def comparar_versoes() -> list:
    """
    Compara o conteúdo atual com a versão da varredura anterior
    e retorna uma lista de novidades e modificações detectadas.
    """
    if not LATEST_DATA_FILE.exists():
        return ["Nenhuma base de dados encontrada. Execute a opção 1 primeiro."]

    if not PREVIOUS_DATA_FILE.exists():
        return ["Esta é a primeira varredura registrada. Não há dados anteriores para comparação."]

    try:
        with open(LATEST_DATA_FILE, "r", encoding="utf-8") as f:
            dados_novos = json.load(f)
        with open(PREVIOUS_DATA_FILE, "r", encoding="utf-8") as f:
            dados_antigos = json.load(f)
    except Exception as e:
        return [f"Erro ao ler arquivos de comparação: {e}"]

    mudancas = []
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # 1. Verifica novas páginas
    novas_urls = set(dados_novos.keys()) - set(dados_antigos.keys())
    for url in novas_urls:
        mudancas.append(f"[NOVA PÁGINA ADICIONADA] {dados_novos[url].get('titulo', 'Sem título')} ({url})")

    # 2. Verifica páginas removidas
    removidas_urls = set(dados_antigos.keys()) - set(dados_novos.keys())
    for url in removidas_urls:
        mudancas.append(f"[PÁGINA REMOVIDA] {dados_antigos[url].get('titulo', 'Sem título')} ({url})")

    # 3. Compara conteúdo de páginas comuns
    urls_comuns = set(dados_novos.keys()).intersection(set(dados_antigos.keys()))
    for url in urls_comuns:
        texto_antigo = dados_antigos[url].get("texto", "").splitlines()
        texto_novo = dados_novos[url].get("texto", "").splitlines()

        diff = list(difflib.unified_diff(texto_antigo, texto_novo, lineterm=""))
        linhas_adicionadas = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++") and len(l) > 3]
        linhas_removidas = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---") and len(l) > 3]

        if linhas_adicionadas or linhas_removidas:
            mudancas.append(f"\n[ALTERAÇÃO NA PÁGINA] {dados_novos[url].get('titulo', 'Sem título')} ({url}):")
            if linhas_adicionadas:
                mudancas.append(f"  + Adicionado ({len(linhas_adicionadas)} linhas/termos):")
                for item in linhas_adicionadas[:5]:  # Exibe até 5 destaques
                    mudancas.append(f"      • {item}")
            if linhas_removidas:
                mudancas.append(f"  - Modificado/Removido ({len(linhas_removidas)} linhas/termos):")
                for item in linhas_removidas[:5]:
                    mudancas.append(f"      • {item}")

    # Registra no log
    if mudancas:
        with open(CHANGELOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"REGISTRO DE MUDANÇAS - {timestamp}\n")
            f.write(f"{'='*60}\n")
            for m in mudancas:
                f.write(m + "\n")
    else:
        mudancas.append("Nenhuma alteração detectada desde a última varredura. Todas as regras e valores permanecem idênticos.")

    return mudancas

if __name__ == "__main__":
    resultado = comparar_versoes()
    for linha in resultado:
        print(linha)
