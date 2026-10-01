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

  // ==================== SELETOR DE ATENDENTE (HEITOR / CHLOE) ====================
  let currentAttendant = localStorage.getItem('uvva_selected_attendant') || 'Heitor';
  const btnAttendantHeitor = document.getElementById('btn-attendant-heitor');
  const btnAttendantChloe = document.getElementById('btn-attendant-chloe');
  const activeAttendantIndicator = document.getElementById('active-attendant-indicator');
  const responseAttendantName = document.getElementById('response-attendant-name');

  function setAttendant(name) {
    currentAttendant = name;
    localStorage.setItem('uvva_selected_attendant', name);

    if (btnAttendantHeitor && btnAttendantChloe) {
      if (name === 'Chloe') {
        btnAttendantChloe.classList.add('active');
        btnAttendantHeitor.classList.remove('active');
      } else {
        btnAttendantHeitor.classList.add('active');
        btnAttendantChloe.classList.remove('active');
      }
    }

    if (activeAttendantIndicator) {
      activeAttendantIndicator.textContent = `${name} (Ativo)`;
    }
    if (responseAttendantName) {
      responseAttendantName.textContent = name;
    }
  }

  // Inicializa estado do atendente
  setAttendant(currentAttendant);

  if (btnAttendantHeitor) {
    btnAttendantHeitor.addEventListener('click', () => setAttendant('Heitor'));
  }
  if (btnAttendantChloe) {
    btnAttendantChloe.addEventListener('click', () => setAttendant('Chloe'));
  }

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
      accumulatedFiles = [];
      if (typeof updateImagePreviews === 'function') updateImagePreviews();
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

  const fileUpload = document.getElementById('file-upload');
  const fileCount = document.getElementById('file-count');

  if (fileUpload && fileCount) {
    fileUpload.addEventListener('change', () => {
      const count = fileUpload.files.length;
      fileCount.textContent = count > 0 ? `${count} anexo(s)` : '';
    });
  }

  // ==================== GRAVAÇÃO DE ÁUDIO (Speech to Text) ====================
  const btnRecordAudio = document.getElementById('btn-record-audio');
  const audioVisualizer = document.getElementById('audio-visualizer');
  const waveBars = document.querySelectorAll('.wave-bar');
  let isRecording = false;
  let recognition = null;
  let audioContext = null;
  let analyser = null;
  let microphone = null;
  let animationFrameId = null;
  let stream = null;

  if (btnRecordAudio) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.lang = 'pt-BR';
      recognition.interimResults = false;
      recognition.continuous = true; // Mantém gravando até pararmos

      recognition.onstart = async () => {
        isRecording = true;
        btnRecordAudio.style.display = 'none';
        if (audioVisualizer) audioVisualizer.style.display = 'flex';
        showToast('Gravando... Fale agora. O áudio será finalizado após 6s de silêncio.', 'info');
        
        try {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
          analyser = audioContext.createAnalyser();
          microphone = audioContext.createMediaStreamSource(stream);
          microphone.connect(analyser);
          analyser.fftSize = 256;
          
          const bufferLength = analyser.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);
          let lastSoundTime = Date.now();
          
          function updateWaves() {
            if (!isRecording) return;
            analyser.getByteFrequencyData(dataArray);
            
            let sum = 0;
            for(let i = 0; i < bufferLength; i++) {
              sum += dataArray[i];
            }
            const average = sum / bufferLength;

            // Detecta silêncio (média muito baixa) por 6 segundos para parar
            if (average > 2) {
              lastSoundTime = Date.now();
            } else if (Date.now() - lastSoundTime > 6000) {
              showToast('Áudio finalizado automaticamente por silêncio.', 'info');
              stopRecording();
              return;
            }

            const normalized = Math.min(average / 50, 1);
            
            waveBars.forEach((bar) => {
              const noise = Math.random() * 0.4;
              const height = 4 + (normalized * 20 * (1 + noise));
              bar.style.height = `${Math.max(4, height)}px`;
            });
            
            animationFrameId = requestAnimationFrame(updateWaves);
          }
          updateWaves();
        } catch (err) {
          console.warn('Erro ao obter áudio para ondas visuais:', err);
        }
      };

      recognition.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          const currentVal = inputQuestion.value.trim();
          inputQuestion.value = currentVal ? currentVal + ' ' + finalTranscript : finalTranscript;
          if (charCounter) charCounter.textContent = `${inputQuestion.value.length} caracteres`;
        }
      };

      recognition.onerror = (event) => {
        if (event.error !== 'no-speech') {
          showToast('Erro no reconhecimento de voz: ' + event.error, 'error');
        }
        // Em caso de no-speech da API, ignoramos se ainda estamos gravando
      };

      recognition.onend = () => {
        // Se a API parar sozinha por algum motivo que não foi nós chamando stopRecording
        if (isRecording) {
          // Restart para forçar continuar escutando até o timeout de 6s atuar
          try { recognition.start(); } catch(e) {}
        }
      };
    } else {
      btnRecordAudio.style.display = 'none';
      console.warn("SpeechRecognition não suportado neste navegador.");
    }

    function stopRecording() {
      if (recognition && isRecording) {
        try { recognition.stop(); } catch(e) {}
        isRecording = false;
        btnRecordAudio.style.display = 'flex';
        if (audioVisualizer) audioVisualizer.style.display = 'none';
        showToast('Gravação finalizada.', 'success');
        
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        if (microphone) microphone.disconnect();
        if (analyser) analyser.disconnect();
        if (audioContext && audioContext.state !== 'closed') audioContext.close();
        if (stream) stream.getTracks().forEach(t => t.stop());
      }
    }
    
    window.stopVoiceRecording = stopRecording;

    btnRecordAudio.addEventListener('click', () => {
      if (!recognition) {
        showToast('Reconhecimento de voz não suportado neste navegador.', 'error');
        return;
      }
      if (isRecording) {
        stopRecording();
      } else {
        recognition.start();
      }
    });

    if (audioVisualizer) {
      audioVisualizer.addEventListener('click', () => {
        stopRecording();
      });
    }
  }

  // ==================== COLAR E GERENCIAR IMAGENS ====================
  const imagePreviewContainer = document.getElementById('image-preview-container');
  let accumulatedFiles = [];

  function updateImagePreviews() {
    if (!imagePreviewContainer) return;
    imagePreviewContainer.innerHTML = '';
    const dt = new DataTransfer();
    
    accumulatedFiles.forEach((file, index) => {
      dt.items.add(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        wrapper.style.width = '64px';
        wrapper.style.height = '64px';
        wrapper.style.borderRadius = '8px';
        wrapper.style.overflow = 'hidden';
        wrapper.style.border = '2px solid var(--border-subtle)';
        wrapper.style.boxShadow = '0 2px 4px rgba(0,0,0,0.5)';
        
        const img = document.createElement('img');
        img.src = e.target.result;
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '×';
        removeBtn.style.position = 'absolute';
        removeBtn.style.top = '2px';
        removeBtn.style.right = '2px';
        removeBtn.style.background = 'rgba(0,0,0,0.7)';
        removeBtn.style.color = '#fff';
        removeBtn.style.border = 'none';
        removeBtn.style.borderRadius = '50%';
        removeBtn.style.width = '18px';
        removeBtn.style.height = '18px';
        removeBtn.style.fontSize = '14px';
        removeBtn.style.lineHeight = '1';
        removeBtn.style.cursor = 'pointer';
        removeBtn.style.display = 'flex';
        removeBtn.style.alignItems = 'center';
        removeBtn.style.justifyContent = 'center';
        
        removeBtn.onclick = () => {
          accumulatedFiles.splice(index, 1);
          updateImagePreviews();
        };
        
        wrapper.appendChild(img);
        wrapper.appendChild(removeBtn);
        imagePreviewContainer.appendChild(wrapper);
      };
      reader.readAsDataURL(file);
    });
    
    if (fileUpload) {
      fileUpload.files = dt.files;
    }
    if (fileCount) {
      const count = accumulatedFiles.length;
      fileCount.textContent = count > 0 ? `${count} imagem(ns)` : '';
    }
  }

  if (inputQuestion && fileUpload) {
    inputQuestion.addEventListener('paste', (e) => {
      const items = (e.clipboardData || e.originalEvent.clipboardData).items;
      let hasImage = false;

      for (let item of items) {
        if (item.type.indexOf('image') === 0) {
          const file = item.getAsFile();
          if (file) {
            accumulatedFiles.push(file);
            hasImage = true;
          }
        }
      }

      if (hasImage) {
        updateImagePreviews();
      }
    });
  }

  async function enviarPergunta() {
    if (window.stopVoiceRecording) {
      window.stopVoiceRecording();
    }
    
    const question = inputQuestion.value.trim();
    const files = fileUpload ? fileUpload.files : [];
    
    if (!question && files.length === 0) {
      showToast('Por favor, digite uma pergunta ou anexe um arquivo (imagem/áudio).', 'warning');
      inputQuestion.focus();
      return;
    }

    // Estado de carregamento
    btnSubmit.disabled = true;
    btnSubmitText.textContent = `Consultando base como ${currentAttendant}...`;
    btnSpinner.style.display = 'inline-block';
    responseContent.innerHTML = `
      <div class="response-placeholder">
        <div class="spinner" style="width: 32px; height: 32px; border-width: 3px; margin-bottom: 1rem;"></div>
        <p>A IA está lendo o site oficial, os manuais e redigindo a resposta como <strong>${currentAttendant}</strong>...</p>
      </div>
    `;

    const startTime = performance.now();

    try {
      const formData = new FormData();
      formData.append('question', question);
      formData.append('attendant', currentAttendant);
      if (files.length > 0) {
        for (let i = 0; i < files.length; i++) {
          formData.append('files', files[i]);
        }
      }

      let res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        body: formData
      });
      if (!res.ok && res.status === 404) {
        res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          body: formData
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
        // Clear input after success
        inputQuestion.value = '';
        if (charCounter) charCounter.textContent = '0 caracteres';
        accumulatedFiles = [];
        if (typeof updateImagePreviews === 'function') updateImagePreviews();
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
      btnSubmitText.textContent = 'Gerar Resposta';
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

  // ==================== FRASES RÁPIDAS ====================
  const btnCopyQuickPhrases = document.querySelectorAll('.btn-copy-quick-phrase');
  btnCopyQuickPhrases.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const card = e.target.closest('.phrase-card');
      if (card) {
        const text = card.querySelector('.phrase-text').textContent;
        navigator.clipboard.writeText(text).then(() => {
          const originalHTML = btn.innerHTML;
          btn.innerHTML = '✅ Copiado!';
          btn.style.color = 'var(--accent-green)';
          btn.style.borderColor = 'var(--accent-green)';
          showToast('Frase copiada para a área de transferência!', 'success');
          setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.color = '';
            btn.style.borderColor = '';
          }, 2000);
        });
      }
    });
  });

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

  // Atualiza imediatamente e verifica a cada 5 segundos (tempo real)
  atualizarStats();
  setInterval(atualizarStats, 5000);
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
