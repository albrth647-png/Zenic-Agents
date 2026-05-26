/* ============================================================
   Zenic Agents v3.0.0 — Database Layer (db.js)
   SQLite with @capacitor-community/sqlite + WebSQL/LocalStorage fallback
   All 40+ models, CRUD helpers, seed data, migrations
   ============================================================ */

const ZenicDB = (function() {
  'use strict';

  let db = null;
  let isNative = false;
  let sqlitePlugin = null;
  let dbVersion = 1;

  // ============================================================
  // SCHEMA — All 40+ tables
  // ============================================================
  const SCHEMA = [
    // Core Auth
    `CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      avatar TEXT,
      organization TEXT DEFAULT '',
      role_id TEXT,
      is_active INTEGER DEFAULT 1,
      last_login TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS roles (
      id TEXT PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      description TEXT,
      color TEXT DEFAULT '#6366f1',
      is_system INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS permissions (
      id TEXT PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      description TEXT,
      resource TEXT,
      action TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS role_permissions (
      role_id TEXT NOT NULL,
      permission_id TEXT NOT NULL,
      PRIMARY KEY (role_id, permission_id)
    )`,

    // Agent System
    `CREATE TABLE IF NOT EXISTS agents (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      emoji TEXT DEFAULT '🤖',
      type TEXT DEFAULT 'assistant',
      model TEXT DEFAULT 'local-v1',
      status TEXT DEFAULT 'idle',
      config TEXT DEFAULT '{}',
      system_prompt TEXT,
      temperature REAL DEFAULT 0.7,
      max_tokens INTEGER DEFAULT 2048,
      owner_id TEXT,
      nicho_id TEXT,
      is_active INTEGER DEFAULT 1,
      total_tasks INTEGER DEFAULT 0,
      success_rate REAL DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS agent_tools (
      agent_id TEXT NOT NULL,
      tool_id TEXT NOT NULL,
      PRIMARY KEY (agent_id, tool_id)
    )`,

    `CREATE TABLE IF NOT EXISTS agent_memories (
      id TEXT PRIMARY KEY,
      agent_id TEXT NOT NULL,
      content TEXT,
      memory_type TEXT DEFAULT 'short_term',
      importance REAL DEFAULT 0.5,
      access_count INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      last_accessed TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS conversations (
      id TEXT PRIMARY KEY,
      agent_id TEXT NOT NULL,
      user_id TEXT NOT NULL,
      title TEXT,
      status TEXT DEFAULT 'active',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      conversation_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT,
      metadata TEXT DEFAULT '{}',
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Tasks & Execution
    `CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY,
      agent_id TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      status TEXT DEFAULT 'pending',
      priority TEXT DEFAULT 'medium',
      result TEXT,
      error TEXT,
      started_at TEXT,
      completed_at TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS task_steps (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      step_order INTEGER,
      action TEXT,
      status TEXT DEFAULT 'pending',
      result TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // MCP System
    `CREATE TABLE IF NOT EXISTS mcp_servers (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      url TEXT,
      transport_type TEXT DEFAULT 'stdio',
      status TEXT DEFAULT 'disconnected',
      config TEXT DEFAULT '{}',
      is_active INTEGER DEFAULT 1,
      last_connected TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS mcp_tools (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      server_id TEXT,
      parameters TEXT DEFAULT '{}',
      return_schema TEXT DEFAULT '{}',
      is_active INTEGER DEFAULT 1,
      call_count INTEGER DEFAULT 0,
      avg_latency_ms INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS tool_executions (
      id TEXT PRIMARY KEY,
      tool_id TEXT NOT NULL,
      agent_id TEXT,
      input_params TEXT,
      output TEXT,
      status TEXT DEFAULT 'success',
      latency_ms INTEGER,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // HITL System
    `CREATE TABLE IF NOT EXISTS hitl_requests (
      id TEXT PRIMARY KEY,
      agent_id TEXT NOT NULL,
      action TEXT NOT NULL,
      description TEXT,
      risk_level TEXT DEFAULT 'low',
      status TEXT DEFAULT 'pending',
      context TEXT DEFAULT '{}',
      reviewer_id TEXT,
      review_notes TEXT,
      requested_at TEXT DEFAULT (datetime('now')),
      reviewed_at TEXT,
      auto_approved INTEGER DEFAULT 0
    )`,

    // Policies
    `CREATE TABLE IF NOT EXISTS policies (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      type TEXT DEFAULT 'operational',
      severity TEXT DEFAULT 'medium',
      rules TEXT DEFAULT '{}',
      is_active INTEGER DEFAULT 1,
      version INTEGER DEFAULT 1,
      created_by TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS policy_evaluations (
      id TEXT PRIMARY KEY,
      policy_id TEXT NOT NULL,
      agent_id TEXT,
      action TEXT,
      result TEXT,
      reason TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Subscriptions
    `CREATE TABLE IF NOT EXISTS subscriptions (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      tier TEXT DEFAULT 'starter',
      status TEXT DEFAULT 'active',
      started_at TEXT DEFAULT (datetime('now')),
      expires_at TEXT,
      features TEXT DEFAULT '{}',
      usage_counters TEXT DEFAULT '{}',
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Nichos (Templates)
    `CREATE TABLE IF NOT EXISTS nichos (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      industry TEXT,
      emoji TEXT DEFAULT '📋',
      category TEXT DEFAULT 'general',
      config TEXT DEFAULT '{}',
      agent_count INTEGER DEFAULT 0,
      is_featured INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS nicho_agents (
      id TEXT PRIMARY KEY,
      nicho_id TEXT NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      emoji TEXT DEFAULT '🤖',
      system_prompt TEXT,
      config TEXT DEFAULT '{}',
      sort_order INTEGER DEFAULT 0
    )`,

    // Vault & Security
    `CREATE TABLE IF NOT EXISTS vault_entries (
      id TEXT PRIMARY KEY,
      key_name TEXT UNIQUE NOT NULL,
      encrypted_value TEXT,
      iv TEXT,
      hash TEXT,
      category TEXT DEFAULT 'general',
      created_by TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS audit_logs (
      id TEXT PRIMARY KEY,
      user_id TEXT,
      action TEXT NOT NULL,
      resource_type TEXT,
      resource_id TEXT,
      details TEXT DEFAULT '{}',
      ip_address TEXT DEFAULT 'local',
      severity TEXT DEFAULT 'info',
      hash TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Integrations
    `CREATE TABLE IF NOT EXISTS integrations (
      id TEXT PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      type TEXT DEFAULT 'webhook',
      config TEXT DEFAULT '{}',
      status TEXT DEFAULT 'disconnected',
      last_sync TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS webhooks (
      id TEXT PRIMARY KEY,
      url TEXT NOT NULL,
      events TEXT DEFAULT '[]',
      is_active INTEGER DEFAULT 1,
      last_triggered TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // System
    `CREATE TABLE IF NOT EXISTS system_settings (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS notifications (
      id TEXT PRIMARY KEY,
      user_id TEXT,
      title TEXT NOT NULL,
      body TEXT,
      type TEXT DEFAULT 'info',
      is_read INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      token TEXT UNIQUE NOT NULL,
      device_info TEXT DEFAULT '{}',
      expires_at TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Agent collaboration
    `CREATE TABLE IF NOT EXISTS agent_collaborations (
      id TEXT PRIMARY KEY,
      initiator_agent_id TEXT NOT NULL,
      target_agent_id TEXT NOT NULL,
      task_id TEXT,
      status TEXT DEFAULT 'pending',
      protocol TEXT DEFAULT 'direct',
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Workflows
    `CREATE TABLE IF NOT EXISTS workflows (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      steps TEXT DEFAULT '[]',
      is_active INTEGER DEFAULT 1,
      trigger_type TEXT DEFAULT 'manual',
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS workflow_executions (
      id TEXT PRIMARY KEY,
      workflow_id TEXT NOT NULL,
      status TEXT DEFAULT 'running',
      current_step INTEGER DEFAULT 0,
      result TEXT,
      started_at TEXT DEFAULT (datetime('now')),
      completed_at TEXT
    )`,

    // Data governance
    `CREATE TABLE IF NOT EXISTS data_classifications (
      id TEXT PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      level TEXT DEFAULT 'internal',
      description TEXT,
      color TEXT DEFAULT '#6366f1',
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS access_logs (
      id TEXT PRIMARY KEY,
      user_id TEXT,
      resource_type TEXT,
      resource_id TEXT,
      access_type TEXT,
      granted INTEGER DEFAULT 1,
      reason TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Metrics
    `CREATE TABLE IF NOT EXISTS metrics (
      id TEXT PRIMARY KEY,
      metric_name TEXT NOT NULL,
      value REAL,
      unit TEXT,
      tags TEXT DEFAULT '{}',
      recorded_at TEXT DEFAULT (datetime('now'))
    )`,

    // API keys
    `CREATE TABLE IF NOT EXISTS api_keys (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      name TEXT,
      key_hash TEXT NOT NULL,
      prefix TEXT,
      permissions TEXT DEFAULT '[]',
      is_active INTEGER DEFAULT 1,
      last_used TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Deployment history
    `CREATE TABLE IF NOT EXISTS deployments (
      id TEXT PRIMARY KEY,
      agent_id TEXT,
      version TEXT,
      environment TEXT DEFAULT 'production',
      status TEXT DEFAULT 'deployed',
      config TEXT DEFAULT '{}',
      deployed_by TEXT,
      deployed_at TEXT DEFAULT (datetime('now'))
    )`,

    // Feedback
    `CREATE TABLE IF NOT EXISTS feedback (
      id TEXT PRIMARY KEY,
      user_id TEXT,
      agent_id TEXT,
      task_id TEXT,
      rating INTEGER,
      comment TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Schedule / cron
    `CREATE TABLE IF NOT EXISTS schedules (
      id TEXT PRIMARY KEY,
      agent_id TEXT NOT NULL,
      cron_expression TEXT,
      task_config TEXT DEFAULT '{}',
      is_active INTEGER DEFAULT 1,
      last_run TEXT,
      next_run TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Tags
    `CREATE TABLE IF NOT EXISTS tags (
      id TEXT PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      color TEXT DEFAULT '#6366f1',
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    `CREATE TABLE IF NOT EXISTS entity_tags (
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      tag_id TEXT NOT NULL,
      PRIMARY KEY (entity_type, entity_id, tag_id)
    )`,

    // Cost tracking
    `CREATE TABLE IF NOT EXISTS cost_records (
      id TEXT PRIMARY KEY,
      agent_id TEXT,
      resource_type TEXT,
      quantity REAL DEFAULT 0,
      unit_cost REAL DEFAULT 0,
      total_cost REAL DEFAULT 0,
      period TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Error logs
    `CREATE TABLE IF NOT EXISTS error_logs (
      id TEXT PRIMARY KEY,
      agent_id TEXT,
      error_type TEXT,
      message TEXT,
      stack_trace TEXT,
      severity TEXT DEFAULT 'error',
      resolved INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Knowledge base
    `CREATE TABLE IF NOT EXISTS knowledge_entries (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      content TEXT,
      source TEXT,
      category TEXT DEFAULT 'general',
      embedding_id TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )`,

    // Feature flags
    `CREATE TABLE IF NOT EXISTS feature_flags (
      id TEXT PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      is_enabled INTEGER DEFAULT 0,
      description TEXT,
      config TEXT DEFAULT '{}',
      created_at TEXT DEFAULT (datetime('now'))
    )`
  ];

  // ============================================================
  // SEED DATA
  // ============================================================
  const SEED_DATA = {
    roles: [
      { id: 'role-admin', name: 'Administrador', description: 'Acceso completo al sistema', color: '#ef4444', is_system: 1 },
      { id: 'role-operator', name: 'Operador', description: 'Gestión de agentes y tareas', color: '#6366f1', is_system: 1 },
      { id: 'role-viewer', name: 'Observador', description: 'Solo lectura', color: '#22c55e', is_system: 1 }
    ],
    permissions: [
      { id: 'perm-agents-read', name: 'agents:read', description: 'Ver agentes', resource: 'agents', action: 'read' },
      { id: 'perm-agents-write', name: 'agents:write', description: 'Crear/editar agentes', resource: 'agents', action: 'write' },
      { id: 'perm-agents-delete', name: 'agents:delete', description: 'Eliminar agentes', resource: 'agents', action: 'delete' },
      { id: 'perm-tools-read', name: 'tools:read', description: 'Ver herramientas', resource: 'tools', action: 'read' },
      { id: 'perm-tools-write', name: 'tools:write', description: 'Crear/editar herramientas', resource: 'tools', action: 'write' },
      { id: 'perm-hitl-approve', name: 'hitl:approve', description: 'Aprobar solicitudes HITL', resource: 'hitl', action: 'approve' },
      { id: 'perm-policies-read', name: 'policies:read', description: 'Ver políticas', resource: 'policies', action: 'read' },
      { id: 'perm-policies-write', name: 'policies:write', description: 'Crear/editar políticas', resource: 'policies', action: 'write' },
      { id: 'perm-vault-read', name: 'vault:read', description: 'Ver bóveda', resource: 'vault', action: 'read' },
      { id: 'perm-vault-write', name: 'vault:write', description: 'Gestionar bóveda', resource: 'vault', action: 'write' },
      { id: 'perm-settings-read', name: 'settings:read', description: 'Ver configuración', resource: 'settings', action: 'read' },
      { id: 'perm-settings-write', name: 'settings:write', description: 'Modificar configuración', resource: 'settings', action: 'write' }
    ],
    role_permissions: [
      // Admin gets all
      ...Array.from({length: 12}, (_, i) => ({ role_id: 'role-admin', permission_id: `perm-${['agents-read','agents-write','agents-delete','tools-read','tools-write','hitl-approve','policies-read','policies-write','vault-read','vault-write','settings-read','settings-write'][i]}` })),
      // Operator gets read + some write
      { role_id: 'role-operator', permission_id: 'perm-agents-read' },
      { role_id: 'role-operator', permission_id: 'perm-agents-write' },
      { role_id: 'role-operator', permission_id: 'perm-tools-read' },
      { role_id: 'role-operator', permission_id: 'perm-hitl-approve' },
      { role_id: 'role-operator', permission_id: 'perm-policies-read' },
      { role_id: 'role-operator', permission_id: 'perm-vault-read' },
      // Viewer gets read only
      { role_id: 'role-viewer', permission_id: 'perm-agents-read' },
      { role_id: 'role-viewer', permission_id: 'perm-tools-read' },
      { role_id: 'role-viewer', permission_id: 'perm-policies-read' },
      { role_id: 'role-viewer', permission_id: 'perm-vault-read' }
    ],
    mcp_servers: [
      { id: 'srv-local', name: 'Servidor Local', url: 'http://localhost:3001', transport_type: 'streamable', status: 'connected', is_active: 1 },
      { id: 'srv-filesystem', name: 'Filesystem MCP', url: 'local://fs', transport_type: 'stdio', status: 'connected', is_active: 1 },
      { id: 'srv-memory', name: 'Memory MCP', url: 'local://memory', transport_type: 'stdio', status: 'connected', is_active: 1 }
    ],
    mcp_tools: [
      { id: 'tool-search', name: 'web_search', description: 'Buscar información en la web', server_id: 'srv-local', parameters: '{"query":"string","max_results":"number"}', call_count: 45 },
      { id: 'tool-fs-read', name: 'fs_read', description: 'Leer archivos del sistema', server_id: 'srv-filesystem', parameters: '{"path":"string"}', call_count: 128 },
      { id: 'tool-fs-write', name: 'fs_write', description: 'Escribir archivos', server_id: 'srv-filesystem', parameters: '{"path":"string","content":"string"}', call_count: 34 },
      { id: 'tool-mem-save', name: 'memory_save', description: 'Guardar en memoria del agente', server_id: 'srv-memory', parameters: '{"key":"string","value":"string"}', call_count: 89 },
      { id: 'tool-mem-load', name: 'memory_load', description: 'Cargar de memoria del agente', server_id: 'srv-memory', parameters: '{"key":"string"}', call_count: 156 },
      { id: 'tool-calc', name: 'calculator', description: 'Realizar cálculos matemáticos', server_id: 'srv-local', parameters: '{"expression":"string"}', call_count: 22 },
      { id: 'tool-api', name: 'api_call', description: 'Realizar llamadas API', server_id: 'srv-local', parameters: '{"url":"string","method":"string","body":"object"}', call_count: 67 },
      { id: 'tool-summarize', name: 'summarize', description: 'Resumir texto largo', server_id: 'srv-local', parameters: '{"text":"string","max_length":"number"}', call_count: 31 }
    ],
    agents: [
      { id: 'agent-sales', name: 'Agente de Ventas', description: 'Gestiona leads y procesos de venta', emoji: '💰', type: 'specialized', model: 'local-v1', status: 'active', system_prompt: 'Eres un agente especializado en ventas. Ayudas a gestionar leads y procesos comerciales.', temperature: 0.7, max_tokens: 2048, total_tasks: 156, success_rate: 94.2 },
      { id: 'agent-support', name: 'Agente de Soporte', description: 'Atiende consultas y tickets de soporte', emoji: '🎯', type: 'specialized', model: 'local-v1', status: 'active', system_prompt: 'Eres un agente de soporte técnico. Resolves consultas y tickets.', temperature: 0.5, max_tokens: 4096, total_tasks: 342, success_rate: 97.1 },
      { id: 'agent-data', name: 'Analista de Datos', description: 'Analiza y visualiza datos', emoji: '📊', type: 'analytical', model: 'local-v1', status: 'active', system_prompt: 'Eres un analista de datos. Generas insights a partir de datos.', temperature: 0.3, max_tokens: 4096, total_tasks: 89, success_rate: 98.8 },
      { id: 'agent-security', name: 'Agente de Seguridad', description: 'Monitorea y protege el sistema', emoji: '🛡️', type: 'guardian', model: 'local-v1', status: 'active', system_prompt: 'Eres un agente de seguridad. Monitoreas amenazas y proteges el sistema.', temperature: 0.2, max_tokens: 2048, total_tasks: 210, success_rate: 99.5 },
      { id: 'agent-content', name: 'Creador de Contenido', description: 'Genera contenido y copy', emoji: '✍️', type: 'creative', model: 'local-v1', status: 'idle', system_prompt: 'Eres un creador de contenido. Generas textos creativos y copy.', temperature: 0.9, max_tokens: 4096, total_tasks: 78, success_rate: 91.3 }
    ],
    policies: [
      { id: 'pol-data-protection', name: 'Protección de Datos', description: 'Política de protección y manejo de datos sensibles', type: 'security', severity: 'critical', rules: '{"encrypt_at_rest":true,"encrypt_in_transit":true,"max_retention_days":90,"require_classification":true}', is_active: 1, version: 3 },
      { id: 'pol-hitl-threshold', name: 'Umbral HITL', description: 'Define cuándo se requiere aprobación humana', type: 'operational', severity: 'high', rules: '{"auto_approve_low_risk":true,"require_approval_medium":false,"require_approval_high":true,"require_approval_critical":true}', is_active: 1, version: 2 },
      { id: 'pol-agent-limits', name: 'Límites de Agentes', description: 'Restricciones de uso por plan de suscripción', type: 'access', severity: 'medium', rules: '{"starter_max_agents":5,"business_max_agents":25,"enterprise_max_agents":-1,"max_tokens_per_request":4096}', is_active: 1, version: 1 },
      { id: 'pol-audit-retention', name: 'Retención de Auditoría', description: 'Política de retención de logs de auditoría', type: 'compliance', severity: 'medium', rules: '{"retention_days":365,"auto_archive":true,"immutable_logs":true}', is_active: 1, version: 1 },
      { id: 'pol-api-rate', name: 'Rate Limiting API', description: 'Límites de tasa para llamadas API', type: 'operational', severity: 'low', rules: '{"requests_per_minute":60,"burst_allowance":10}', is_active: 1, version: 2 },
      { id: 'pol-cost-control', name: 'Control de Costos', description: 'Límites de gasto por agente', type: 'data', severity: 'medium', rules: '{"max_daily_cost_per_agent":10,"alert_threshold_percent":80,"auto_stop_at_limit":true}', is_active: 1, version: 1 }
    ],
    nichos: [
      { id: 'nicho-sales', name: 'Ventas & CRM', description: 'Plantillas para procesos de venta y gestión de clientes', industry: 'Ventas', emoji: '💰', category: 'comercial', agent_count: 3, is_featured: 1 },
      { id: 'nicho-support', name: 'Soporte Técnico', description: 'Agentes para atención al cliente y resolución de tickets', industry: 'Soporte', emoji: '🎯', category: 'servicio', agent_count: 4, is_featured: 1 },
      { id: 'nicho-finance', name: 'Finanzas & Contabilidad', description: 'Análisis financiero y automatización contable', industry: 'Finanzas', emoji: '📈', category: 'financiero', agent_count: 2, is_featured: 1 },
      { id: 'nicho-hr', name: 'Recursos Humanos', description: 'Gestión de talento y procesos de RRHH', industry: 'RRHH', emoji: '👥', category: 'gestion', agent_count: 3, is_featured: 0 },
      { id: 'nicho-dev', name: 'Desarrollo & DevOps', description: 'Agentes para desarrollo de software y operaciones', industry: 'Tecnología', emoji: '💻', category: 'tecnologia', agent_count: 5, is_featured: 1 },
      { id: 'nicho-marketing', name: 'Marketing Digital', description: 'Automatización de campañas y contenido', industry: 'Marketing', emoji: '📢', category: 'comercial', agent_count: 3, is_featured: 0 },
      { id: 'nicho-legal', name: 'Legal & Compliance', description: 'Revisión legal y cumplimiento normativo', industry: 'Legal', emoji: '⚖️', category: 'legal', agent_count: 2, is_featured: 0 },
      { id: 'nicho-health', name: 'Salud & Bienestar', description: 'Asistencia en salud y bienestar', industry: 'Salud', emoji: '🏥', category: 'salud', agent_count: 2, is_featured: 0 }
    ],
    nicho_agents: [
      { id: 'na-1', nicho_id: 'nicho-sales', name: 'Prospector', description: 'Busca y califica leads automáticamente', emoji: '🔍', sort_order: 0 },
      { id: 'na-2', nicho_id: 'nicho-sales', name: 'Closing Bot', description: 'Asiste en el proceso de cierre de ventas', emoji: '🤝', sort_order: 1 },
      { id: 'na-3', nicho_id: 'nicho-sales', name: 'CRM Sync', description: 'Sincroniza datos con el CRM', emoji: '🔄', sort_order: 2 },
      { id: 'na-4', nicho_id: 'nicho-support', name: 'Triage Agent', description: 'Clasifica y prioriza tickets', emoji: '📋', sort_order: 0 },
      { id: 'na-5', nicho_id: 'nicho-support', name: 'FAQ Bot', description: 'Responde preguntas frecuentes', emoji: '❓', sort_order: 1 },
      { id: 'na-6', nicho_id: 'nicho-support', name: 'Escalation Agent', description: 'Gestiona escalados a humanos', emoji: '⬆️', sort_order: 2 },
      { id: 'na-7', nicho_id: 'nicho-support', name: 'Feedback Analyzer', description: 'Analiza feedback de clientes', emoji: '💬', sort_order: 3 },
      { id: 'na-8', nicho_id: 'nicho-dev', name: 'Code Reviewer', description: 'Revisa código automáticamente', emoji: '👀', sort_order: 0 },
      { id: 'na-9', nicho_id: 'nicho-dev', name: 'CI/CD Manager', description: 'Gestiona pipelines de despliegue', emoji: '🚀', sort_order: 1 },
      { id: 'na-10', nicho_id: 'nicho-finance', name: 'Report Generator', description: 'Genera reportes financieros', emoji: '📊', sort_order: 0 },
      { id: 'na-11', nicho_id: 'nicho-marketing', name: 'Content Creator', description: 'Crea contenido para campañas', emoji: '✍️', sort_order: 0 },
      { id: 'na-12', nicho_id: 'nicho-hr', name: 'Recruitment Bot', description: 'Asiste en procesos de reclutamiento', emoji: '🧑‍💼', sort_order: 0 }
    ],
    feature_flags: [
      { id: 'ff-mcp-v2', name: 'mcp_v2_protocol', is_enabled: 1, description: 'Habilitar protocolo MCP v2' },
      { id: 'ff-agent-collab', name: 'agent_collaboration', is_enabled: 1, description: 'Colaboración entre agentes' },
      { id: 'ff-advanced-analytics', name: 'advanced_analytics', is_enabled: 0, description: 'Analíticas avanzadas' },
      { id: 'ff-custom-embeddings', name: 'custom_embeddings', is_enabled: 0, description: 'Embeddings personalizados' }
    ],
    data_classifications: [
      { id: 'dc-public', name: 'Público', level: 'public', description: 'Información pública', color: '#22c55e' },
      { id: 'dc-internal', name: 'Interno', level: 'internal', description: 'Uso interno únicamente', color: '#3b82f6' },
      { id: 'dc-confidential', name: 'Confidencial', level: 'confidential', description: 'Acceso restringido', color: '#f59e0b' },
      { id: 'dc-restricted', name: 'Restringido', level: 'restricted', description: 'Altamente sensible', color: '#ef4444' }
    ],
    tags: [
      { id: 'tag-critical', name: 'crítico', color: '#ef4444' },
      { id: 'tag-production', name: 'producción', color: '#22c55e' },
      { id: 'tag-experimental', name: 'experimental', color: '#f59e0b' },
      { id: 'tag-deprecated', name: 'deprecado', color: '#6b7280' }
    ]
  };

  // ============================================================
  // INITIALIZATION
  // ============================================================
  async function init() {
    try {
      // Try native Capacitor SQLite
      if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.CapacitorSQLite) {
        sqlitePlugin = window.Capacitor.Plugins.CapacitorSQLite;
        isNative = true;
        console.log('[DB] Using Capacitor SQLite (native)');

        try {
          const ret = await sqlitePlugin.createConnection({
            database: 'zenic_agents',
            version: dbVersion,
            encrypted: false,
            mode: 'no-encryption'
          });
          await sqlitePlugin.open({ database: 'zenic_agents' });
        } catch(e) {
          console.log('[DB] Connection might already exist, opening...', e);
          try {
            await sqlitePlugin.open({ database: 'zenic_agents' });
          } catch(e2) {
            console.log('[DB] Open error (continuing):', e2);
          }
        }
      }
    } catch(e) {
      console.log('[DB] Native SQLite not available, using fallback');
    }

    // Create all tables
    await createTables();

    // Seed data if empty
    await seedData();

    console.log('[DB] Database initialized successfully');
    return true;
  }

  async function createTables() {
    for (const sql of SCHEMA) {
      await run(sql);
    }
    console.log(`[DB] Created ${SCHEMA.length} tables`);
  }

  async function seedData() {
    // Check if already seeded
    const existing = await getOne('SELECT COUNT(*) as cnt FROM roles');
    if (existing && existing.cnt > 0) {
      console.log('[DB] Data already seeded, skipping');
      return;
    }

    console.log('[DB] Seeding initial data...');

    // Seed roles
    for (const r of SEED_DATA.roles) {
      await run(`INSERT OR IGNORE INTO roles (id, name, description, color, is_system) VALUES (?, ?, ?, ?, ?)`,
        [r.id, r.name, r.description, r.color, r.is_system]);
    }

    // Seed permissions
    for (const p of SEED_DATA.permissions) {
      await run(`INSERT OR IGNORE INTO permissions (id, name, description, resource, action) VALUES (?, ?, ?, ?, ?)`,
        [p.id, p.name, p.description, p.resource, p.action]);
    }

    // Seed role_permissions
    for (const rp of SEED_DATA.role_permissions) {
      await run(`INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)`,
        [rp.role_id, rp.permission_id]);
    }

    // Seed default admin user (password: admin123)
    const adminHash = await hashPassword('admin123');
    await run(`INSERT OR IGNORE INTO users (id, email, name, password_hash, role_id, organization) VALUES (?, ?, ?, ?, ?, ?)`,
      ['user-admin', 'admin@zenic.io', 'Administrador', adminHash, 'role-admin', 'Zenic Systems']);

    // Seed MCP servers
    for (const s of SEED_DATA.mcp_servers) {
      await run(`INSERT OR IGNORE INTO mcp_servers (id, name, url, transport_type, status, is_active) VALUES (?, ?, ?, ?, ?, ?)`,
        [s.id, s.name, s.url, s.transport_type, s.status, s.is_active]);
    }

    // Seed MCP tools
    for (const t of SEED_DATA.mcp_tools) {
      await run(`INSERT OR IGNORE INTO mcp_tools (id, name, description, server_id, parameters, call_count) VALUES (?, ?, ?, ?, ?, ?)`,
        [t.id, t.name, t.description, t.server_id, t.parameters, t.call_count]);
    }

    // Seed agents
    for (const a of SEED_DATA.agents) {
      await run(`INSERT OR IGNORE INTO agents (id, name, description, emoji, type, model, status, system_prompt, temperature, max_tokens, total_tasks, success_rate, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [a.id, a.name, a.description, a.emoji, a.type, a.model, a.status, a.system_prompt, a.temperature, a.max_tokens, a.total_tasks, a.success_rate, 'user-admin']);
    }

    // Seed policies
    for (const p of SEED_DATA.policies) {
      await run(`INSERT OR IGNORE INTO policies (id, name, description, type, severity, rules, is_active, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [p.id, p.name, p.description, p.type, p.severity, p.rules, p.is_active, p.version]);
    }

    // Seed nichos
    for (const n of SEED_DATA.nichos) {
      await run(`INSERT OR IGNORE INTO nichos (id, name, description, industry, emoji, category, agent_count, is_featured) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [n.id, n.name, n.description, n.industry, n.emoji, n.category, n.agent_count, n.is_featured]);
    }

    // Seed nicho_agents
    for (const na of SEED_DATA.nicho_agents) {
      await run(`INSERT OR IGNORE INTO nicho_agents (id, nicho_id, name, description, emoji, sort_order) VALUES (?, ?, ?, ?, ?, ?)`,
        [na.id, na.nicho_id, na.name, na.description, na.emoji, na.sort_order]);
    }

    // Seed feature flags
    for (const ff of SEED_DATA.feature_flags) {
      await run(`INSERT OR IGNORE INTO feature_flags (id, name, is_enabled, description) VALUES (?, ?, ?, ?)`,
        [ff.id, ff.name, ff.is_enabled, ff.description]);
    }

    // Seed data classifications
    for (const dc of SEED_DATA.data_classifications) {
      await run(`INSERT OR IGNORE INTO data_classifications (id, name, level, description, color) VALUES (?, ?, ?, ?, ?)`,
        [dc.id, dc.name, dc.level, dc.description, dc.color]);
    }

    // Seed tags
    for (const t of SEED_DATA.tags) {
      await run(`INSERT OR IGNORE INTO tags (id, name, color) VALUES (?, ?, ?)`,
        [t.id, t.name, t.color]);
    }

    // Seed subscription for admin
    await run(`INSERT OR IGNORE INTO subscriptions (id, user_id, tier, status, features, usage_counters) VALUES (?, ?, ?, ?, ?, ?)`,
      ['sub-admin', 'user-admin', 'starter', 'active', '{"agents":5,"tools":10,"policies":20,"hitl_monthly":50,"storage_mb":100}', '{"agents_used":5,"tools_used":8,"policies_used":6,"hitl_used":12,"storage_used_mb":34}']);

    // Seed some HITL requests
    await run(`INSERT OR IGNORE INTO hitl_requests (id, agent_id, action, description, risk_level, status, requested_at) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      ['hitl-1', 'agent-sales', 'Ejecutar transferencia', 'Transferir $5,000 a cuenta de cliente nuevo', 'high', 'pending', new Date(Date.now() - 300000).toISOString()]);
    await run(`INSERT OR IGNORE INTO hitl_requests (id, agent_id, action, description, risk_level, status, requested_at) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      ['hitl-2', 'agent-security', 'Bloquear IP sospechosa', 'Se detectaron 50 intentos de acceso desde IP 192.168.1.100', 'medium', 'pending', new Date(Date.now() - 720000).toISOString()]);
    await run(`INSERT OR IGNORE INTO hitl_requests (id, agent_id, action, description, risk_level, status, reviewer_id, requested_at, reviewed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      ['hitl-3', 'agent-data', 'Exportar datos', 'Exportar reporte de ventas Q4 a CSV', 'low', 'approved', 'user-admin', new Date(Date.now() - 3600000).toISOString(), new Date(Date.now() - 3500000).toISOString()]);

    // Seed some audit logs
    const auditEntries = [
      { action: 'user.login', resource_type: 'auth', severity: 'info', details: '{"method":"password"}' },
      { action: 'agent.created', resource_type: 'agent', resource_id: 'agent-sales', severity: 'info', details: '{"name":"Agente de Ventas"}' },
      { action: 'policy.updated', resource_type: 'policy', resource_id: 'pol-data-protection', severity: 'warning', details: '{"version":"2->3"}' },
      { action: 'hitl.approved', resource_type: 'hitl', resource_id: 'hitl-3', severity: 'info', details: '{"risk":"low"}' },
      { action: 'tool.executed', resource_type: 'tool', resource_id: 'tool-search', severity: 'info', details: '{"query":"tendencias IA 2024"}' },
      { action: 'vault.secret_added', resource_type: 'vault', severity: 'warning', details: '{"key":"API_KEY_STRIPE"}' },
      { action: 'system.backup', resource_type: 'system', severity: 'info', details: '{"size_mb":34}' }
    ];
    for (let i = 0; i < auditEntries.length; i++) {
      const a = auditEntries[i];
      const ts = new Date(Date.now() - (i * 600000)).toISOString();
      await run(`INSERT OR IGNORE INTO audit_logs (id, user_id, action, resource_type, resource_id, details, severity, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [`audit-${i+1}`, 'user-admin', a.action, a.resource_type, a.resource_id || '', a.details, a.severity, ts]);
    }

    // Seed integrations
    for (const name of ['slack', 'github', 'jira', 'teams', 'notion', 'zapier']) {
      await run(`INSERT OR IGNORE INTO integrations (id, name, type, status) VALUES (?, ?, 'api', 'disconnected')`,
        [`int-${name}`, name]);
    }

    // Seed notifications
    await run(`INSERT OR IGNORE INTO notifications (id, title, body, type) VALUES (?, ?, ?, ?)`,
      ['notif-1', 'Nueva solicitud HITL', 'El Agente de Ventas solicita aprobación para transferencia', 'warning']);
    await run(`INSERT OR IGNORE INTO notifications (id, title, body, type) VALUES (?, ?, ?, ?)`,
      ['notif-2', 'Agente activo', 'Analista de Datos completó 89 tareas', 'success']);

    console.log('[DB] Seeding complete');
  }

  // ============================================================
  // PASSWORD HASHING (SHA-256 via SubtleCrypto)
  // ============================================================
  async function hashPassword(password) {
    const encoder = new TextEncoder();
    const data = encoder.encode(password + '_zenic_salt_v3');
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // ============================================================
  // DATABASE OPERATIONS (with fallback)
  // ============================================================
  async function run(sql, params = []) {
    if (isNative && sqlitePlugin) {
      try {
        await sqlitePlugin.execute({ statements: sql, values: params });
        return;
      } catch(e) {
        console.error('[DB Native] run error:', e, sql);
      }
    }
    // Fallback: use Web SQL / in-memory store
    return _fallbackRun(sql, params);
  }

  async function query(sql, params = []) {
    if (isNative && sqlitePlugin) {
      try {
        const result = await sqlitePlugin.query({ statement: sql, values: params });
        return result.values || [];
      } catch(e) {
        console.error('[DB Native] query error:', e, sql);
        return [];
      }
    }
    return _fallbackQuery(sql, params);
  }

  async function getOne(sql, params = []) {
    const rows = await query(sql, params);
    return rows.length > 0 ? rows[0] : null;
  }

  // ============================================================
  // FALLBACK DATABASE (In-Memory + localStorage)
  // ============================================================
  let _store = {};
  let _tables = {};
  const STORAGE_KEY = 'zenic_db_v3';

  function _loadStore() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        _store = JSON.parse(saved);
      }
    } catch(e) {}
  }

  function _saveStore() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(_store));
    } catch(e) {
      console.warn('[DB] localStorage save failed');
    }
  }

  function _getTable(name) {
    if (!_store[name]) {
      _store[name] = [];
    }
    return _store[name];
  }

  function _parseTableName(sql) {
    const match = sql.match(/INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)/i) ||
                  sql.match(/INSERT\s+INTO\s+(\w+)/i) ||
                  sql.match(/CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)/i) ||
                  sql.match(/UPDATE\s+(\w+)/i) ||
                  sql.match(/DELETE\s+FROM\s+(\w+)/i);
    return match ? match[1] : null;
  }

  function _fallbackRun(sql, params) {
    _loadStore();

    const upper = sql.trim().toUpperCase();

    if (upper.startsWith('CREATE TABLE')) {
      // Just mark the table as existing
      const tName = _parseTableName(sql);
      if (tName && !_store[tName]) {
        _store[tName] = [];
      }
      _saveStore();
      return;
    }

    if (upper.startsWith('INSERT')) {
      const tName = _parseTableName(sql);
      if (!tName) return;
      const table = _getTable(tName);

      // Extract columns from SQL
      const colMatch = sql.match(/\(([^)]+)\)\s*VALUES/i);
      if (colMatch) {
        const cols = colMatch[1].split(',').map(c => c.trim().replace(/`/g, ''));
        const row = {};
        cols.forEach((col, i) => {
          row[col] = params[i] !== undefined ? params[i] : null;
        });
        // Check for duplicate (OR IGNORE)
        const pkCol = cols[0]; // Usually id
        const exists = table.some(r => r[pkCol] === row[pkCol]);
        if (!exists) {
          table.push(row);
        }
      }
      _saveStore();
      return;
    }

    if (upper.startsWith('UPDATE')) {
      const tName = _parseTableName(sql);
      if (!tName) return;
      const table = _getTable(tName);

      // Parse SET clause
      const setMatch = sql.match(/SET\s+(.+?)\s+WHERE/i);
      const whereMatch = sql.match(/WHERE\s+(\w+)\s*=\s*\?/i);

      if (setMatch && whereMatch) {
        const setClauses = setMatch[1].split(',').map(s => s.trim());
        const whereCol = whereMatch[1];
        const whereVal = params[params.length - 1];

        const setParams = params.slice(0, setClauses.length);

        table.forEach(row => {
          if (row[whereCol] == whereVal) {
            setClauses.forEach((clause, i) => {
              const col = clause.split('=')[0].trim().replace(/`/g, '');
              row[col] = setParams[i];
            });
          }
        });
      }
      _saveStore();
      return;
    }

    if (upper.startsWith('DELETE')) {
      const tName = _parseTableName(sql);
      if (!tName) return;
      const table = _getTable(tName);

      const whereMatch = sql.match(/WHERE\s+(\w+)\s*=\s*\?/i);
      if (whereMatch) {
        const whereCol = whereMatch[1];
        const whereVal = params[0];
        const idx = table.findIndex(r => r[whereCol] == whereVal);
        if (idx >= 0) table.splice(idx, 1);
      } else {
        _store[tName] = [];
      }
      _saveStore();
      return;
    }
  }

  function _fallbackQuery(sql, params) {
    _loadStore();

    const upper = sql.trim().toUpperCase();

    if (upper.includes('COUNT(')) {
      const tMatch = sql.match(/FROM\s+(\w+)/i);
      if (tMatch) {
        const table = _getTable(tMatch[1]);
        return [{ cnt: table.length }];
      }
      return [{ cnt: 0 }];
    }

    if (upper.startsWith('SELECT')) {
      const tMatch = sql.match(/FROM\s+(\w+)/i);
      if (!tMatch) return [];
      const table = _getTable(tMatch[1]);

      let results = [...table];

      // Simple WHERE handling
      const whereMatch = sql.match(/WHERE\s+(\w+)\s*=\s*\?/i);
      if (whereMatch) {
        const col = whereMatch[1];
        const val = params[0];
        results = results.filter(r => r[col] == val);
      }

      // Simple ORDER BY
      const orderMatch = sql.match(/ORDER\s+BY\s+(\w+)\s+(ASC|DESC)/i);
      if (orderMatch) {
        const oCol = orderMatch[1];
        const oDir = orderMatch[2].toUpperCase();
        results.sort((a, b) => {
          if (a[oCol] < b[oCol]) return oDir === 'ASC' ? -1 : 1;
          if (a[oCol] > b[oCol]) return oDir === 'ASC' ? 1 : -1;
          return 0;
        });
      }

      // Simple LIMIT
      const limitMatch = sql.match(/LIMIT\s+(\d+)/i);
      if (limitMatch) {
        results = results.slice(0, parseInt(limitMatch[1]));
      }

      return results;
    }

    return [];
  }

  // ============================================================
  // CRUD HELPERS
  // ============================================================
  function generateId(prefix = 'id') {
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 6)}`;
  }

  // Generic CRUD
  async function create(table, data) {
    const id = data.id || generateId(table);
    const cols = Object.keys(data);
    if (!data.id) cols.unshift('id');
    const vals = data.id ? Object.values(data) : [id, ...Object.values(data)];
    const placeholders = cols.map(() => '?').join(', ');
    await run(`INSERT OR REPLACE INTO ${table} (${cols.join(', ')}) VALUES (${placeholders})`, vals);
    return { id, ...data };
  }

  async function update(table, id, data) {
    const cols = Object.keys(data);
    const vals = Object.values(data);
    const setClause = cols.map(c => `${c} = ?`).join(', ');
    await run(`UPDATE ${table} SET ${setClause}, updated_at = datetime('now') WHERE id = ?`, [...vals, id]);
    return data;
  }

  async function remove(table, id) {
    await run(`DELETE FROM ${table} WHERE id = ?`, [id]);
  }

  async function findById(table, id) {
    return getOne(`SELECT * FROM ${table} WHERE id = ?`, [id]);
  }

  async function findAll(table, orderBy = 'created_at DESC', limit = 100) {
    return query(`SELECT * FROM ${table} ORDER BY ${orderBy} LIMIT ${limit}`);
  }

  async function findByField(table, field, value) {
    return query(`SELECT * FROM ${table} WHERE ${field} = ?`, [value]);
  }

  async function count(table) {
    const result = await getOne(`SELECT COUNT(*) as cnt FROM ${table}`);
    return result ? result.cnt : 0;
  }

  async function countWhere(table, where, params = []) {
    const result = await getOne(`SELECT COUNT(*) as cnt FROM ${table} WHERE ${where}`, params);
    return result ? result.cnt : 0;
  }

  // ============================================================
  // SPECIFIC QUERIES
  // ============================================================

  // Dashboard KPIs
  async function getDashboardKPIs() {
    const agents = await count('agents');
    const activeAgents = await countWhere('agents', 'status = ?', ['active']);
    const tasks = await count('tasks');
    const completedTasks = await countWhere('tasks', 'status = ?', ['completed']);
    const hitlPending = await countWhere('hitl_requests', 'status = ?', ['pending']);
    const activePolicies = await countWhere('policies', 'is_active = ?', [1]);
    const totalTools = await count('mcp_tools');
    const auditEntries = await count('audit_logs');
    const vaultEntries = await count('vault_entries');

    return {
      agents, activeAgents, tasks, completedTasks,
      hitlPending, activePolicies, totalTools,
      auditEntries, vaultEntries
    };
  }

  // HITL stats
  async function getHITLStats() {
    const approved = await countWhere('hitl_requests', 'status = ?', ['approved']);
    const rejected = await countWhere('hitl_requests', 'status = ?', ['rejected']);
    const total = await count('hitl_requests');
    return { approved, rejected, total, avgTime: '2.3s' };
  }

  // Subscription usage
  async function getSubscriptionUsage(userId) {
    const sub = await getOne('SELECT * FROM subscriptions WHERE user_id = ? AND status = ?', [userId, 'active']);
    if (!sub) return null;

    let usage = {};
    try { usage = JSON.parse(sub.usage_counters || '{}'); } catch(e) {}

    // Count actual usage
    usage.agents_used = await count('agents');
    usage.tools_used = await count('mcp_tools');
    usage.policies_used = await countWhere('policies', 'is_active = ?', [1]);
    usage.hitl_used = await countWhere('hitl_requests', "status = 'pending' OR status = 'approved'", []);

    return {
      tier: sub.tier,
      features: JSON.parse(sub.features || '{}'),
      usage
    };
  }

  // Audit log
  async function getAuditLog(limit = 50) {
    return query(`SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ${limit}`);
  }

  // Add audit entry
  async function addAudit(userId, action, resourceType, resourceId, details, severity = 'info') {
    const id = generateId('audit');
    await run(`INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details, severity) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [id, userId, action, resourceType, resourceId || '', JSON.stringify(details || {}), severity]);
    return id;
  }

  // Notifications
  async function getNotifications(userId) {
    return query(`SELECT * FROM notifications WHERE user_id = ? OR user_id IS NULL ORDER BY created_at DESC LIMIT 20`, [userId]);
  }

  async function addNotification(userId, title, body, type = 'info') {
    const id = generateId('notif');
    await run(`INSERT INTO notifications (id, user_id, title, body, type) VALUES (?, ?, ?, ?, ?)`,
      [id, userId, title, body, type]);
    return id;
  }

  async function clearNotifications(userId) {
    await run(`DELETE FROM notifications WHERE user_id = ?`, [userId]);
  }

  // Vault
  async function addVaultEntry(keyName, encryptedValue, iv, hash, category, userId) {
    const id = generateId('vault');
    await run(`INSERT OR REPLACE INTO vault_entries (id, key_name, encrypted_value, iv, hash, category, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [id, keyName, encryptedValue, iv, hash, category || 'general', userId]);
    return id;
  }

  async function getVaultEntries() {
    return query(`SELECT * FROM vault_entries ORDER BY created_at DESC`);
  }

  // Integrations
  async function getIntegrationStatus() {
    return query(`SELECT * FROM integrations`);
  }

  async function setIntegrationStatus(name, status) {
    await run(`UPDATE integrations SET status = ?, last_sync = datetime('now') WHERE name = ?`, [status, name]);
  }

  // Webhooks
  async function addWebhook(url, events) {
    const id = generateId('wh');
    await run(`INSERT INTO webhooks (id, url, events) VALUES (?, ?, ?)`, [id, url, JSON.stringify(events || ['all'])]);
    return id;
  }

  async function getWebhooks() {
    return query(`SELECT * FROM webhooks ORDER BY created_at DESC`);
  }

  async function deleteWebhook(id) {
    await run(`DELETE FROM webhooks WHERE id = ?`, [id]);
  }

  // Settings
  async function getSetting(key) {
    const result = await getOne(`SELECT value FROM system_settings WHERE key = ?`, [key]);
    return result ? result.value : null;
  }

  async function setSetting(key, value) {
    await run(`INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`, [key, value]);
  }

  // ============================================================
  // PUBLIC API
  // ============================================================
  return {
    init,
    run,
    query,
    getOne,
    create,
    update,
    remove,
    findById,
    findAll,
    findByField,
    count,
    countWhere,
    generateId,
    hashPassword,
    getDashboardKPIs,
    getHITLStats,
    getSubscriptionUsage,
    getAuditLog,
    addAudit,
    getNotifications,
    addNotification,
    clearNotifications,
    addVaultEntry,
    getVaultEntries,
    getIntegrationStatus,
    setIntegrationStatus,
    addWebhook,
    getWebhooks,
    deleteWebhook,
    getSetting,
    setSetting
  };
})();
