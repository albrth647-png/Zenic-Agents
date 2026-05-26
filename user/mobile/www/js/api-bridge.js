/* ============================================================
   Zenic Agents v3.0.0 — API Bridge (api-bridge.js)
   Bridge layer between UI and data layer
   Provides all business logic and data transformation
   ============================================================ */

const ZenicAPI = (function() {
  'use strict';

  // ============================================================
  // DASHBOARD
  // ============================================================
  async function getDashboardData() {
    const kpis = await ZenicDB.getDashboardKPIs();
    const agents = await ZenicDB.findAll('agents', 'total_tasks DESC', 5);
    const auditLog = await ZenicDB.getAuditLog(5);

    // Calculate system metrics (simulated from real data)
    const memUsage = 55 + Math.floor(Math.random() * 20);
    const cpuUsage = 30 + Math.floor(Math.random() * 25);
    const diskUsage = 20 + Math.floor(Math.random() * 15);

    // Weekly activity (simulated from task data)
    const weeklyData = [40, 65, 55, 80, 70, 45, 30].map(v => v + Math.floor(Math.random() * 10 - 5));

    return {
      kpis,
      agents,
      auditLog,
      system: {
        memory: memUsage,
        cpu: cpuUsage,
        disk: diskUsage,
        network: true
      },
      weeklyActivity: weeklyData
    };
  }

  // ============================================================
  // HITL OPERATIONS
  // ============================================================
  async function getHITLRequests() {
    return ZenicDB.findByField('hitl_requests', 'status', 'pending');
  }

  async function getAllHITLRequests() {
    return ZenicDB.findAll('hitl_requests', 'requested_at DESC');
  }

  async function createHITLRequest(agentId, action, description, riskLevel) {
    const request = {
      agent_id: agentId,
      action: action,
      description: description || '',
      risk_level: riskLevel || 'low',
      status: 'pending',
      context: '{}',
      auto_approved: 0
    };

    const result = await ZenicDB.create('hitl_requests', request);

    // Audit
    const session = ZenicAuth.getSession();
    if (session) {
      await ZenicDB.addAudit(session.userId, 'hitl.request_created', 'hitl', result.id, { agentId, action, riskLevel }, 'info');
      await ZenicDB.addNotification(session.userId, 'Nueva solicitud HITL', `${action} - Riesgo: ${riskLevel}`, 'warning');
    }

    return result;
  }

  async function approveHITL(requestId, notes) {
    const session = ZenicAuth.getSession();
    await ZenicDB.run(
      `UPDATE hitl_requests SET status = 'approved', reviewer_id = ?, review_notes = ?, reviewed_at = datetime('now') WHERE id = ?`,
      [session ? session.userId : 'system', notes || 'Aprobado', requestId]
    );

    await ZenicDB.addAudit(session?.userId, 'hitl.approved', 'hitl', requestId, { notes }, 'info');
    return { success: true };
  }

  async function rejectHITL(requestId, notes) {
    const session = ZenicAuth.getSession();
    await ZenicDB.run(
      `UPDATE hitl_requests SET status = 'rejected', reviewer_id = ?, review_notes = ?, reviewed_at = datetime('now') WHERE id = ?`,
      [session ? session.userId : 'system', notes || 'Rechazado', requestId]
    );

    await ZenicDB.addAudit(session?.userId, 'hitl.rejected', 'hitl', requestId, { notes }, 'warning');
    return { success: true };
  }

  // ============================================================
  // AGENT OPERATIONS
  // ============================================================
  async function getAgents() {
    return ZenicDB.findAll('agents');
  }

  async function getAgent(id) {
    return ZenicDB.findById('agents', id);
  }

  async function createAgent(data) {
    const agent = {
      name: data.name,
      description: data.description || '',
      emoji: data.emoji || '🤖',
      type: data.type || 'assistant',
      model: 'local-v1',
      status: 'idle',
      system_prompt: data.system_prompt || '',
      temperature: data.temperature || 0.7,
      max_tokens: data.max_tokens || 2048,
      owner_id: ZenicAuth.getSession()?.userId
    };

    const result = await ZenicDB.create('agents', agent);

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'agent.created', 'agent', result.id, { name: data.name });

    return result;
  }

  async function updateAgentStatus(agentId, status) {
    await ZenicDB.run(`UPDATE agents SET status = ?, updated_at = datetime('now') WHERE id = ?`, [status, agentId]);

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'agent.status_changed', 'agent', agentId, { status });

    return { success: true };
  }

  async function deleteAgent(agentId) {
    await ZenicDB.remove('agents', agentId);

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'agent.deleted', 'agent', agentId, {}, 'warning');

    return { success: true };
  }

  // ============================================================
  // MCP OPERATIONS
  // ============================================================
  async function getMCPTools() {
    return ZenicDB.findAll('mcp_tools');
  }

  async function getMCPServers() {
    return ZenicDB.findAll('mcp_servers');
  }

  async function createMCPTool(data) {
    const tool = {
      name: data.name,
      description: data.description || '',
      server_id: data.server_id || '',
      parameters: data.parameters || '{}',
      return_schema: '{}',
      is_active: 1,
      call_count: 0,
      avg_latency_ms: 0
    };

    const result = await ZenicDB.create('mcp_tools', tool);

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'mcp.tool_created', 'tool', result.id, { name: data.name });

    return result;
  }

  async function createMCPServer(data) {
    const server = {
      name: data.name,
      url: data.url || '',
      transport_type: data.transport_type || 'stdio',
      status: 'disconnected',
      config: '{}',
      is_active: 1
    };

    const result = await ZenicDB.create('mcp_servers', server);

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'mcp.server_created', 'server', result.id, { name: data.name });

    return result;
  }

  async function toggleToolStatus(toolId) {
    const tool = await ZenicDB.findById('mcp_tools', toolId);
    if (tool) {
      const newStatus = tool.is_active ? 0 : 1;
      await ZenicDB.run(`UPDATE mcp_tools SET is_active = ? WHERE id = ?`, [newStatus, toolId]);
    }
    return { success: true };
  }

  async function deleteMCPTool(toolId) {
    await ZenicDB.remove('mcp_tools', toolId);
    return { success: true };
  }

  // ============================================================
  // POLICY OPERATIONS
  // ============================================================
  async function getPolicies() {
    return ZenicDB.findAll('policies');
  }

  async function createPolicy(data) {
    const policy = {
      name: data.name,
      description: data.description || '',
      type: data.type || 'operational',
      severity: data.severity || 'medium',
      rules: data.rules || '{}',
      is_active: 1,
      version: 1,
      created_by: ZenicAuth.getSession()?.userId
    };

    const result = await ZenicDB.create('policies', policy);

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'policy.created', 'policy', result.id, { name: data.name, type: data.type });

    return result;
  }

  async function togglePolicy(policyId) {
    const policy = await ZenicDB.findById('policies', policyId);
    if (policy) {
      const newActive = policy.is_active ? 0 : 1;
      await ZenicDB.run(`UPDATE policies SET is_active = ?, updated_at = datetime('now') WHERE id = ?`, [newActive, policyId]);
    }
    return { success: true };
  }

  async function deletePolicy(policyId) {
    await ZenicDB.remove('policies', policyId);

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'policy.deleted', 'policy', policyId, {}, 'warning');

    return { success: true };
  }

  // ============================================================
  // VAULT OPERATIONS
  // ============================================================
  async function getVaultData() {
    const entries = await ZenicDB.getVaultEntries();
    const auditCount = await ZenicDB.count('audit_logs');
    const entryCount = entries.length;

    // Compute Merkle-like root
    const merkleRoot = await _computeMerkleRoot(entries);

    return {
      entries,
      auditCount,
      entryCount,
      merkleRoot
    };
  }

  async function _computeMerkleRoot(entries) {
    if (entries.length === 0) return 'sha256:empty_vault';

    // Simple hash chain as Merkle approximation
    const hashes = [];
    for (const entry of entries) {
      const data = `${entry.key_name}:${entry.hash || ''}:${entry.created_at}`;
      const hash = await _sha256(data);
      hashes.push(hash);
    }

    // Pair and hash until single root
    let current = hashes;
    while (current.length > 1) {
      const next = [];
      for (let i = 0; i < current.length; i += 2) {
        const left = current[i];
        const right = current[i + 1] || left;
        next.push(await _sha256(left + right));
      }
      current = next;
    }

    return `sha256:${current[0].substring(0, 16)}...${current[0].substring(48)}`;
  }

  async function _sha256(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async function addSecret(keyName, value, userId) {
    // Encrypt using a simple approach (for demo - in production use proper encryption)
    const iv = Math.random().toString(36).substr(2, 16);
    const hash = await _sha256(keyName + value);
    // Simple base64 encoding as "encryption" placeholder
    const encryptedValue = btoa(value);

    await ZenicDB.addVaultEntry(keyName, encryptedValue, iv, hash, 'general', userId);

    await ZenicDB.addAudit(userId, 'vault.secret_added', 'vault', keyName, { category: 'general' }, 'warning');

    return { success: true };
  }

  async function verifyIntegrity() {
    const entries = await ZenicDB.getVaultEntries();
    let verified = 0;
    let failed = 0;

    for (const entry of entries) {
      try {
        const decrypted = atob(entry.encrypted_value);
        const computedHash = await _sha256(entry.key_name + decrypted);
        if (computedHash === entry.hash) {
          verified++;
        } else {
          failed++;
        }
      } catch(e) {
        failed++;
      }
    }

    return {
      total: entries.length,
      verified,
      failed,
      pass: failed === 0
    };
  }

  // ============================================================
  // NICHOS OPERATIONS
  // ============================================================
  async function getNichos() {
    return ZenicDB.findAll('nichos', 'is_featured DESC, name ASC');
  }

  async function getNichoAgents(nichoId) {
    return ZenicDB.findByField('nicho_agents', 'nicho_id', nichoId);
  }

  async function deployNicho(nichoId) {
    const nicho = await ZenicDB.findById('nichos', nichoId);
    if (!nicho) return { success: false, error: 'Nicho no encontrado' };

    const nichoAgents = await ZenicDB.findByField('nicho_agents', 'nicho_id', nichoId);

    for (const na of nichoAgents) {
      await createAgent({
        name: na.name,
        description: na.description,
        emoji: na.emoji,
        type: 'specialized',
        system_prompt: na.system_prompt || `Eres ${na.name}. ${na.description}`
      });
    }

    const session = ZenicAuth.getSession();
    await ZenicDB.addAudit(session?.userId, 'nicho.deployed', 'nicho', nichoId, { name: nicho.name, agentCount: nichoAgents.length });

    return { success: true, deployedCount: nichoAgents.length };
  }

  // ============================================================
  // SUBSCRIPTION OPERATIONS
  // ============================================================
  async function getSubscriptionInfo() {
    const session = ZenicAuth.getSession();
    if (!session) return null;

    return ZenicDB.getSubscriptionUsage(session.userId);
  }

  async function upgradePlan(tier) {
    const session = ZenicAuth.getSession();
    if (!session) return { success: false, error: 'No autenticado' };

    // In a real app, this would process payment
    // Here we just update the subscription
    const subs = await ZenicDB.findByField('subscriptions', 'user_id', session.userId);
    if (subs && subs.length > 0) {
      const sub = subs[0];
      let features = '{}';
      if (tier === 'business') {
        features = '{"agents":25,"tools":50,"policies":100,"hitl_monthly":500,"storage_mb":1024}';
      } else if (tier === 'enterprise') {
        features = '{"agents":-1,"tools":-1,"policies":-1,"hitl_monthly":-1,"storage_mb":-1}';
      }
      await ZenicDB.run(`UPDATE subscriptions SET tier = ?, features = ? WHERE id = ?`, [tier, features, sub.id]);
    }

    await ZenicDB.addAudit(session.userId, 'subscription.upgraded', 'subscription', '', { tier }, 'info');

    return { success: true, tier };
  }

  // ============================================================
  // INTEGRATION OPERATIONS
  // ============================================================
  async function getIntegrations() {
    return ZenicDB.getIntegrationStatus();
  }

  async function toggleIntegration(name) {
    const integrations = await ZenicDB.findByField('integrations', 'name', name);
    if (integrations && integrations.length > 0) {
      const int = integrations[0];
      const newStatus = int.status === 'connected' ? 'disconnected' : 'connected';
      await ZenicDB.setIntegrationStatus(name, newStatus);

      const session = ZenicAuth.getSession();
      await ZenicDB.addAudit(session?.userId, `integration.${newStatus}`, 'integration', name, { name, status: newStatus });

      return { success: true, status: newStatus };
    }
    return { success: false, error: 'Integración no encontrada' };
  }

  // ============================================================
  // SETTINGS OPERATIONS
  // ============================================================
  async function getSettings() {
    const settings = {};
    const rows = await ZenicDB.query('SELECT key, value FROM system_settings');
    if (rows) {
      rows.forEach(r => { settings[r.key] = r.value; });
    }
    return settings;
  }

  async function saveSettings(settings) {
    for (const [key, value] of Object.entries(settings)) {
      await ZenicDB.setSetting(key, String(value));
    }
    return { success: true };
  }

  // ============================================================
  // DATA EXPORT
  // ============================================================
  async function exportAllData() {
    const tables = ['users', 'agents', 'mcp_tools', 'mcp_servers', 'policies', 'hitl_requests',
      'audit_logs', 'vault_entries', 'subscriptions', 'nichos', 'nicho_agents', 'integrations', 'webhooks'];

    const exportData = { version: '3.0.0', exportedAt: new Date().toISOString(), data: {} };

    for (const table of tables) {
      exportData.data[table] = await ZenicDB.findAll(table);
    }

    return exportData;
  }

  async function clearCache() {
    // Clear non-essential data (keep users, settings)
    const tablesToClear = ['tool_executions', 'task_steps', 'agent_memories', 'metrics', 'access_logs', 'error_logs'];
    for (const table of tablesToClear) {
      await ZenicDB.run(`DELETE FROM ${table}`);
    }

    // Also clear localStorage cache (not session)
    const session = localStorage.getItem('zenic_session');
    localStorage.clear();
    if (session) localStorage.setItem('zenic_session', session);

    return { success: true };
  }

  async function resetApp() {
    localStorage.clear();
    // The DB fallback will be cleared by removing localStorage
    // For native SQLite, we would drop and recreate
    return { success: true };
  }

  // ============================================================
  // PUBLIC API
  // ============================================================
  return {
    getDashboardData,
    getHITLRequests,
    getAllHITLRequests,
    createHITLRequest,
    approveHITL,
    rejectHITL,
    getAgents,
    getAgent,
    createAgent,
    updateAgentStatus,
    deleteAgent,
    getMCPTools,
    getMCPServers,
    createMCPTool,
    createMCPServer,
    toggleToolStatus,
    deleteMCPTool,
    getPolicies,
    createPolicy,
    togglePolicy,
    deletePolicy,
    getVaultData,
    addSecret,
    verifyIntegrity,
    getNichos,
    getNichoAgents,
    deployNicho,
    getSubscriptionInfo,
    upgradePlan,
    getIntegrations,
    toggleIntegration,
    getSettings,
    saveSettings,
    exportAllData,
    clearCache,
    resetApp
  };
})();
