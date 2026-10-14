// Monitor APS Pacujá - Client Application Logic
document.addEventListener('DOMContentLoaded', () => {
  let evolutionChartInstance = null;
  let currentChartType = 'qualidade';
  let cachedDashboardData = null;

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }


  // DOM Elements
  const periodSelect = document.getElementById('period-select');
  const teamFilter = document.getElementById('team-filter');
  const btnSync = document.getElementById('btn-sync');
  const syncIcon = document.getElementById('sync-icon');
  const statusMessage = document.getElementById('status-message');
  const statusTitle = document.getElementById('status-title');
  const reportCount = document.getElementById('report-count');

  // KPI elements
  const kpiC2Val = document.getElementById('kpi-c2-val');
  const kpiC2Foot = document.getElementById('kpi-c2-foot');
  const kpiC3Val = document.getElementById('kpi-c3-val');
  const kpiC3Foot = document.getElementById('kpi-c3-foot');
  const teamsCount = document.getElementById('teams-count');
  const lastCheck = document.getElementById('last-check');

  // Classification bars
  const countOtimo = document.getElementById('count-otimo');
  const countBom = document.getElementById('count-bom');
  const countSuficiente = document.getElementById('count-suficiente');
  const countRegular = document.getElementById('count-regular');
  const fillOtimo = document.getElementById('fill-otimo');
  const fillBom = document.getElementById('fill-bom');
  const fillSuficiente = document.getElementById('fill-suficiente');
  const fillRegular = document.getElementById('fill-regular');
  const periodTag = document.getElementById('period-tag');

  // Tables & containers
  const tbodyAttention = document.getElementById('tbody-attention');
  const tbodyAllIndicators = document.getElementById('tbody-all-indicators');
  const indicatorSearch = document.getElementById('indicator-search');
  const teamsGrid = document.getElementById('teams-grid-container');
  const actionsList = document.getElementById('actions-list');
  const actionsBadge = document.getElementById('actions-count-badge');

  // Modals
  const actionModal = document.getElementById('action-modal');
  const btnAddAction = document.getElementById('btn-add-action');
  const btnQuickAction = document.getElementById('btn-quick-action');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const btnCancelAction = document.getElementById('btn-cancel-action');
  const formAction = document.getElementById('form-action');

  const auditModal = document.getElementById('audit-modal');
  const btnOpenAudit = document.getElementById('btn-open-audit');
  const auditModalClose = document.getElementById('audit-modal-close');
  const btnCloseAudit = document.getElementById('btn-close-audit');
  const tbodyRawFiles = document.getElementById('tbody-raw-files');

  // Initial Load
  init();

  async function init() {
    await loadStatus();
    await loadDashboard();
    await loadActions();
    setupEventListeners();
  }

  function setupEventListeners() {
    periodSelect.addEventListener('change', () => loadDashboard());
    teamFilter.addEventListener('change', () => loadDashboard());

    btnSync.addEventListener('click', triggerSync);

    // Chart toggles
    document.querySelectorAll('.toggle-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentChartType = e.target.dataset.chart;
        if (cachedDashboardData) {
          renderEvolutionChart(cachedDashboardData.time_series);
        }
      });
    });

    // Indicator search
    indicatorSearch.addEventListener('input', (e) => {
      filterAllIndicatorsTable(e.target.value.toLowerCase());
    });

    // Action Modal
    const openActionModal = (prefCode = '', prefTeam = '') => {
      formAction.reset();
      if (prefCode) {
        document.getElementById('action-indicator').value = prefCode;
      }
      if (prefTeam) {
        document.getElementById('action-team-type').value = prefTeam;
      }
      actionModal.classList.add('active');
    };

    btnAddAction.addEventListener('click', () => openActionModal());
    btnQuickAction.addEventListener('click', () => openActionModal());

    const closeActionModal = () => actionModal.classList.remove('active');
    modalCloseBtn.addEventListener('click', closeActionModal);
    btnCancelAction.addEventListener('click', closeActionModal);

    formAction.addEventListener('submit', handleActionSubmit);

    // Audit Modal
    btnOpenAudit.addEventListener('click', openAuditModal);
    const closeAuditModal = () => auditModal.classList.remove('active');
    auditModalClose.addEventListener('click', closeAuditModal);
    btnCloseAudit.addEventListener('click', closeAuditModal);

    // Close modals on escape key or backdrop click
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeActionModal();
        closeAuditModal();
      }
    });

    [actionModal, auditModal].forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.remove('active');
        }
      });
    });
  }

  async function loadStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();

      statusMessage.textContent = data.message;
      reportCount.textContent = `${data.reports_count} arquivos validados`;

      if (data.available_periods && data.available_periods.length > 0) {
        periodSelect.innerHTML = '';
        data.available_periods.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p;
          opt.textContent = `${p} (Publicado)`;
          periodSelect.appendChild(opt);
        });
      }
    } catch (err) {
      console.error('Erro ao carregar status:', err);
    }
  }

  async function loadDashboard() {
    const period = periodSelect.value;
    const team = teamFilter.value;

    let url = '/api/dashboard';
    const params = new URLSearchParams();
    if (period) params.append('period', period);
    if (team) params.append('team_type', team);
    if (params.toString()) url += `?${params.toString()}`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      cachedDashboardData = data;

      renderDashboard(data);
    } catch (err) {
      console.error('Erro ao carregar dashboard:', err);
    }
  }

  function renderDashboard(data) {
    if (!data.period) return;

    // Period tag
    periodTag.textContent = data.period;

    // KPIs
    kpiC2Val.textContent = data.kpis.component_2.label;
    kpiC2Foot.innerHTML = `<span class="dot green"></span> ${data.kpis.component_2.desc}`;

    kpiC3Val.textContent = data.kpis.component_3.label;
    kpiC3Foot.innerHTML = `<span class="dot green"></span> ${data.kpis.component_3.desc}`;

    teamsCount.textContent = data.kpis.teams_count;
    lastCheck.textContent = data.kpis.last_check;

    // Classification Bars
    let otimo = 0, bom = 0, suficiente = 0, regular = 0;
    data.component_summaries.forEach(s => {
      otimo += s.qtd_otimo || 0;
      bom += s.qtd_bom || 0;
      suficiente += s.qtd_suficiente || 0;
      regular += s.qtd_regular || 0;
    });

    const total = otimo + bom + suficiente + regular || 1;
    countOtimo.textContent = `${otimo} eq (${Math.round((otimo/total)*100)}%)`;
    countBom.textContent = `${bom} eq (${Math.round((bom/total)*100)}%)`;
    countSuficiente.textContent = `${suficiente} eq (${Math.round((suficiente/total)*100)}%)`;
    countRegular.textContent = `${regular} eq (${Math.round((regular/total)*100)}%)`;

    fillOtimo.style.width = `${(otimo / total) * 100}%`;
    fillBom.style.width = `${(bom / total) * 100}%`;
    fillSuficiente.style.width = `${(suficiente / total) * 100}%`;
    fillRegular.style.width = `${(regular / total) * 100}%`;

    // Charts
    renderEvolutionChart(data.time_series);

    // Attention Indicators Table
    renderAttentionTable(data.attention_indicators);

    // All Indicators Table
    renderAllIndicatorsTable(data.indicators);

    // Teams Grid
    renderTeamsGrid(data.teams);
  }

  function renderEvolutionChart(timeSeries) {
    const canvas = document.getElementById('evolutionChart');
    const chartEmpty = document.getElementById('chart-empty');
    if (!canvas || !timeSeries || !timeSeries.periods || timeSeries.periods.length === 0) {
      if (chartEmpty) chartEmpty.style.display = 'flex';
      return;
    }
    if (chartEmpty) chartEmpty.style.display = 'none';

    if (evolutionChartInstance) {
      evolutionChartInstance.destroy();
    }

    const periods = timeSeries.periods;
    const datasets = [];

    if (currentChartType === 'qualidade') {
      // Componente III por tipo de equipe (eSF, eSB, eMulti)
      const colors = {
        eSF: { border: '#2563eb', bg: 'rgba(37, 99, 235, 0.1)' },
        eSB: { border: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
        eMulti: { border: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.1)' },
      };

      for (const [team, dataObj] of Object.entries(timeSeries.teams)) {
        // Percentual favorável (Ótimo + Bom)
        const favorable = dataObj.otimo.map((val, idx) => {
          const tot = val + dataObj.bom[idx] + dataObj.suficiente[idx] + dataObj.regular[idx];
          return tot > 0 ? Math.round(((val + dataObj.bom[idx]) / tot) * 100) : 0;
        });

        datasets.push({
          label: `${team} (% Bom/Ótimo)`,
          data: favorable,
          borderColor: colors[team]?.border || '#64748b',
          backgroundColor: colors[team]?.bg || 'rgba(100, 116, 139, 0.1)',
          borderWidth: 2.5,
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          pointHoverRadius: 6,
        });
      }
    } else {
      // Componente II (CVAT)
      datasets.push({
        label: 'Vínculo e Acompanhamento eSF (% Ótimo)',
        data: periods.map(() => 100),
        borderColor: '#059669',
        backgroundColor: 'rgba(5, 150, 105, 0.15)',
        borderWidth: 3,
        tension: 0.2,
        fill: true,
        pointRadius: 5,
      });
    }

    evolutionChartInstance = new Chart(canvas, {
      type: 'line',
      data: {
        labels: periods,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { font: { family: 'DM Sans', size: 11 }, boxWidth: 12 }
          },
          tooltip: {
            backgroundColor: '#0b2141',
            titleFont: { family: 'Manrope', size: 12, weight: 'bold' },
            bodyFont: { family: 'DM Sans', size: 11 },
            padding: 10,
            cornerRadius: 8,
          }
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: {
              callback: (v) => `${v}%`,
              font: { family: 'DM Sans', size: 10 }
            },
            grid: { color: '#f1f5f9' }
          },
          x: {
            grid: { display: false },
            ticks: { font: { family: 'DM Sans', size: 10 } }
          }
        }
      }
    });
  }

  function renderAttentionTable(attentionList) {
    tbodyAttention.innerHTML = '';

    if (!attentionList || attentionList.length === 0) {
      tbodyAttention.innerHTML = `
        <tr>
          <td colspan="7" class="table-empty-cell">
            <div class="table-empty">
              <div class="empty-symbol">✓</div>
              <strong>Nenhum indicador em estado de alerta no período</strong>
              <p>Todas as equipes avaliadas atingiram faixas favoráveis.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    attentionList.forEach(item => {
      const tr = document.createElement('tr');
      const trendIcon = item.trend === 'subiu' ? '↑' : (item.trend === 'caiu' ? '↓' : '→');
      const trendText = item.trend === 'subiu' ? 'Subiu' : (item.trend === 'caiu' ? 'Caiu' : 'Estável');

      tr.innerHTML = `
        <td>
          <strong>${escapeHtml(item.indicator_code)}</strong> - ${escapeHtml(item.name)}
        </td>
        <td><span class="team-badge ${escapeHtml(item.team_type.toLowerCase())}">${escapeHtml(item.team_type)}</span></td>
        <td><span class="badge badge-info">Peso ${item.peso || '—'}</span></td>
        <td>
          <span class="concept-chip regular">${item.regular} Reg</span>
          <span class="concept-chip enough">${item.suficiente} Suf</span>
          <span class="concept-chip good">${item.bom} Bom</span>
          <span class="concept-chip excellent">${item.otimo} Óti</span>
        </td>
        <td>
          <span class="concept-chip ${escapeHtml(item.predominant.toLowerCase())}">${escapeHtml(item.predominant)}</span>
        </td>
        <td>
          <span class="trend-badge ${escapeHtml(item.trend)}">${trendIcon} ${trendText}</span>
        </td>
        <td>
          <button class="btn btn-primary btn-sm btn-action-trigger" data-code="${escapeHtml(item.indicator_code)}" data-team="${escapeHtml(item.team_type)}">
            + Ação
          </button>
        </td>
      `;
      tbodyAttention.appendChild(tr);
    });

    document.querySelectorAll('.btn-action-trigger').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const code = e.currentTarget.dataset.code;
        const team = e.currentTarget.dataset.team;
        document.getElementById('action-indicator').value = code;
        document.getElementById('action-team-type').value = team;
        actionModal.classList.add('active');
      });
    });
  }

  function renderAllIndicatorsTable(indicators) {
    tbodyAllIndicators.innerHTML = '';
    if (!indicators || indicators.length === 0) return;

    indicators.forEach(item => {
      const tr = document.createElement('tr');
      tr.className = 'indicator-row';
      tr.dataset.text = `${item.indicator_code} ${item.name} ${item.team_type}`.toLowerCase();

      tr.innerHTML = `
        <td><strong>${item.indicator_code}</strong></td>
        <td>${item.name}</td>
        <td><span class="team-badge ${item.team_type.toLowerCase()}">${item.team_type}</span></td>
        <td><strong>${item.peso || '—'}</strong></td>
        <td>${item.regular}</td>
        <td>${item.suficiente}</td>
        <td>${item.bom}</td>
        <td>${item.otimo}</td>
        <td><span class="concept-chip ${item.predominant.toLowerCase()}">${item.predominant}</span></td>
      `;
      tbodyAllIndicators.appendChild(tr);
    });
  }

  function filterAllIndicatorsTable(query) {
    const rows = document.querySelectorAll('.indicator-row');
    rows.forEach(r => {
      const text = r.dataset.text || '';
      r.style.display = text.includes(query) ? '' : 'none';
    });
  }

  function renderTeamsGrid(teams) {
    teamsGrid.innerHTML = '';
    if (!teams || teams.length === 0) return;

    teams.forEach(t => {
      const card = document.createElement('div');
      card.className = 'team-card';
      const badgeClass = t.sg_equipe.toLowerCase();

      card.innerHTML = `
        <span class="team-badge ${badgeClass}">${t.sg_equipe}</span>
        <div class="team-name">${t.no_equipe}</div>
        <div class="team-code">Código INE/CNES: ${t.co_equipe}</div>
      `;
      teamsGrid.appendChild(card);
    });
  }

  async function loadActions() {
    try {
      const res = await fetch('/api/actions');
      const data = await res.json();
      renderActions(data.actions || []);
    } catch (err) {
      console.error('Erro ao carregar ações:', err);
    }
  }

  function renderActions(actions) {
    actionsList.innerHTML = '';
    actionsBadge.textContent = actions.length;

    if (actions.length === 0) {
      actionsList.innerHTML = `
        <div class="action-empty" id="actions-empty-state">
          Nenhuma ação cadastrada ainda. Clique em "+ Nova Ação" para registrar plano, responsável e prazo.
        </div>
      `;
      return;
    }

    actions.forEach(a => {
      const card = document.createElement('div');
      card.className = 'action-card';

      const statusLabels = {
        pendente: 'Pendente',
        em_andamento: 'Em Andamento',
        concluido: 'Concluído'
      };

      card.innerHTML = `
        <div class="action-card-header">
          <span class="team-badge ${escapeHtml(a.team_type ? a.team_type.toLowerCase() : 'esf')}">${escapeHtml(a.team_type || 'Geral')}</span>
          <span class="action-status-pill ${escapeHtml(a.status)}" data-id="${a.id}" data-current="${escapeHtml(a.status)}">
            ${escapeHtml(statusLabels[a.status] || a.status)}
          </span>
        </div>
        <div class="action-card-title">${escapeHtml(a.title)}</div>
        <p style="font-size: 11px; color: #64748b; margin: 4px 0;">${escapeHtml(a.description || '')}</p>
        <div class="action-card-meta">
          <span>👤 ${escapeHtml(a.responsible)}</span>
          <span>📅 Prazo: ${escapeHtml(a.deadline)}</span>
          ${a.indicator_code ? `<span>🎯 Indicador: ${escapeHtml(a.indicator_code)}</span>` : ''}
          <button class="btn btn-secondary btn-sm btn-delete-action" data-id="${a.id}" style="margin-left: auto; padding: 2px 6px; font-size: 10px;">Excluir</button>
        </div>
      `;
      actionsList.appendChild(card);
    });

    // Eventos de clique para avançar status
    document.querySelectorAll('.action-status-pill').forEach(pill => {
      pill.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        const curr = e.currentTarget.dataset.current;
        const nextStatus = curr === 'pendente' ? 'em_andamento' : (curr === 'em_andamento' ? 'concluido' : 'pendente');

        await fetch(`/api/actions/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: nextStatus })
        });
        showToast('Situação da ação atualizada!', 'success');
        loadActions();
      });
    });

    // Evento para excluir ação
    document.querySelectorAll('.btn-delete-action').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        if (!confirm('Deseja realmente remover esta ação?')) return;
        const id = e.currentTarget.dataset.id;
        await fetch(`/api/actions/${id}`, { method: 'DELETE' });
        showToast('Ação removida.', 'info');
        loadActions();
      });
    });
  }

  async function handleActionSubmit(e) {
    e.preventDefault();
    const payload = {
      title: document.getElementById('action-title').value,
      team_type: document.getElementById('action-team-type').value,
      indicator_code: document.getElementById('action-indicator').value,
      responsible: document.getElementById('action-responsible').value,
      deadline: document.getElementById('action-deadline').value,
      description: document.getElementById('action-description').value,
      status: 'pendente'
    };

    try {
      const res = await fetch('/api/actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        actionModal.classList.remove('active');
        showToast('Ação de melhoria registrada com sucesso!', 'success');
        loadActions();
      } else {
        showToast('Erro ao criar ação.', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Falha na comunicação com o servidor.', 'error');
    }
  }

  async function openAuditModal() {
    tbodyRawFiles.innerHTML = '<tr><td colspan="6">Carregando auditoria...</td></tr>';
    auditModal.classList.add('active');

    try {
      const res = await fetch('/api/raw-files');
      const data = await res.json();
      tbodyRawFiles.innerHTML = '';

      if (!data.files || data.files.length === 0) {
        tbodyRawFiles.innerHTML = '<tr><td colspan="6">Nenhum arquivo auditado.</td></tr>';
        return;
      }

      data.files.forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${f.filename}</strong></td>
          <td>${f.component}</td>
          <td>${Math.round(f.file_size / 1024)} KB</td>
          <td class="hash-cell">${f.sha256_hash}</td>
          <td>${f.fetched_at ? f.fetched_at.slice(0, 16).replace('T', ' ') : '—'}</td>
          <td>
            <a href="/api/raw-files/${f.filename}/download" class="btn btn-secondary btn-sm">
              Baixar CSV
            </a>
          </td>
        `;
        tbodyRawFiles.appendChild(tr);
      });
    } catch (err) {
      console.error(err);
      tbodyRawFiles.innerHTML = '<tr><td colspan="6">Erro ao carregar arquivos auditados.</td></tr>';
    }
  }

  async function triggerSync() {
    syncIcon.classList.add('spinning');
    btnSync.disabled = true;
    showToast('Consultando catálogo público oficial do Siaps...', 'info');

    try {
      const res = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger: 'web_dashboard' })
      });
      const data = await res.json();

      if (res.ok) {
        showToast(`Sincronização concluída! ${data.files_downloaded} novos, ${data.files_unchanged} inalterados.`, 'success');
        await loadStatus();
        await loadDashboard();
      } else {
        showToast(`Falha na sincronização: ${data.message}`, 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Erro ao sincronizar dados com o Siaps.', 'error');
    } finally {
      syncIcon.classList.remove('spinning');
      btnSync.disabled = false;
    }
  }

  function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';

    const icon = type === 'success' ? '✓' : (type === 'error' ? '✕' : 'ℹ');
    toast.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
});
