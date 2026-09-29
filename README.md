# 🍇 Assistente IA - Vinícola Uvva (Web App & Inteligência)

Sistema inteligente com **Interface Web Moderna (Single Page App)** para suporte ao cliente, detecção diária de alterações nas regras da plataforma, integração dinâmica de documentos (PDF, Word, TXT) e geração de respostas 100% fiéis aos fatos com Google Gemini.

---

## 🌟 Funcionalidades do Web App

1. **💬 Atendimento ao Cliente (Split-Screen)**:
   - Painel esquerdo com sugestões rápidas e campo de texto com atalho `Ctrl + Enter`.
   - Painel direito com a resposta do atendente oficial (Heitor), formatada e com **botão de 1 clique para copiar direto para o WhatsApp**.
2. **📁 Base de Conhecimento & Upload Universal**:
   - Arraste e solte **qualquer arquivo** (`.pdf`, `.docx`, `.txt`, `.csv`, `.json`, `.md`).
   - O sistema extrai o conteúdo imediatamente e incorpora na memória da IA.
   - Inspetor visual do texto bruto consolidado.
3. **🕷️ Sincronização & Varredura do Site**:
   - Robô automatizado que faz login, clica em todas as abas e atualiza a base com terminal visual em tempo real.
4. **📊 Alterações e Novidades Detectadas**:
   - Comparativo visual destacando novas páginas, regras alteradas e exclusões.
5. **🗺️ Páginas Mapeadas**:
   - Catálogo de todas as URLs e tabelas arquivadas com filtro de busca em tempo real.
6. **⚙️ Configurações Integradas**:
   - Ajuste sua chave Gemini e credenciais diretamente pela interface web.

---

## 🚀 Como Executar Localmente

### Opção 1: Duplo clique (Mais fácil)
Basta clicar duas vezes em **`iniciar_web.bat`**. O servidor iniciará e seu navegador abrirá automaticamente em:
👉 **`http://localhost:8000`**

### Opção 2: Pelo Terminal
```powershell
.\venv\Scripts\activate
python app.py
```

*(Se preferir o modo terminal antigo por texto, basta executar `python main.py` ou `iniciar.bat`).*

---

## ☁️ Deploy no GitHub e Vercel

### 1. Inicializar e Enviar para o GitHub
```powershell
git init
git add .
git commit -m "feat: transforma em Web App com suporte a upload de arquivos e deploy Vercel"
git branch -M main
git remote add origin https://github.com/Hyuryx/AssistenteIA.git
git push -u origin main
```

> **Atenção:** O arquivo `.env` e as credenciais estão protegidos pelo `.gitignore` e **nunca** serão enviados para o repositório público.

### 2. Configurar na Vercel
1. Acesse [vercel.com](https://vercel.com/) e clique em **"Add New Project"**.
2. Importe o repositório **`AssistenteIA`**.
3. Na seção **Environment Variables**, adicione:
   - `GEMINI_API_KEY`: Sua chave obtida no [Google AI Studio](https://aistudio.google.com/).
   - `TELEFONE_LOGIN`: Seu telefone de acesso à plataforma.
   - `SENHA_LOGIN`: Sua senha de acesso.
4. Clique em **Deploy**! O `vercel.json` e a pasta `api/` já estão configurados para o deploy serverless.

---

## 🔒 Segurança e Privacidade
- Respostas da IA estritamente balizadas na base consolidada (`base_conhecimento.txt`).
- Nenhuma chave ou credencial é exposta em repositórios públicos.
