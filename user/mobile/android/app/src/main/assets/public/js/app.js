/* ============================================================
   Zenic Agents v3.0.0 — Main Application Logic (app.js)
   Router, Navigation, UI Interactions, Data Binding
   ============================================================ */

const ZenicApp = (function() {
  'use strict';

  let currentPage = 'dashboard';
  let clockInterval = null;

  // ============================================================
  // INITIALIZATION
  // ============================================================
  async function init() {
    // Show splash
    await _animateSplash();

    // Initialize database
    try {
      await ZenicDB.init();
    } catch(e) {
      console.error('[App] DB init error:', e);
    }

    // Check auth
    if (ZenicAuth.isAuthenticated()) {
      await _showApp();
    } else {
      _showAuth();
    }

    // Handle hash navigation
    window.addEventListener('hashchange', _handleHashChange);

    // Set initial hash
    if (window.location.hash) {
      _handleHashChange();
    }
  }

  async function _animateSplash() {
    return new Promise(resolve => {
      setTimeout(() => {
        const splash = document.getElementById('splash-screen');
        if (splash) {
          splash.classList.add('fade-out');
          setTimeout(() => splash.classList.add('hidden'), 500);
        }
        resolve();
      }, 2200);
    });
  }

  // ============================================================
  // AUTH UI
  // ============================================================
  function _showAuth() {
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app-screen').classList.add('hidden');
  }

  function _hideAuth() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app-screen').classList.remove('hidden');
  }

  function showLogin() {
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('register-form').classList.add('hidden');
  }

  function showRegister() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
  }

  async function login() {
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    if (!email || !password) {
      toast('Ingresa correo y contraseña', 'warning');
      return;
    }

    _setButtonLoading('.btn-primary', true);
    const result = await ZenicAuth.login(email, password);
    _setButtonLoading('.btn-primary', false);

    if (result.success) {
      toast('¡Bienvenido de vuelta!', 'success');
      await _showApp();
    } else {
      toast(result.error, 'error');
    }
  }

  async function register() {
    const name = document.getElementById('reg-name').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const org = document.getElementById('reg-org').value.trim();

    _setButtonLoading('#register-form .btn-primary', true);
    const result = await ZenicAuth.register(name, email, password, org);
    _setButtonLoading('#register-form .btn-primary', false);

    if (result.success) {
      toast('¡Cuenta creada exitosamente!', 'success');
      await _showApp();
    } else {
      toast(result.error, 'error');
    }
  }

  async function logout() {
    await ZenicAuth.logout();
    _showAuth();
    toast('Sesión cerrada', 'info');
    // Stop clock
    if (clockInterval) clearInterval(clockInterval);
  }

  function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    input.type = input.type === 'password' ? 'text' : 'password';
  }

  // ============================================================
  // MAIN APP INITIALIZATION
  // ============================================================
  async function _showApp() {
    _hideAuth();

    const session = ZenicAuth.getSession();
    if (session) {
      // Update header
      const letter = session.name ? session.name.charAt(0).toUpperCase() : 'Z';
      document.getElementById('header-avatar-letter').textContent = letter;
      document.getElementById('drawer-avatar').textContent = letter;
      document.getElementById('drawer-user-name').textContent = session.name || 'Usuario';
      document.getElementById('drawer-user-role').textContent = session.role || 'Operador';
    }

    // Start clock
    _updateClock();
    clockInterval = setInterval(_updateClock, 30000);

    // Load initial page
    await navigate('dashboard');
  }

  function _updateClock() {
    const now = new Date();
    const h = now.getHours().toString().padStart(2, '0');
    const m = now.getMinutes().toString().padStart(2, '0');
    const el = document.getElementById('greeting-time');
    if (el) el.textContent = `${h}:${m}`;

    // Update greeting
    const hour = now.getHours();
    let greeting = 'Buenas noches';
    if (hour >= 5 && hour < 12) greeting = 'Buenos días';
    else if (hour >= 12 && hour < 19) greeting = 'Buenas tardes';

    const gEl = document.getElementById('greeting-text');
    if (gEl) gEl.textContent = greeting;
  }

  // ============================================================
  // NAVIGATION / ROUTER
  // ============================================================
  const PAGE_TITLES = {
    dashboard: 'Centro de Comando',
    arbitraje: 'Arbitraje (HITL)',
    boveda: 'Bóveda',
    nichos: 'Nichos & Plantillas',
    apis: 'APIs & MCP',
    politicas: 'Políticas',
    suscripcion: 'Suscripción',
    integraciones: 'Integraciones',
    configuracion: 'Configuración',
    perfil: 'Perfil'
  };

  async function navigate(page) {
    currentPage = page;

    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

    // Show target page
    const target = document.getElementById(`page-${page}`);
    if (target) target.classList.add('active');

    // Update title
    document.getElementById('page-title').textContent = PAGE_TITLES[page] || page;

    // Update bottom nav
    document.querySelectorAll('.nav-item').forEach(n => {
      n.classList.toggle('active', n.dataset.page === page);
    });

    // Update drawer items
    document.querySelectorAll('.drawer-item[data-page]').forEach(d => {
      d.classList.toggle('active', d.dataset.page === page);
    });

    // Update hash
    window.location.hash = page;

    // Load page data
    await _loadPageData(page);
  }

  function _handleHashChange() {
    const hash = window.location.hash.replace('#', '');
    if (hash && hash !== currentPage) {
      navigate(hash);
    }
  }

  async function _loadPageData(page) {
    switch(page) {
      case 'dashboard': await _loadDashboard(); break;
      case 'arbitraje': await _loadArbitraje(); break;
      case 'boveda': await _loadBoveda(); break;
      case 'nichos': await _loadNichos(); break;
      case 'apis': await _loadAPIs(); break;
      case 'politicas': await _loadPoliticas(); break;
      case 'suscripcion': await _loadSuscripcion(); break;
      case 'integraciones': await _loadIntegraciones(); break;
      case 'configuracion': await _loadConfiguracion(); break;
      case 'perfil': await _loadPerfil(); break;
    }
  }

  // ============================================================
  // DASHBOARD
  // ============================================================
  async function _loadDashboard() {
    try {
      const data = await ZenicAPI.getDashboardData();

      // KPIs
      document.getElementById('kpi-agents').textContent = data.kpis.activeAgents;
      document.getElementById('kpi-tasks').textContent = data.kpis.completedTasks;
      document.getElementById('kpi-hitl').textContent = data.kpis.hitlPending;
      document.getElementById('kpi-policies').textContent = data.kpis.activePolicies;

      // System status
      document.getElementById('mem-pct').textContent = data.system.memory + '%';
      document.getElementById('mem-bar').style.width = data.system.memory + '%';
      document.getElementById('cpu-pct').textContent = data.system.cpu + '%';
      document.getElementById('cpu-bar').style.width = data.system.cpu + '%';
      document.getElementById('disk-pct').textContent = data.system.disk + '%';
      document.getElementById('disk-bar').style.width = data.system.disk + '%';

      // Activity chart
      _renderChart(data.weeklyActivity);

      // Agent cards
      _renderAgentCards(data.agents);

      // Update notification count
      const notifs = await ZenicDB.getNotifications(ZenicAuth.getSession()?.userId);
      const unread = notifs ? notifs.filter(n => !n.is_read).length : 0;
      document.getElementById('notif-count').textContent = unread;
      document.getElementById('notif-count').style.display = unread > 0 ? 'flex' : 'none';

    } catch(e) {
      console.error('[App] Dashboard load error:', e);
    }
  }

  function _renderChart(data) {
    const container = document.getElementById('activity-chart');
    const days = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
    const maxVal = Math.max(...data, 1);

    container.innerHTML = data.map((v, i) => `
      <div class="chart-bar-group">
        <div class="chart-bar" style="height:${Math.max((v / maxVal) * 100, 4)}%"></div>
        <span>${days[i]}</span>
      </div>
    `).join('');
  }

  function _renderAgentCards(agents) {
    const container = document.getElementById('dashboard-agents');
    if (!agents || agents.length === 0) {
      container.innerHTML = '<div class="empty-state"><p>No hay agentes</p></div>';
      return;
    }

    container.innerHTML = agents.map(a => `
      <div class="agent-card" onclick="ZenicApp.showAgentDetail('${a.id}')">
        <div class="agent-emoji">${a.emoji || '🤖'}</div>
        <div class="agent-info">
          <div class="agent-name">${a.name}</div>
          <div class="agent-status">${a.status === 'active' ? '🟢 Activo' : '🟡 Inactivo'} • ${a.total_tasks || 0} tareas</div>
        </div>
        <span class="agent-badge ${a.status === 'active' ? 'badge-green' : 'badge-amber'}">${a.success_rate || 0}%</span>
      </div>
    `).join('');
  }

  function updateChart() {
    _loadDashboard();
  }

  // ============================================================
  // ARBITRAJE (HITL)
  // ============================================================
  async function _loadArbitraje() {
    try {
      const requests = await ZenicAPI.getHITLRequests();
      const allRequests = await ZenicAPI.getAllHITLRequests();
      const stats = await ZenicDB.getHITLStats();

      // Pending count
      const pendingCount = requests ? requests.length : 0;
      document.getElementById('hitl-count').textContent = `${pendingCount} pendientes`;

      // HITL list
      const listEl = document.getElementById('hitl-list');
      if (!requests || requests.length === 0) {
        listEl.innerHTML = '<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg><p>No hay solicitudes pendientes</p></div>';
      } else {
        listEl.innerHTML = requests.map(r => `
          <div class="hitl-item">
            <div class="hitl-item-header">
              <span class="hitl-item-title">${r.action}</span>
              <span class="badge badge-${r.risk_level === 'critical' ? 'red' : r.risk_level === 'high' ? 'amber' : r.risk_level === 'medium' ? 'blue' : 'green'}">${r.risk_level.toUpperCase()}</span>
            </div>
            <div class="hitl-item-desc">${r.description || 'Sin descripción'}</div>
            <div class="hitl-item-meta">
              <span class="badge badge-purple">${r.agent_id || 'Sistema'}</span>
              <span class="badge badge-cyan">${_timeAgo(r.requested_at)}</span>
            </div>
            <div class="hitl-actions">
              <button class="btn btn-primary btn-sm" onclick="ZenicApp.approveHITL('${r.id}')">✓ Aprobar</button>
              <button class="btn btn-danger btn-sm" onclick="ZenicApp.rejectHITL('${r.id}')">✗ Rechazar</button>
            </div>
          </div>
        `).join('');
      }

      // Stats
      document.getElementById('hitl-approved').textContent = stats.approved;
      document.getElementById('hitl-rejected').textContent = stats.rejected;
      document.getElementById('hitl-avg-time').textContent = stats.avgTime;
      document.getElementById('hitl-total').textContent = stats.total;

      // Agent select
      const agents = await ZenicAPI.getAgents();
      const agentSelect = document.getElementById('hitl-agent');
      if (agentSelect) {
        agentSelect.innerHTML = agents.map(a => `<option value="${a.id}">${a.emoji} ${a.name}</option>`).join('');
      }

    } catch(e) {
      console.error('[App] Arbitraje load error:', e);
    }
  }

  async function createHITLRequest() {
    const agentId = document.getElementById('hitl-agent').value;
    const action = document.getElementById('hitl-action').value.trim();
    const risk = document.getElementById('hitl-risk').value;

    if (!action) {
      toast('Describe la acción propuesta', 'warning');
      return;
    }

    await ZenicAPI.createHITLRequest(agentId, action, action, risk);
    toast('Solicitud HITL creada', 'success');
    document.getElementById('hitl-action').value = '';
    await _loadArbitraje();
  }

  async function approveHITL(id) {
    await ZenicAPI.approveHITL(id, 'Aprobado desde app móvil');
    toast('Solicitud aprobada ✓', 'success');
    await _loadArbitraje();
  }

  async function rejectHITL(id) {
    await ZenicAPI.rejectHITL(id, 'Rechazado desde app móvil');
    toast('Solicitud rechazada', 'info');
    await _loadArbitraje();
  }

  // ============================================================
  // BÓVEDA
  // ============================================================
  async function _loadBoveda() {
    try {
      const data = await ZenicAPI.getVaultData();

      // Merkle root
      document.getElementById('merkle-root').textContent = data.merkleRoot;
      document.getElementById('vault-entries').textContent = data.entryCount;
      document.getElementById('vault-audits').textContent = data.auditCount;

      // Audit list
      const auditList = document.getElementById('audit-list');
      const audits = await ZenicDB.getAuditLog(20);
      if (!audits || audits.length === 0) {
        auditList.innerHTML = '<div class="empty-state"><p>No hay registros de auditoría</p></div>';
      } else {
        auditList.innerHTML = audits.map(a => `
          <div class="audit-item">
            <span class="audit-time">${_timeAgo(a.created_at)}</span>
            <div class="audit-action">
              <span class="audit-user">${a.action}</span>
              <span style="color:var(--text-muted);font-size:11px">${a.resource_type}${a.resource_id ? ':' + a.resource_id : ''}</span>
            </div>
          </div>
        `).join('');
      }

      // Secret list
      const secretList = document.getElementById('secret-list');
      if (!data.entries || data.entries.length === 0) {
        secretList.innerHTML = '<div class="empty-state"><p>No hay secretos almacenados</p></div>';
      } else {
        secretList.innerHTML = data.entries.map(e => `
          <div class="secret-item">
            <span class="secret-key">🔑 ${e.key_name}</span>
            <span class="secret-val">••••••</span>
          </div>
        `).join('');
      }

    } catch(e) {
      console.error('[App] Bóveda load error:', e);
    }
  }

  async function addSecret() {
    const key = document.getElementById('secret-key').value.trim();
    const value = document.getElementById('secret-value').value.trim();

    if (!key || !value) {
      toast('Ingresa clave y valor', 'warning');
      return;
    }

    const session = ZenicAuth.getSession();
    await ZenicAPI.addSecret(key, value, session?.userId);

    document.getElementById('secret-key').value = '';
    document.getElementById('secret-value').value = '';

    toast('Secreto guardado en la bóveda 🔒', 'success');
    await _loadBoveda();
  }

  async function verifyIntegrity() {
    const result = await ZenicAPI.verifyIntegrity();
    const el = document.getElementById('integrity-result');
    el.classList.remove('hidden');

    if (result.pass) {
      el.className = 'integrity-result pass';
      el.innerHTML = `✅ Verificación exitosa: ${result.verified}/${result.total} entradas íntegras`;
    } else {
      el.className = 'integrity-result fail';
      el.innerHTML = `❌ Verificación fallida: ${result.failed}/${result.total} entradas con errores`;
    }
  }

  async function exportAuditLog() {
    const data = await ZenicAPI.exportAllData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    // Create download link
    const a = document.createElement('a');
    a.href = url;
    a.download = `zenic-audit-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast('Datos exportados', 'success');
  }

  // ============================================================
  // NICHOS
  // ============================================================
  async function _loadNichos() {
    try {
      const nichos = await ZenicAPI.getNichos();
      const container = document.getElementById('nicho-list');

      if (!nichos || nichos.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No hay plantillas disponibles</p></div>';
        return;
      }

      container.innerHTML = nichos.map(n => `
        <div class="nicho-category">
          <div class="nicho-cat-header" onclick="ZenicApp.toggleNichoExpand('${n.id}')">
            <span class="nicho-cat-title">${n.emoji} ${n.name}</span>
            <span class="nicho-cat-count">${n.agent_count || 0} agentes ${n.is_featured ? '⭐' : ''}</span>
          </div>
          <div class="nicho-items" id="nicho-items-${n.id}" style="display:none">
            <div class="section-desc">${n.description || ''}</div>
            <button class="btn btn-primary btn-sm" onclick="ZenicApp.deployNicho('${n.id}')" style="margin-bottom:8px">🚀 Desplegar Plantilla</button>
            <div id="nicho-agent-list-${n.id}"></div>
          </div>
        </div>
      `).join('');

    } catch(e) {
      console.error('[App] Nichos load error:', e);
    }
  }

  async function toggleNichoExpand(nichoId) {
    const el = document.getElementById(`nicho-items-${nichoId}`);
    if (!el) return;

    const isVisible = el.style.display !== 'none';
    el.style.display = isVisible ? 'none' : 'block';

    if (!isVisible) {
      // Load agents for this nicho
      const agents = await ZenicAPI.getNichoAgents(nichoId);
      const listEl = document.getElementById(`nicho-agent-list-${nichoId}`);
      if (listEl && agents && agents.length > 0) {
        listEl.innerHTML = agents.map(a => `
          <div class="nicho-item">
            <div>
              <div class="nicho-item-name">${a.emoji} ${a.name}</div>
              <div class="nicho-item-desc">${a.description || ''}</div>
            </div>
            <span class="nicho-item-arrow">›</span>
          </div>
        `).join('');
      }
    }
  }

  async function deployNicho(nichoId) {
    const result = await ZenicAPI.deployNicho(nichoId);
    if (result.success) {
      toast(`¡Plantilla desplegada! ${result.deployedCount} agentes creados 🚀`, 'success');
    } else {
      toast(result.error || 'Error al desplegar', 'error');
    }
  }

  function filterNichos() {
    const search = document.getElementById('nicho-search').value.toLowerCase();
    document.querySelectorAll('.nicho-category').forEach(el => {
      const text = el.textContent.toLowerCase();
      el.style.display = text.includes(search) ? 'block' : 'none';
    });
  }

  // ============================================================
  // APIs & MCP
  // ============================================================
  async function _loadAPIs() {
    try {
      const tools = await ZenicAPI.getMCPTools();
      const servers = await ZenicAPI.getMCPServers();

      // Tools
      const toolList = document.getElementById('tool-list');
      if (toolList) {
        toolList.innerHTML = (tools && tools.length > 0) ? tools.map(t => `
          <div class="tool-item">
            <div class="tool-item-header">
              <span class="tool-name">${t.name}</span>
              <span class="badge ${t.is_active ? 'badge-green' : 'badge-red'}">${t.is_active ? 'Activo' : 'Inactivo'}</span>
            </div>
            <div class="tool-desc">${t.description || ''}</div>
            <div class="tool-meta">
              <span class="badge badge-cyan">${t.call_count || 0} llamadas</span>
              <span class="badge badge-purple">~${t.avg_latency_ms || 0}ms</span>
              ${t.server_id ? `<span class="badge badge-blue">${t.server_id}</span>` : ''}
            </div>
            <div class="btn-row" style="margin-top:8px">
              <button class="btn btn-secondary btn-sm" onclick="ZenicApp.toggleToolStatus('${t.id}')">${t.is_active ? 'Desactivar' : 'Activar'}</button>
              <button class="btn btn-danger btn-sm" onclick="ZenicApp.deleteTool('${t.id}')">Eliminar</button>
            </div>
          </div>
        `).join('') : '<div class="empty-state"><p>No hay herramientas registradas</p></div>';
      }

      // Servers
      const serverList = document.getElementById('server-list');
      if (serverList) {
        serverList.innerHTML = (servers && servers.length > 0) ? servers.map(s => `
          <div class="server-item">
            <div class="server-item-header">
              <span class="server-name">${s.name}</span>
              <span class="badge ${s.status === 'connected' ? 'badge-green' : 'badge-red'}">${s.status === 'connected' ? 'Conectado' : 'Desconectado'}</span>
            </div>
            <div class="server-url">${s.url || 'local'}</div>
            <span class="badge badge-cyan">${s.transport_type}</span>
          </div>
        `).join('') : '<div class="empty-state"><p>No hay servidores registrados</p></div>';
      }

      // Server select for tool form
      const serverSelect = document.getElementById('tool-server');
      if (serverSelect && servers) {
        serverSelect.innerHTML = servers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
      }

    } catch(e) {
      console.error('[App] APIs load error:', e);
    }
  }

  function showAddTool() {
    document.getElementById('add-tool-form').style.display = 'block';
  }

  function hideAddTool() {
    document.getElementById('add-tool-form').style.display = 'none';
  }

  async function createTool() {
    const name = document.getElementById('tool-name').value.trim();
    const desc = document.getElementById('tool-desc').value.trim();
    const params = document.getElementById('tool-params').value.trim() || '{}';
    const serverId = document.getElementById('tool-server').value;

    if (!name) {
      toast('Ingresa el nombre de la herramienta', 'warning');
      return;
    }

    await ZenicAPI.createMCPTool({
      name,
      description: desc,
      parameters: params,
      server_id: serverId
    });

    toast('Herramienta creada exitosamente 🔧', 'success');
    hideAddTool();
    document.getElementById('tool-name').value = '';
    document.getElementById('tool-desc').value = '';
    document.getElementById('tool-params').value = '';
    await _loadAPIs();
  }

  async function createServer() {
    const name = document.getElementById('server-name').value.trim();
    const url = document.getElementById('server-url').value.trim();
    const transport = document.getElementById('server-transport').value;

    if (!name) {
      toast('Ingresa el nombre del servidor', 'warning');
      return;
    }

    await ZenicAPI.createMCPServer({
      name,
      url,
      transport_type: transport
    });

    toast('Servidor MCP registrado 🖥️', 'success');
    document.getElementById('server-name').value = '';
    document.getElementById('server-url').value = '';
    await _loadAPIs();
  }

  async function toggleToolStatus(toolId) {
    await ZenicAPI.toggleToolStatus(toolId);
    toast('Estado actualizado', 'success');
    await _loadAPIs();
  }

  async function deleteTool(toolId) {
    await ZenicAPI.deleteMCPTool(toolId);
    toast('Herramienta eliminada', 'info');
    await _loadAPIs();
  }

  function switchTab(btn, section) {
    const tabName = btn.dataset.tab;
    const parent = btn.closest('.section-card');

    // Update tab buttons
    parent.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');

    // Update tab content
    parent.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    const content = document.getElementById(`${section}-${tabName}`);
    if (content) content.classList.add('active');
  }

  // ============================================================
  // POLÍTICAS
  // ============================================================
  async function _loadPoliticas() {
    try {
      const policies = await ZenicAPI.getPolicies();
      const listEl = document.getElementById('policy-list');

      if (!policies || policies.length === 0) {
        listEl.innerHTML = '<div class="empty-state"><p>No hay políticas definidas</p></div>';
        return;
      }

      listEl.innerHTML = policies.map(p => `
        <div class="policy-item">
          <div class="policy-item-header">
            <span class="policy-item-name">📜 ${p.name}</span>
            <div class="policy-item-meta">
              <span class="badge badge-${p.severity === 'critical' ? 'red' : p.severity === 'high' ? 'amber' : p.severity === 'medium' ? 'blue' : 'green'}">${p.severity}</span>
              <span class="badge badge-cyan">${p.type}</span>
            </div>
          </div>
          <div class="policy-item-desc">${p.description || ''}</div>
          <div class="policy-item-meta">
            <span class="badge ${p.is_active ? 'badge-green' : 'badge-red'}">${p.is_active ? 'Activa' : 'Inactiva'}</span>
            <span class="badge badge-purple">v${p.version || 1}</span>
          </div>
          <div class="btn-row" style="margin-top:8px">
            <button class="btn btn-secondary btn-sm" onclick="ZenicApp.togglePolicy('${p.id}')">${p.is_active ? 'Desactivar' : 'Activar'}</button>
            <button class="btn btn-danger btn-sm" onclick="ZenicApp.deletePolicy('${p.id}')">Eliminar</button>
          </div>
        </div>
      `).join('');

    } catch(e) {
      console.error('[App] Políticas load error:', e);
    }
  }

  function showAddPolicy() {
    document.getElementById('add-policy-form').style.display = 'block';
  }

  function hideAddPolicy() {
    document.getElementById('add-policy-form').style.display = 'none';
  }

  async function createPolicy() {
    const name = document.getElementById('policy-name').value.trim();
    const desc = document.getElementById('policy-desc').value.trim();
    const type = document.getElementById('policy-type').value;
    const severity = document.getElementById('policy-severity').value;
    const rules = document.getElementById('policy-rules').value.trim() || '{}';

    if (!name) {
      toast('Ingresa el nombre de la política', 'warning');
      return;
    }

    await ZenicAPI.createPolicy({ name, description: desc, type, severity, rules });

    toast('Política creada exitosamente 📜', 'success');
    hideAddPolicy();
    document.getElementById('policy-name').value = '';
    document.getElementById('policy-desc').value = '';
    document.getElementById('policy-rules').value = '';
    await _loadPoliticas();
  }

  async function togglePolicy(policyId) {
    await ZenicAPI.togglePolicy(policyId);
    toast('Estado de política actualizado', 'success');
    await _loadPoliticas();
  }

  async function deletePolicy(policyId) {
    await ZenicAPI.deletePolicy(policyId);
    toast('Política eliminada', 'info');
    await _loadPoliticas();
  }

  // ============================================================
  // SUSCRIPCIÓN
  // ============================================================
  async function _loadSuscripcion() {
    try {
      const sub = await ZenicAPI.getSubscriptionInfo();
      if (!sub) return;

      // Current plan
      const tierNames = { starter: 'Starter', business: 'Business', enterprise: 'Enterprise' };
      document.getElementById('plan-badge').textContent = tierNames[sub.tier] || sub.tier;
      document.getElementById('plan-name').textContent = `Plan ${tierNames[sub.tier] || sub.tier}`;

      // Usage
      const limits = sub.features || {};
      const usage = sub.usage || {};

      const agentsUsed = usage.agents_used || 0;
      const agentsLimit = limits.agents || 5;
      document.getElementById('usage-agents').textContent = `${agentsUsed}/${agentsLimit === -1 ? '∞' : agentsLimit}`;
      document.getElementById('usage-agents-bar').style.width = agentsLimit === -1 ? '10%' : `${(agentsUsed / agentsLimit) * 100}%`;

      const toolsUsed = usage.tools_used || 0;
      const toolsLimit = limits.tools || 10;
      document.getElementById('usage-tools').textContent = `${toolsUsed}/${toolsLimit === -1 ? '∞' : toolsLimit}`;
      document.getElementById('usage-tools-bar').style.width = toolsLimit === -1 ? '10%' : `${(toolsUsed / toolsLimit) * 100}%`;

      const policiesUsed = usage.policies_used || 0;
      const policiesLimit = limits.policies || 20;
      document.getElementById('usage-policies').textContent = `${policiesUsed}/${policiesLimit === -1 ? '∞' : policiesLimit}`;
      document.getElementById('usage-policies-bar').style.width = policiesLimit === -1 ? '10%' : `${(policiesUsed / policiesLimit) * 100}%`;

      const hitlUsed = usage.hitl_used || 0;
      const hitlLimit = limits.hitl_monthly || 50;
      document.getElementById('usage-hitl').textContent = `${hitlUsed}/${hitlLimit === -1 ? '∞' : hitlLimit}`;
      document.getElementById('usage-hitl-bar').style.width = hitlLimit === -1 ? '10%' : `${(hitlUsed / hitlLimit) * 100}%`;

      const storageUsed = usage.storage_used_mb || 0;
      const storageLimit = limits.storage_mb || 100;
      document.getElementById('usage-storage').textContent = `${storageUsed} MB / ${storageLimit === -1 ? '∞' : storageLimit + ' MB'}`;
      document.getElementById('usage-storage-bar').style.width = storageLimit === -1 ? '5%' : `${(storageUsed / storageLimit) * 100}%`;

      // Highlight active plan card
      document.querySelectorAll('.plan-card').forEach(pc => {
        pc.classList.toggle('active', pc.dataset.tier === sub.tier);
      });

    } catch(e) {
      console.error('[App] Suscripción load error:', e);
    }
  }

  async function upgradePlan(tier) {
    const result = await ZenicAPI.upgradePlan(tier);
    if (result.success) {
      toast(`¡Plan actualizado a ${tier}! 💎`, 'success');
      await _loadSuscripcion();
    } else {
      toast(result.error || 'Error al actualizar', 'error');
    }
  }

  // ============================================================
  // INTEGRACIONES
  // ============================================================
  async function _loadIntegraciones() {
    try {
      const integrations = await ZenicAPI.getIntegrations();

      if (integrations) {
        integrations.forEach(int => {
          const statusEl = document.getElementById(`int-${int.name}-status`);
          if (statusEl) {
            statusEl.textContent = int.status === 'connected' ? 'Conectado' : 'Desconectado';
            statusEl.closest('.integration-card').classList.toggle('connected', int.status === 'connected');
          }
        });
      }

      // Webhooks
      const webhooks = await ZenicDB.getWebhooks();
      const whList = document.getElementById('webhook-list');
      if (whList) {
        if (!webhooks || webhooks.length === 0) {
          whList.innerHTML = '';
        } else {
          whList.innerHTML = webhooks.map(w => `
            <div class="webhook-item">
              <span>${w.url}</span>
              <button class="webhook-delete" onclick="ZenicApp.deleteWebhook('${w.id}')">✕</button>
            </div>
          `).join('');
        }
      }

    } catch(e) {
      console.error('[App] Integraciones load error:', e);
    }
  }

  async function toggleIntegration(name) {
    const result = await ZenicAPI.toggleIntegration(name);
    if (result.success) {
      toast(`${name}: ${result.status === 'connected' ? 'Conectado' : 'Desconectado'}`, result.status === 'connected' ? 'success' : 'info');
      await _loadIntegraciones();
    }
  }

  async function addWebhook() {
    const url = document.getElementById('webhook-url').value.trim();
    if (!url) {
      toast('Ingresa la URL del webhook', 'warning');
      return;
    }

    await ZenicDB.addWebhook(url, ['all']);
    document.getElementById('webhook-url').value = '';
    toast('Webhook añadido 🔗', 'success');
    await _loadIntegraciones();
  }

  async function deleteWebhook(id) {
    await ZenicDB.deleteWebhook(id);
    toast('Webhook eliminado', 'info');
    await _loadIntegraciones();
  }

  // ============================================================
  // CONFIGURACIÓN
  // ============================================================
  async function _loadConfiguracion() {
    try {
      const settings = await ZenicAPI.getSettings();

      // Apply saved settings to UI
      if (settings.dark_mode !== undefined) {
        document.getElementById('setting-dark').checked = settings.dark_mode === 'true';
      }
      if (settings.notifications !== undefined) {
        document.getElementById('setting-notif').checked = settings.notifications !== 'false';
      }
      if (settings.auto_hitl !== undefined) {
        document.getElementById('setting-autohitl').checked = settings.auto_hitl === 'true';
      }
      if (settings.audit_detailed !== undefined) {
        document.getElementById('setting-audit').checked = settings.audit_detailed !== 'false';
      }
    } catch(e) {
      console.error('[App] Config load error:', e);
    }
  }

  function toggleDarkMode() {
    const isDark = document.getElementById('setting-dark').checked;
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    saveSettings();
  }

  function toggleNotifications() {
    saveSettings();
  }

  async function saveSettings() {
    const settings = {
      dark_mode: document.getElementById('setting-dark').checked.toString(),
      notifications: document.getElementById('setting-notif').checked.toString(),
      auto_hitl: document.getElementById('setting-autohitl').checked.toString(),
      audit_detailed: document.getElementById('setting-audit').checked.toString(),
      language: document.getElementById('setting-lang').value,
      timezone: document.getElementById('setting-tz').value
    };

    await ZenicAPI.saveSettings(settings);
  }

  async function exportData() {
    const data = await ZenicAPI.exportAllData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `zenic-backup-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('Datos exportados correctamente 📤', 'success');
  }

  async function clearCache() {
    await ZenicAPI.clearCache();
    toast('Caché limpiado 🗑️', 'success');
  }

  async function resetApp() {
    showModal(
      '⚠️ Restaurar Fábrica',
      '<p style="color:var(--red)">Esta acción eliminará TODOS los datos de la aplicación. ¿Estás seguro?</p>',
      [
        { text: 'Cancelar', class: 'btn-secondary', action: () => closeModal() },
        { text: 'Eliminar Todo', class: 'btn-danger', action: async () => {
          await ZenicAPI.resetApp();
          closeModal();
          logout();
          toast('Aplicación restaurada', 'info');
        }}
      ]
    );
  }

  // ============================================================
  // PERFIL
  // ============================================================
  async function _loadPerfil() {
    try {
      const user = await ZenicAuth.getCurrentUser();
      if (!user) return;

      const letter = user.name ? user.name.charAt(0).toUpperCase() : 'Z';

      document.getElementById('profile-avatar-large').textContent = letter;
      document.getElementById('profile-name').textContent = user.name;
      document.getElementById('profile-email').textContent = user.email;
      document.getElementById('profile-role-badge').textContent = user.role;

      document.getElementById('profile-edit-name').value = user.name;
      document.getElementById('profile-edit-email').value = user.email;
      document.getElementById('profile-edit-org').value = user.organization || '';

      // Stats
      const auditCount = await ZenicDB.countWhere('audit_logs', 'user_id = ?', [user.id]);
      document.getElementById('stat-sessions').textContent = Math.max(1, Math.floor(auditCount / 3));
      document.getElementById('stat-actions').textContent = auditCount;
      document.getElementById('stat-last-login').textContent = user.lastLogin ? _formatDate(user.lastLogin) : 'Ahora';
      document.getElementById('stat-member-since').textContent = user.createdAt ? _formatDate(user.createdAt) : 'Hoy';

    } catch(e) {
      console.error('[App] Perfil load error:', e);
    }
  }

  async function updateProfile() {
    const name = document.getElementById('profile-edit-name').value.trim();
    const org = document.getElementById('profile-edit-org').value.trim();

    if (!name) {
      toast('El nombre es requerido', 'warning');
      return;
    }

    const session = ZenicAuth.getSession();
    const result = await ZenicAuth.updateProfile(session.userId, { name, organization: org });

    if (result.success) {
      // Update UI
      const letter = name.charAt(0).toUpperCase();
      document.getElementById('profile-avatar-large').textContent = letter;
      document.getElementById('profile-name').textContent = name;
      document.getElementById('header-avatar-letter').textContent = letter;
      document.getElementById('drawer-avatar').textContent = letter;
      document.getElementById('drawer-user-name').textContent = name;

      toast('Perfil actualizado ✓', 'success');
    }
  }

  async function changePassword() {
    const current = document.getElementById('profile-current-pw').value;
    const newPw = document.getElementById('profile-new-pw').value;
    const confirm = document.getElementById('profile-confirm-pw').value;

    if (!current || !newPw) {
      toast('Completa todos los campos', 'warning');
      return;
    }

    if (newPw !== confirm) {
      toast('Las contraseñas no coinciden', 'error');
      return;
    }

    if (newPw.length < 6) {
      toast('La contraseña debe tener al menos 6 caracteres', 'warning');
      return;
    }

    const session = ZenicAuth.getSession();
    const result = await ZenicAuth.changePassword(session.userId, current, newPw);

    if (result.success) {
      document.getElementById('profile-current-pw').value = '';
      document.getElementById('profile-new-pw').value = '';
      document.getElementById('profile-confirm-pw').value = '';
      toast('Contraseña cambiada exitosamente 🔑', 'success');
    } else {
      toast(result.error, 'error');
    }
  }

  // ============================================================
  // AGENT DETAIL MODAL
  // ============================================================
  async function showAgentDetail(agentId) {
    const agent = await ZenicAPI.getAgent(agentId);
    if (!agent) return;

    showModal(agent.emoji + ' ' + agent.name, `
      <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:48px">${agent.emoji}</div>
      </div>
      <div class="about-info">
        <div class="about-row"><span>Estado</span><span>${agent.status === 'active' ? '🟢 Activo' : '🟡 Inactivo'}</span></div>
        <div class="about-row"><span>Tipo</span><span>${agent.type}</span></div>
        <div class="about-row"><span>Modelo</span><span>${agent.model}</span></div>
        <div class="about-row"><span>Tareas</span><span>${agent.total_tasks || 0}</span></div>
        <div class="about-row"><span>Tasa de Éxito</span><span>${agent.success_rate || 0}%</span></div>
        <div class="about-row"><span>Temperatura</span><span>${agent.temperature}</span></div>
        <div class="about-row"><span>Max Tokens</span><span>${agent.max_tokens}</span></div>
      </div>
      <div style="margin-top:16px">
        <p style="font-size:13px;color:var(--text-secondary)">${agent.description || ''}</p>
      </div>
    `, [
      { text: 'Activar', class: 'btn-primary', action: async () => {
        await ZenicAPI.updateAgentStatus(agentId, 'active');
        closeModal();
        toast('Agente activado', 'success');
        if (currentPage === 'dashboard') await _loadDashboard();
      }},
      { text: 'Cerrar', class: 'btn-secondary', action: () => closeModal() }
    ]);
  }

  // ============================================================
  // DRAWER
  // ============================================================
  function toggleDrawer() {
    const drawer = document.getElementById('side-drawer');
    const overlay = document.getElementById('drawer-overlay');
    const isOpen = drawer.classList.contains('open');

    drawer.classList.toggle('open', !isOpen);
    overlay.classList.toggle('active', !isOpen);
  }

  function closeDrawer() {
    document.getElementById('side-drawer').classList.remove('open');
    document.getElementById('drawer-overlay').classList.remove('active');
  }

  // ============================================================
  // NOTIFICATIONS
  // ============================================================
  async function showNotifications() {
    const panel = document.getElementById('notif-panel');
    const overlay = document.getElementById('notif-overlay');
    panel.classList.add('open');
    overlay.classList.add('active');

    const session = ZenicAuth.getSession();
    const notifs = await ZenicDB.getNotifications(session?.userId);

    const listEl = document.getElementById('notif-list');
    if (!notifs || notifs.length === 0) {
      listEl.innerHTML = '<div class="empty-state"><p>Sin notificaciones</p></div>';
    } else {
      listEl.innerHTML = notifs.map(n => `
        <div class="notif-item">
          <div class="notif-item-title">${n.title}</div>
          <div class="notif-item-body">${n.body || ''}</div>
          <div class="notif-item-time">${_timeAgo(n.created_at)}</div>
        </div>
      `).join('');
    }
  }

  function closeNotifications() {
    document.getElementById('notif-panel').classList.remove('open');
    document.getElementById('notif-overlay').classList.remove('active');
  }

  async function clearNotifications() {
    const session = ZenicAuth.getSession();
    await ZenicDB.clearNotifications(session?.userId);
    document.getElementById('notif-list').innerHTML = '<div class="empty-state"><p>Sin notificaciones</p></div>';
    document.getElementById('notif-count').style.display = 'none';
    toast('Notificaciones limpiadas', 'info');
  }

  // ============================================================
  // TOAST
  // ============================================================
  function toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span class="toast-icon">${icons[type]}</span><span class="toast-msg">${message}</span>`;

    container.appendChild(el);

    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'all 0.3s ease';
      setTimeout(() => el.remove(), 300);
    }, 3500);
  }

  // ============================================================
  // MODAL
  // ============================================================
  function showModal(title, bodyHtml, buttons = []) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;

    const footer = document.getElementById('modal-footer');
    footer.innerHTML = '';
    buttons.forEach(btn => {
      const button = document.createElement('button');
      button.className = `btn ${btn.class || 'btn-secondary'}`;
      button.textContent = btn.text;
      button.onclick = btn.action;
      footer.appendChild(button);
    });

    document.getElementById('modal-overlay').classList.add('active');
  }

  function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
  }

  // ============================================================
  // HELPERS
  // ============================================================
  function _timeAgo(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'Ahora';
    if (diffMin < 60) return `Hace ${diffMin}m`;
    if (diffHour < 24) return `Hace ${diffHour}h`;
    if (diffDay < 7) return `Hace ${diffDay}d`;
    return date.toLocaleDateString('es');
  }

  function _formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function _setButtonLoading(selector, loading) {
    const btn = document.querySelector(selector);
    if (btn) {
      btn.disabled = loading;
      btn.style.opacity = loading ? '0.7' : '1';
    }
  }

  // ============================================================
  // INIT ON DOM READY
  // ============================================================
  document.addEventListener('DOMContentLoaded', init);

  // ============================================================
  // PUBLIC API
  // ============================================================
  return {
    init,
    navigate,
    login,
    register,
    logout,
    showLogin,
    showRegister,
    togglePasswordVisibility,
    toggleDrawer,
    closeDrawer,
    showNotifications,
    closeNotifications,
    clearNotifications,
    updateChart,
    createHITLRequest,
    approveHITL,
    rejectHITL,
    addSecret,
    verifyIntegrity,
    exportAuditLog,
    toggleNichoExpand,
    deployNicho,
    filterNichos,
    showAddTool,
    hideAddTool,
    createTool,
    createServer,
    toggleToolStatus,
    deleteTool,
    switchTab,
    showAddPolicy,
    hideAddPolicy,
    createPolicy,
    togglePolicy,
    deletePolicy,
    upgradePlan,
    toggleIntegration,
    addWebhook,
    deleteWebhook,
    toggleDarkMode,
    toggleNotifications,
    saveSettings,
    exportData,
    clearCache,
    resetApp,
    updateProfile,
    changePassword,
    showAgentDetail,
    toast,
    showModal,
    closeModal
  };
})();
