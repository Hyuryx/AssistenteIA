// ==========================================================================
//  Assistente IA Vinícola Uvva - Suporte Oficial ao Cliente
// ==========================================================================

// Configuração da URL da API (Suporta abertura direta via file:// e Vercel)
let API_BASE = '';
if (window.location.protocol === 'file:') {
  const savedUrl = localStorage.getItem('uvva_api_url');
  API_BASE = savedUrl ? savedUrl.replace(/\/+$/, '') : 'http://localhost:8000';
}

document.addEventListener('DOMContentLoaded', () => {
  // Banner de arquivo local (quando aberto direto no disco)
  const localFileBanner = document.getElementById('local-file-banner');
  const currentApiUrlSpan = document.getElementById('current-api-url');
  const btnChangeApiUrl = document.getElementById('btn-change-api-url');

  if (window.location.protocol === 'file:') {
    if (localFileBanner) localFileBanner.style.display = 'flex';
    if (currentApiUrlSpan) currentApiUrlSpan.textContent = API_BASE;
  }

  if (btnChangeApiUrl) {
    btnChangeApiUrl.addEventListener('click', () => {
      const novaUrl = prompt(
        'Digite a URL do seu backend (Vercel ou Servidor Local):\n\nExemplo na Vercel: https://assistente-ia.vercel.app\nExemplo Local: http://localhost:8000',
        API_BASE
      );
      if (novaUrl !== null) {
        const cleanUrl = novaUrl.trim().replace(/\/+$/, '');
        localStorage.setItem('uvva_api_url', cleanUrl);
        API_BASE = cleanUrl;
        if (currentApiUrlSpan) currentApiUrlSpan.textContent = cleanUrl;
        showToast('URL da API configurada para: ' + cleanUrl, 'success');
        atualizarStats();
      }
    });
  }

  // ==================== ATENDIMENTO AO CLIENTE ====================
  const inputQuestion = document.getElementById('input-question');
  const btnSubmit = document.getElementById('btn-submit-question');
  const btnSubmitText = document.getElementById('btn-submit-text');
  const btnSpinner = document.getElementById('btn-spinner');
  const responseContent = document.getElementById('response-content');
  const btnCopy = document.getElementById('btn-copy-response');
  const copyBtnText = document.getElementById('copy-btn-text');
  const btnClear = document.getElementById('btn-clear-question');
  const charCounter = document.getElementById('char-counter');
  const responseTimestamp = document.getElementById('response-timestamp');
  const headerKbBadge = document.getElementById('header-kb-badge');
  const chips = document.querySelectorAll('.chip');

  // Contador de caracteres
  if (inputQuestion && charCounter) {
    inputQuestion.addEventListener('input', () => {
      const len = inputQuestion.value.length;
      charCounter.textContent = `${len} caracteres`;
    });
  }

  // Botão Limpar
  if (btnClear && inputQuestion) {
    btnClear.addEventListener('click', () => {
      inputQuestion.value = '';
      if (charCounter) charCounter.textContent = '0 caracteres';
      inputQuestion.focus();
    });
  }

  // Sugestões Rápidas (Chips)
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.getAttribute('data-question');
      inputQuestion.value = q;
      if (charCounter) charCounter.textContent = `${q.length} caracteres`;
      inputQuestion.focus();
    });
  });

  // Atalho de teclado Ctrl + Enter para enviar
  if (inputQuestion) {
    inputQuestion.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        enviarPergunta();
      }
    });
  }

  if (btnSubmit) {
    btnSubmit.addEventListener('click', enviarPergunta);
  }

  async function enviarPergunta() {
    const question = inputQuestion.value.trim();
    if (!question) {
      showToast('Por favor, digite ou cole uma pergunta.', 'warning');
      inputQuestion.focus();
      return;
    }

    // Estado de carregamento
    btnSubmit.disabled = true;
    btnSubmitText.textContent = 'Consultando base e gerando resposta...';
    btnSpinner.style.display = 'inline-block';
    responseContent.innerHTML = `
      <div class="response-placeholder">
        <div class="spinner" style="width: 32px; height: 32px; border-width: 3px; margin-bottom: 1rem;"></div>
        <p>A IA está lendo o site oficial, os manuais e redigindo a resposta formal...</p>
      </div>
    `;

    const startTime = performance.now();

    try {
      let res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      if (!res.ok && res.status === 404) {
        res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question })
        });
      }
      const data = await res.json();

      const duration = ((performance.now() - startTime) / 1000).toFixed(1);
      if (responseTimestamp) {
        responseTimestamp.textContent = `Gerado em ${duration}s • Pronto para cópia`;
      }

      if (data.success) {
        formatarEExibirResposta(data.answer);
        atualizarStats();
      } else {
        responseContent.innerHTML = `<div style="color: #f87171; padding: 1rem;">${data.answer || 'Erro ao consultar o assistente.'}</div>`;
      }
    } catch (err) {
      responseContent.innerHTML = `
        <div style="color: #f87171; padding: 1rem; line-height: 1.6;">
          <strong>Erro ao conectar com a API:</strong> ${err.message}<br>
          <small style="color: var(--text-dim);">Dica: Se estiver usando o arquivo local, execute <code>iniciar_servidor.bat</code> ou acesse a URL publicada na Vercel.</small>
        </div>
      `;
    } finally {
      btnSubmit.disabled = false;
      btnSubmitText.textContent = 'Consultar Base & Gerar Resposta';
      btnSpinner.style.display = 'none';
    }
  }

  function formatarEExibirResposta(rawText) {
    let formatted = rawText
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*(.*?)\*/g, '<strong style="color: #ffffff;">$1</strong>')
      .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color: var(--accent-purple-light); text-decoration: underline;">$1</a>');
    
    responseContent.innerHTML = `<div style="white-space: pre-wrap; font-size: 0.95rem;">${formatted}</div>`;
  }

  // Copiar para WhatsApp
  if (btnCopy) {
    btnCopy.addEventListener('click', () => {
      const raw = responseContent.innerText;
      if (!raw || raw.includes('Envie uma dúvida ao lado') || raw.includes('A IA está lendo o site')) {
        showToast('Nenhuma resposta pronta para copiar.', 'warning');
        return;
      }

      navigator.clipboard.writeText(raw).then(() => {
        copyBtnText.textContent = 'Copiado!';
        btnCopy.style.background = '#10b981';
        showToast('Mensagem copiada para a área de transferência! Pronta para colar no WhatsApp.', 'success');
        setTimeout(() => {
          copyBtnText.textContent = 'Copiar para WhatsApp';
          btnCopy.style.background = '';
        }, 2500);
      }).catch(err => {
        showToast('Erro ao copiar: ' + err, 'error');
      });
    });
  }

  // ==================== MODAL DE CONSULTA DA BASE DE CONHECIMENTO ====================
  const kbModal = document.getElementById('kb-modal');
  const btnOpenKbModal = document.getElementById('btn-open-kb-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const modalKbText = document.getElementById('modal-kb-text');
  const modalKbSubtitle = document.getElementById('modal-kb-subtitle');
  const modalKbSearch = document.getElementById('modal-kb-search');
  
  // Elementos do Medidor de Inteligência (0% a 100%)
  const intelPercentage = document.getElementById('intel-percentage');
  const intelBar = document.getElementById('intel-bar');
  const intelLevelText = document.getElementById('intel-level-text');
  const intelPages = document.getElementById('intel-pages');
  const intelDocs = document.getElementById('intel-docs');
  const intelSize = document.getElementById('intel-size');
  const intelQuestions = document.getElementById('intel-questions');

  let rawKbFullText = '';

  function renderizarInteligencia(data) {
    if (!data) return;
    const score = data.intelligence_score ?? data.knowledge_base?.intelligence_score ?? 0;
    const level = data.intelligence_level ?? data.knowledge_base?.intelligence_level ?? 'Nível Operacional';
    const pages = data.total_pages ?? data.knowledge_base?.total_pages ?? 0;
    const docs = data.total_documents ?? data.knowledge_base?.total_documents ?? 0;
    const size = data.kb_size_kb ?? data.knowledge_base?.kb_size_kb ?? 0;
    const questions = data.questions_answered ?? data.knowledge_base?.questions_answered ?? 0;

    if (intelPercentage) intelPercentage.textContent = `${score}%`;
    if (intelBar) intelBar.style.width = `${score}%`;
    if (intelLevelText) intelLevelText.textContent = level;
    if (intelPages) intelPages.textContent = pages;
    if (intelDocs) intelDocs.textContent = docs;
    if (intelSize) intelSize.textContent = `${size} KB`;
    if (intelQuestions) intelQuestions.textContent = questions;
  }

  if (btnOpenKbModal && kbModal) {
    btnOpenKbModal.addEventListener('click', async () => {
      kbModal.style.display = 'flex';
      modalKbText.textContent = 'Carregando texto da base oficial...';
      try {
        let res = await fetch(`${API_BASE}/api/knowledge-base`);
        if (!res.ok && res.status === 404) {
          res = await fetch(`${API_BASE}/knowledge-base`);
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        rawKbFullText = data.content || 'Base vazia.';
        modalKbText.textContent = rawKbFullText;
        if (modalKbSubtitle) {
          modalKbSubtitle.textContent = `${(rawKbFullText.length / 1024).toFixed(1)} KB • ${(rawKbFullText.split('\n').length)} linhas`;
        }
        renderizarInteligencia(data);
      } catch (err) {
        modalKbText.textContent = `Atenção: Não foi possível carregar a base de dados.\n\nMotivo: ${err.message}\n\n• Se você abriu o arquivo direto pelo computador: dê 2 cliques no arquivo 'iniciar_servidor.bat' na pasta do projeto para iniciar o backend local.\n• Se estiver usando a versão web da Vercel: certifique-se de que a publicação foi concluída.`;
      }
    });
  }

  if (btnCloseModal && kbModal) {
    btnCloseModal.addEventListener('click', () => {
      kbModal.style.display = 'none';
      if (modalKbSearch) modalKbSearch.value = '';
    });
    kbModal.addEventListener('click', (e) => {
      if (e.target === kbModal) {
        kbModal.style.display = 'none';
        if (modalKbSearch) modalKbSearch.value = '';
      }
    });
  }

  // Busca rápida no modal da base
  if (modalKbSearch && modalKbText) {
    modalKbSearch.addEventListener('input', () => {
      const term = modalKbSearch.value.trim().toLowerCase();
      if (!term || !rawKbFullText) {
        modalKbText.textContent = rawKbFullText;
        return;
      }
      const lines = rawKbFullText.split('\n');
      const filtered = lines.filter(l => l.toLowerCase().includes(term));
      if (filtered.length > 0) {
        modalKbText.textContent = `--- Encontradas ${filtered.length} linhas contendo "${term}": ---\n\n` + filtered.join('\n');
      } else {
        modalKbText.textContent = `Nenhum trecho encontrado contendo "${term}".`;
      }
    });
  }

  // ==================== ESTATÍSTICAS E STATUS DINÂMICO ====================
  const badgeApiStatus = document.getElementById('badge-api-status');
  const badgeKbStatus = document.getElementById('badge-kb-status');

  async function atualizarStats() {
    try {
      let res = await fetch(`${API_BASE}/api/stats`);
      if (!res.ok && res.status === 404) {
        res = await fetch(`${API_BASE}/stats`);
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Renderiza medidor de inteligência em tempo real
      renderizarInteligencia(data);

      // 1. Atualiza Badge da API Key (Verde = Ativa, Laranja = Esgotada, Vermelho = Offline)
      if (badgeApiStatus) {
        const apiKeyInfo = data.api_key || {};
        const color = apiKeyInfo.color || (data.has_api_key ? 'green' : 'red');
        const label = apiKeyInfo.label || (data.has_api_key ? 'Ativa' : 'Offline');

        badgeApiStatus.textContent = label;
        badgeApiStatus.className = `badge-pill badge-status-${color}`;
        badgeApiStatus.title = apiKeyInfo.desc || `Status: ${label}`;
      }

      // 2. Atualiza Badge da Base de Dados (Verde = Ativa, Laranja = Em Manutenção, Vermelho = Offline)
      if (badgeKbStatus) {
        const kbInfo = data.knowledge_base || {};
        const color = kbInfo.color || (data.total_pages > 0 ? 'green' : 'red');
        const label = kbInfo.label || (data.total_pages > 0 ? `Ativa (${data.total_pages} Páginas)` : 'Offline');

        badgeKbStatus.textContent = label;
        badgeKbStatus.className = `badge-pill badge-status-${color}`;
        badgeKbStatus.title = kbInfo.desc || `Status: ${label}`;
      }
    } catch (err) {
      // Se não conseguir conectar com a API ou se estiver offline
      if (badgeApiStatus) {
        badgeApiStatus.textContent = 'Offline';
        badgeApiStatus.className = 'badge-pill badge-status-red';
        badgeApiStatus.title = 'Servidor local não iniciado ou API inacessível';
      }
      if (badgeKbStatus) {
        badgeKbStatus.textContent = 'Offline';
        badgeKbStatus.className = 'badge-pill badge-status-red';
        badgeKbStatus.title = 'Base de dados inacessível';
      }
    }
  }

  // Atualiza imediatamente e verifica a cada 30 segundos
  atualizarStats();
  setInterval(atualizarStats, 30000);
});

// ==================== TOAST FEEDBACK ====================
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'warning') icon = '⚠️';
  if (type === 'error') icon = '❌';

  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideDown 0.3s ease reverse forwards';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
