import sys
import os
from datetime import datetime
from config import KB_TEXT_FILE, LATEST_DATA_FILE, CHANGELOG_FILE
from scraper import executar_varredura
from detector_mudancas import comparar_versoes
from atendente import responder_duvida

def limpar_tela():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    print(r"""
==================================================================
           ASSISTENTE DE SUPORTE - VINÍCOLA UVVA
              Varredura Total & Respostas com IA
==================================================================
    """)

def exibir_resumo():
    if not LATEST_DATA_FILE.exists():
        print("\n[AVISO] Nenhuma base de dados encontrada.")
        print("Execute a opção [1] para varrer o site primeiro.\n")
        return

    import json
    with open(LATEST_DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)

    print(f"\nTotal de páginas mapeadas: {len(dados)}")
    print("-" * 50)
    for url, info in dados.items():
        print(f"• {info.get('titulo', 'Sem título')[:40]:<40} -> {url}")
    print("-" * 50 + "\n")

def menu_atendimento():
    print("\n" + "=" * 60)
    print("  MODO ATENDIMENTO AO CLIENTE (Digite 'voltar' para sair)")
    print("=" * 60)
    
    while True:
        pergunta = input("\n[Dúvida do Cliente] > ").strip()
        if not pergunta:
            continue
        if pergunta.lower() in ["voltar", "sair", "exit"]:
            break

        print("\nConsultando base oficial do site e gerando resposta...")
        resposta = responder_duvida(pergunta)
        
        print("\n" + "-" * 60)
        print("RESPOSTA PRONTA PARA ENVIAR AO CLIENTE:")
        print("-" * 60)
        print(resposta)
        print("-" * 60)

def main():
    while True:
        banner()
        print("Escolha uma opção:")
        print("  [1] Sincronizar e Varrer o Site (Atualizar dados de todas as abas)")
        print("  [2] Atender Dúvida de Cliente (Gerar mensagem formal e educada)")
        print("  [3] Ver Alterações e Novidades Detectadas no Site")
        print("  [4] Ver Resumo das Páginas Mapeadas")
        print("  [0] Sair")
        
        opcao = input("\nDigite a opção desejada [0-4]: ").strip()

        if opcao == "1":
            print("\nVocê deseja ver o navegador abrindo ou rodar em segundo plano?")
            print("  [1] Visível (Recomendado na primeira vez para acompanhar o login)")
            print("  [2] Segundo plano (Invisível/Silencioso)")
            modo = input("Escolha [1 ou 2, padrão 1]: ").strip()
            headless = (modo == "2")
            
            executar_varredura(headless=headless)
            print("\nVerificando alterações em relação ao dia anterior...")
            mudancas = comparar_versoes()
            for linha in mudancas:
                print(linha)
            
            # Atualiza os arquivos locais de Word/TXT com base nas mudanças
            from atualizador_arquivos import atualizar_arquivos_locais
            atualizar_arquivos_locais(mudancas)
            
            input("\nPressione Enter para continuar...")

        elif opcao == "2":
            menu_atendimento()

        elif opcao == "3":
            print("\n" + "=" * 60)
            print("HISTÓRICO DE ALTERAÇÕES DETECTADAS:")
            print("=" * 60)
            mudancas = comparar_versoes()
            for linha in mudancas:
                print(linha)
            input("\nPressione Enter para continuar...")

        elif opcao == "4":
            exibir_resumo()
            input("Pressione Enter para continuar...")

        elif opcao == "0":
            print("\nEncerrando assistente. Bom trabalho no atendimento!\n")
            sys.exit(0)

        else:
            print("\nOpção inválida! Tente novamente.")
            input("Pressione Enter para continuar...")
        
        limpar_tela()

if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        print("\n" + "=" * 60)
        print("OCORREU UM ERRO FATAL:")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        input("\nPressione Enter para fechar a janela...")
