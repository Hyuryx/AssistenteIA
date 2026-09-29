// ==========================================================================
//  Assistente IA Vinícola Uvva - Lógica do Frontend Web
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Elementos das Abas
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // Navegação entre abas
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      
      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetTab);
      if (targetPane) targetPane.classList.add('active');

      // Atualiza dados sob demanda quando a aba é aberta
      if (targetTab === 'tab-conhecimento') carregarDocumentos();
      if (targetTab === 'tab-mudancas') carregarChangelog();
      if (targetTab === 'tab-paginas') carregarPaginas();
      if (targetTab === 'tab-config') carregarConfiguracoes();
    });
  });

  // ==================== ABA 1: ATENDIMENTO AO CLIENTE ====================
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
  const chips = document.querySelectorAll('.chip');

  // Contador de caracteres
  inputQuestion.addEventListener('input', () => {
    const len = inputQuestion.value.length;
    charCounter.textContent = `${len} caracteres`;
  });

  // Botão Limpar
  btnClear.addEventListener('click', () => {
    inputQuestion.value = '';
    charCounter.textContent = '0 caracteres';
    inputQuestion.focus();
  });

  // Sugestões Rápidas (Chips)
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.getAttribute('data-question');
      inputQuestion.value = q;
      charCounter.textContent = `${q.length} caracteres`;
      inputQuestion.focus();
    });
  });

  // Atalho de teclado Ctrl + Enter para enviar
  inputQuestion.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      enviarPergunta();
    }
  });

  btnSubmit.addEventListener('click', enviarPergunta);

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
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      const data = await res.json();

      const duration = ((performance.now() - startTime) / 1000).toFixed(1);
      responseTimestamp.textContent = `Gerado em ${duration}s • Pronto para cópia`;

      if (data.success) {
        formatarEExibirResposta(data.answer);
      } else {
        responseContent.innerHTML = `<div style="color: #f87171; padding: 1rem;">${data.answer || 'Erro ao consultar o assistente.'}</div>`;
      }
    } catch (err) {
      responseContent.innerHTML = `<div style="color: #f87171; padding: 1rem;">Erro de conexão com o servidor: ${err.message}</div>`;
    } finally {
      btnSubmit.disabled = false;
      btnSubmitText.textContent = 'Consultar Base & Gerar Resposta';
      btnSpinner.style.display = 'none';
    }
  }

  function formatarEExibirResposta(rawText) {
    // Formata *negrito* para <strong> e links para texto destacado
    let formatted = rawText
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*(.*?)\*/g, '<strong style="color: #ffffff;">$1</strong>')
      .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color: var(--accent-purple-light); text-decoration: underline;">$1</a>');
    
    responseContent.innerHTML = `<div style="white-space: pre-wrap; font-size: 0.95rem;">${formatted}</div>`;
  }

  // Copiar para WhatsApp
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

  // ==================== ABA 2: BASE DE CONHECIMENTO & UPLOAD ====================
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const documentsTbody = document.getElementById('documents-tbody');

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesUpload(e.dataTransfer.files);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFilesUpload(fileInput.files);
    }
  });

  async function handleFilesUpload(files) {
    for (let file of files) {
      const formData = new FormData();
      formData.append('file', file);

      showToast(`Fazendo upload e extraindo: ${file.name}...`, 'info');

      try {
        const res = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        });
        const result = await res.json();
        if (result.success) {
          showToast(result.message, 'success');
        } else {
          showToast(result.message, 'error');
        }
      } catch (err) {
        showToast(`Erro ao enviar ${file.name}: ${err.message}`, 'error');
      }
    }
    carregarDocumentos();
    atualizarStats();
  }

  async function carregarDocumentos() {
    try {
      const res = await fetch('/api/documents');
      const data = await res.json();
      
      if (!data.documents || data.documents.length === 0) {
        documentsTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-dim); padding: 2rem;">Nenhum documento encontrado.</td></tr>`;
        return;
      }

      documentsTbody.innerHTML = data.documents.map(doc => {
        let badgeClass = 'txt';
        if (doc.extension === '.pdf') badgeClass = 'pdf';
        else if (doc.extension.includes('doc')) badgeClass = 'docx';

        return `
          <tr>
            <td>
              <strong style="${doc.is_main_kb ? 'color: var(--accent-wine-light);' : ''}">${doc.name}</strong>
              ${doc.is_main_kb ? ' <span style="font-size: 0.7rem; background: rgba(159, 18, 57, 0.2); color: #f43f5e; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">Consolidada</span>' : ''}
            </td>
            <td><span class="file-ext-badge ${badgeClass}">${doc.extension.replace('.', '').toUpperCase()}</span></td>
            <td>${doc.size_kb} KB</td>
            <td>${doc.modified}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      documentsTbody.innerHTML = `<tr><td colspan="4" style="color: #f87171; text-align: center;">Erro ao carregar documentos: ${err.message}</td></tr>`;
    }
  }

  // Inspecionar Base Bruta (Modal)
  const kbModal = document.getElementById('kb-modal');
  const btnViewRawKb = document.getElementById('btn-view-raw-kb');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const modalKbText = document.getElementById('modal-kb-text');

  btnViewRawKb.addEventListener('click', async () => {
    kbModal.style.display = 'flex';
    modalKbText.textContent = 'Carregando texto da base...';
    try {
      const res = await fetch('/api/knowledge-base');
      const data = await res.json();
      modalKbText.textContent = data.content || 'Base vazia.';
    } catch (err) {
      modalKbText.textContent = 'Erro ao carregar base: ' + err.message;
    }
  });

  btnCloseModal.addEventListener('click', () => {
    kbModal.style.display = 'none';
  });

  // ==================== ABA 3: SINCRONIZAR E VARRER SITE ====================
  const btnTriggerSync = document.getElementById('btn-trigger-sync');
  const syncHeadless = document.getElementById('sync-headless');
  const syncTerminal = document.getElementById('sync-terminal-body');
  const syncLastTime = document.getElementById('sync-last-time');

  let syncPollingInterval = null;

  btnTriggerSync.addEventListener('click', async () => {
    btnTriggerSync.disabled = true;
    showToast('Iniciando varredura da plataforma...', 'info');

    try {
      const res = await fetch(`/api/sync?headless=${syncHeadless.checked}`, { method: 'POST' });
      const data = await res.json();

      if (data.success) {
        startSyncPolling();
      } else {
        showToast(data.message, 'warning');
        btnTriggerSync.disabled = false;
      }
    } catch (err) {
      showToast('Erro ao iniciar varredura: ' + err.message, 'error');
      btnTriggerSync.disabled = false;
    }
  });

  function startSyncPolling() {
    if (syncPollingInterval) clearInterval(syncPollingInterval);
    syncPollingInterval = setInterval(async () => {
      try {
        const res = await fetch('/api/sync/status');
        const state = await res.json();

        if (state.logs && state.logs.length > 0) {
          syncTerminal.innerHTML = state.logs.map(log => {
            let cls = '';
            if (log.includes('ERRO') || log.includes('Erro')) cls = 'error';
            else if (log.includes('concluída') || log.includes('SUCESSO')) cls = 'success';
            return `<div class="terminal-line ${cls}">> ${log}</div>`;
          }).join('');
          syncTerminal.scrollTop = syncTerminal.scrollHeight;
        }

        if (state.last_sync) {
          syncLastTime.textContent = `Última: ${state.last_sync}`;
        }

        if (!state.is_running) {
          clearInterval(syncPollingInterval);
          btnTriggerSync.disabled = false;
          atualizarStats();
          if (state.status === 'success') {
            showToast('Varredura e sincronização finalizadas com sucesso!', 'success');
          }
        }
      } catch (e) {
        console.error("Erro no polling da varredura:", e);
      }
    }, 2000);
  }

  // ==================== ABA 4: ALTERAÇÕES E NOVIDADES ====================
  const changelogContainer = document.getElementById('changelog-container');
  const btnRefreshChangelog = document.getElementById('btn-refresh-changelog');

  btnRefreshChangelog.addEventListener('click', carregarChangelog);

  async function carregarChangelog() {
    changelogContainer.innerHTML = `<div style="color: var(--text-dim); padding: 1rem; text-align: center;">Buscando alterações...</div>`;
    try {
      const res = await fetch('/api/changelog');
      const data = await res.json();
      
      if (!data.changelog || data.changelog.length === 0) {
        changelogContainer.innerHTML = `<div style="color: var(--text-muted); padding: 1.5rem; text-align: center;">Nenhuma alteração registrada até o momento.</div>`;
        return;
      }

      changelogContainer.innerHTML = data.changelog.map(item => {
        let badgeColor = 'rgba(255, 255, 255, 0.05)';
        let textColor = '#cbd5e1';
        let prefix = '📌';

        if (item.includes('NOVA PÁGINA')) {
          badgeColor = 'rgba(16, 185, 129, 0.15)';
          textColor = '#34d399';
          prefix = '🆕';
        } else if (item.includes('REMOVIDA')) {
          badgeColor = 'rgba(239, 68, 68, 0.15)';
          textColor = '#f87171';
          prefix = '🗑️';
        } else if (item.includes('ALTERAÇÃO')) {
          badgeColor = 'rgba(245, 158, 11, 0.15)';
          textColor = '#fbbf24';
          prefix = '⚡';
        }

        return `
          <div style="background: ${badgeColor}; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem 1.25rem; font-size: 0.9rem; color: ${textColor}; display: flex; align-items: center; gap: 0.75rem;">
            <span>${prefix}</span>
            <span>${item}</span>
          </div>
        `;
      }).join('');
    } catch (err) {
      changelogContainer.innerHTML = `<div style="color: #f87171; padding: 1rem;">Erro ao carregar histórico: ${err.message}</div>`;
    }
  }

  // ==================== ABA 5: PÁGINAS MAPEADAS ====================
  const pagesGrid = document.getElementById('pages-grid');
  const filterPagesInput = document.getElementById('filter-pages-input');
  let todasPaginas = [];

  filterPagesInput.addEventListener('input', () => {
    const term = filterPagesInput.value.toLowerCase();
    const filtradas = todasPaginas.filter(p => 
      p.title.toLowerCase().includes(term) || p.url.toLowerCase().includes(term)
    );
    renderizarPaginas(filtradas);
  });

  async function carregarPaginas() {
    try {
      const res = await fetch('/api/pages');
      const data = await res.json();
      todasPaginas = data.pages || [];
      renderizarPaginas(todasPaginas);
    } catch (err) {
      pagesGrid.innerHTML = `<div style="color: #f87171; padding: 2rem;">Erro ao carregar páginas: ${err.message}</div>`;
    }
  }

  function renderizarPaginas(lista) {
    if (!lista || lista.length === 0) {
      pagesGrid.innerHTML = `<div style="color: var(--text-dim); padding: 2rem; grid-column: 1/-1; text-align: center;">Nenhuma página encontrada. Execute a opção de varredura primeiro.</div>`;
      return;
    }

    pagesGrid.innerHTML = lista.map(p => `
      <div class="glass-card" style="padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="font-size: 0.75rem; color: var(--accent-purple-light); word-break: break-all; margin-bottom: 0.3rem;">${p.url}</div>
          <h3 style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; color: #fff;">${p.title}</h3>
          <p style="font-size: 0.8rem; color: var(--text-dim); line-height: 1.5; margin-bottom: 1rem;">${p.text_snippet}</p>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 0.75rem; font-size: 0.75rem; color: var(--text-muted);">
          <span>${p.tables_count > 0 ? `📊 ${p.tables_count} tabelas extraídas` : 'Texto simples'}</span>
          <a href="${p.url}" target="_blank" style="color: var(--accent-cyan); text-decoration: none;">Acessar ↗</a>
        </div>
      </div>
    `).join('');
  }

  // ==================== ABA 6: CONFIGURAÇÕES ====================
  const configForm = document.getElementById('config-form');
  const cfgGeminiKey = document.getElementById('cfg-gemini-key');
  const cfgTelefone = document.getElementById('cfg-telefone');
  const cfgSenha = document.getElementById('cfg-senha');

  async function carregarConfiguracoes() {
    try {
      const res = await fetch('/api/config');
      const conf = await res.json();
      if (conf.gemini_api_key_masked) {
        cfgGeminiKey.placeholder = `Chave configurada: (${conf.gemini_api_key_masked})`;
      }
      if (conf.telefone_login) {
        cfgTelefone.value = conf.telefone_login;
      }
    } catch (e) {
      console.error("Erro ao carregar configurações:", e);
    }
  }

  configForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {};
    if (cfgGeminiKey.value.trim()) payload.gemini_api_key = cfgGeminiKey.value.trim();
    if (cfgTelefone.value.trim()) payload.telefone_login = cfgTelefone.value.trim();
    if (cfgSenha.value.trim()) payload.senha_login = cfgSenha.value.trim();

    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        showToast('Configurações salvas com sucesso!', 'success');
        cfgGeminiKey.value = '';
        cfgSenha.value = '';
        carregarConfiguracoes();
        atualizarStats();
      }
    } catch (err) {
      showToast('Erro ao salvar configurações: ' + err.message, 'error');
    }
  });

  // ==================== ATUALIZAÇÃO GERAL DE MÉTRICAS ====================
  async function atualizarStats() {
    try {
      const res = await fetch('/api/stats');
      const stats = await res.json();

      document.getElementById('stat-total-docs').textContent = stats.total_documents || 0;
      document.getElementById('stat-kb-size').textContent = `${stats.kb_size_kb || 0} KB`;
      document.getElementById('stat-kb-lines').textContent = stats.kb_lines || 0;

      const headerKb = document.getElementById('header-kb-badge');
      if (headerKb) headerKb.textContent = `Base: ${stats.kb_size_kb} KB (${stats.kb_lines} linhas)`;

      const statusPill = document.getElementById('status-pill');
      if (stats.has_api_key) {
        statusPill.textContent = 'IA Pronta';
        statusPill.className = 'badge-pill status-online';
      } else {
        statusPill.textContent = 'Sem API Key';
        statusPill.className = 'badge-pill';
      }
    } catch (e) {
      console.error("Erro ao atualizar stats:", e);
    }
  }

  // Toast Notificações
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    else if (type === 'error') icon = '❌';
    else if (type === 'warning') icon = '⚠️';

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideIn 0.3s ease reverse forwards';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Inicializa dados na carga
  atualizarStats();
});
