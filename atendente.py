import os
import json
from config import KB_TEXT_FILE, LATEST_DATA_FILE, obter_gemini_api_key

def gerar_system_prompt(atendente_nome: str = "Heitor") -> str:
    nome = "Chloe" if "chloe" in (atendente_nome or "").lower() else "Heitor"
    artigo = "a" if nome == "Chloe" else "o"
    return f"""Você é {artigo} {nome}, Atendente Oficial de Suporte ao Cliente da Vinícola Uvva.
Sua missão é atuar como o próprio suporte, resolvendo as dúvidas dos clientes de forma direta e ativa.

DIRETRIZES FUNDAMENTAIS DE FIDELIDADE:
1. Você deve se basear nas informações oficiais da base de dados (e dos manuais/PDFs fornecidos) para regras de negócio, bônus e valores.
2. VOCÊ É O SUPORTE. NUNCA oriente o cliente a "entrar em contato com o suporte". Você mesmo deve fornecer a solução.
3. Para dúvidas de "como fazer", crie um guia passo a passo claro (ex: "Vá na aba X, clique em Y").
4. Sempre que possível, inclua os caminhos ou URLs das abas relacionadas. IMPORTANTE: NUNCA use formatação markdown para links (não faça `[link](link)`). Apenas escreva a URL diretamente no texto (ex: "Acesse: https://site.com").
5. EXCEÇÃO PARA FLUXOS PADRÕES: Para procedimentos comuns de aplicativos que podem não estar explícitos no texto extraído (como 'Esqueci minha senha' ou 'Problemas de login'), você tem permissão para instruir o fluxo padrão do sistema: "Acesse a tela de login, clique na opção 'Esqueceu a senha?', digite seu número de telefone, aguarde o envio do código por SMS e crie uma nova senha".
6. NUNCA invente ou deduza valores financeiros, porcentagens de lucro ou regras de negócio não documentadas.
7. Se for uma dúvida de negócio muito específica que não está na base, informe educadamente que você irá consultar a supervisão.
8. FORMATO WHATSAPP E OBJETIVIDADE: A resposta será enviada em um grupo de WhatsApp.
   - O cliente pode enviar *MÚLTIPLAS PERGUNTAS* de uma vez só (ex: "Quanto tempo demora o saque? Qual o valor mínimo?").
   - Identifique cada pergunta e responda de forma BEM OBJETIVA, item por item.
   - Respostas curtas (1 a 2 linhas por pergunta). NADA de "textões" ou mensagens gigantescas.
   - Use formatação simples (apenas *negrito* para dar destaque). Não use cabeçalhos markdown como `###`.
   - Use emojis com moderação para deixar o texto amigável.
9. Responda de forma pronta para envio (copy-paste):
   - Saudação cordial se apresentando como {nome} (ex: "Olá! 👋 Me chamo {nome}, sou {artigo} Atendente Oficial de Suporte da Vinícola Uvva...").
   - Respostas curtas e diretas.
   - Encerramento formal colocando-se à disposição.
10. REGRA CRÍTICA PARA SAQUES E RETIRADAS:
   - Os saques na Vinícola Uvva funcionam 24 HORAS POR DIA (24/7) E SÃO INSTANTÂNEOS!
   - Assim que o cliente solicita a retirada na plataforma, o dinheiro cai instantaneamente na conta cadastrada (via PIX ou USDT).
   - NUNCA diga que o saque demora ou leva até 24 horas. "24 horas" refere-se à disponibilidade do sistema (disponível 24 horas por dia, a qualquer momento). O recebimento na conta é IMEDIATO / INSTANTÂNEO.
   - Valores mínimos: R$ 6,00 no PIX e R$ 40,00 no USDT. Taxa padrão de 6% (ou desconto de 50% para membros com Cartão SVIP).
"""

ULTIMO_ERRO_QUOTA = False

def carregar_base_conhecimento() -> str:
    """Lê o texto consolidado extraído do site."""
    if not KB_TEXT_FILE.exists():
        return ""
    try:
        with open(KB_TEXT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler base: {e}"

def responder_duvida(pergunta_cliente: str, atendente_nome: str = "Heitor") -> str:
    """
    Recebe a pergunta do cliente e o nome do atendente (Heitor ou Chloe),
    injeta o contexto da base de dados e aciona a IA para compor a resposta formal.
    """
    nome = "Chloe" if "chloe" in (atendente_nome or "").lower() else "Heitor"
    artigo = "a" if nome == "Chloe" else "o"
    system_prompt = gerar_system_prompt(nome)

    base_texto = carregar_base_conhecimento()
    if not base_texto:
        return (
            "[AVISO] Nenhuma base de dados encontrada!\n"
            "Execute primeiro a opção [1] no menu principal para que o robô faça a varredura do site."
        )

    api_key = obter_gemini_api_key()
    if not api_key:
        # Modo busca textual caso a chave ainda não tenha sido configurada
        print("\n[AVISO] Nenhuma chave do Gemini configurada.")
        print("Realizando localização direta nos dados extraídos do site...\n")
        
        termos = [t.lower() for t in pergunta_cliente.split() if len(t) > 3]
        linhas_correspondentes = []
        for linha in base_texto.splitlines():
            if any(termo in linha.lower() for termo in termos):
                linhas_correspondentes.append(linha)

        if linhas_correspondentes:
            trecho = "\n".join(linhas_correspondentes[:10])
            return (
                f"Olá! 👋 Me chamo {nome}, sou {artigo} Atendente Oficial da Vinícola Uvva.\n\n"
                f"=== DADOS ENCONTRADOS NO SITE ===\n"
                f"{trecho}\n\n"
                "Para que a IA redija a mensagem formal automaticamente, configure sua chave do Gemini no .env ou na Vercel."
            )
        else:
            return f"Olá! 👋 Me chamo {nome}. Nenhum dado relacionado foi encontrado na base extraída do site."

    # Se a chave da API existir, chama o modelo Gemini oficial
    prompt_completo = f"""
{system_prompt}

---
BASE OFICIAL DE DADOS DA PLATAFORMA (EXTRAÍDA DIRETAMENTE DO SITE):
{base_texto}
---

DÚVIDA DO CLIENTE:
"{pergunta_cliente}"

Gere a resposta formal e educada pronta para o cliente agora:
"""

    # Utiliza o SDK google-genai
    from google import genai
    import time
    global ULTIMO_ERRO_QUOTA
    
    client = genai.Client(api_key=api_key)
    
    for tentativa in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_completo
            )
            ULTIMO_ERRO_QUOTA = False
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                ULTIMO_ERRO_QUOTA = True
            if ("503" in str(e) or "429" in str(e)) and tentativa < 2:
                time.sleep(5)
                continue
            return f"[Erro ao consultar a IA]: {e}\nVerifique se a sua chave GEMINI_API_KEY no arquivo .env é válida."

if __name__ == "__main__":
    teste = "Qual a porcentagem do menor produto e como funciona o saque?"
    print(responder_duvida(teste))
