// ── Auth ──────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
  role?: string;
  tenant_id?: string;
}

export interface UserResponse {
  id: string;
  tenant_id: string;
  email: string;
  role: string;
  name: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

// ── Clients ───────────────────────────────────────────────────
export interface ClientCreate {
  name: string;
  email?: string;
  company?: string;
  phone?: string;
  stage?: string;
}

export interface ClientUpdate {
  name?: string;
  email?: string;
  company?: string;
  phone?: string;
  stage?: string;
}

export interface ClientResponse {
  id: number;
  tenant_id: string;
  name: string;
  email: string;
  company: string;
  phone: string;
  stage: string;
  created_at: string;
}

export interface ClientListResponse {
  clients: ClientResponse[];
  total: number;
}

export interface StatsResponse {
  total_clients: number;
  by_stage: Record<string, number>;
}

export interface PipelineResponse {
  stages: Record<string, ClientResponse[]>;
}

// ── Collector ─────────────────────────────────────────────────
export interface CollectorStartRequest {
  niche_id?: string;
}

export interface CollectorAnswerRequest {
  session_id: string;
  template_dict?: Record<string, unknown>;
  field_name: string;
  value: string;
  field_type?: string;
}

export interface CollectorSessionResponse {
  session_id: string;
  niche_id: string;
  questions: Record<string, unknown>[];
  answers_applied: number;
  answers_rejected: number;
  still_missing: number;
  completion_pct: number;
  is_complete: boolean;
  round_number: number;
  source: string;
}

// ── Plans ─────────────────────────────────────────────────────
export interface PlanResponse {
  slug: string;
  name: string;
  max_clients: number;
  max_messages_per_day: number;
  max_collector_sessions: number;
  features: string[];
}

export interface UsageResponse {
  plan: string;
  plan_name: string;
  daily: Record<string, number>;
  total_clients: number;
  total_clients_limit: number;
  features: string[];
}

export interface UpgradeRequest {
  tenant_id: string;
  plan: string;
}

// ── Channels ──────────────────────────────────────────────────
export interface ChannelPrefsResponse {
  preferred_channel: string;
  recipient: string;
  additional_channels: string[];
}

export interface ChannelPrefsUpdate {
  preferred_channel: string;
  recipient?: string;
  additional_channels?: string[];
}

export interface ChannelSendRequest {
  message?: string;
  tenant_id?: string;
  channel_override?: string;
  template_key?: string;
  niche_id?: string;
  template_vars?: Record<string, string>;
}

export interface ChannelSendResponse {
  success: boolean;
  channel: string;
  recipient: string;
  message: string;
  sent_via: string;
  language: string;
}

// ── Admin ─────────────────────────────────────────────────────
export interface HealthResponse {
  healthy: boolean;
  success_rates: Record<string, number>;
  latencies: Record<string, number>;
  circuit_breaker_states: Record<string, string>;
  timestamp: number;
  source: string;
}

export interface AuditEntryResponse {
  agent: string;
  input_hash: string;
  output_hash: string;
  source: string;
  confidence: number;
  duration_ms: number;
  retry_count: number;
  circuit_breaker_state: string;
  evidence_summary: string;
  timestamp: number;
}

export interface AuditListResponse {
  entries: AuditEntryResponse[];
  total: number;
}

export interface ConfigResponse {
  host: string;
  port: number;
  log_level: string;
  max_sessions: number;
  rate_limit_rpm: number;
  personality: string;
  language: string;
  streaming_enabled: boolean;
  tools_enabled: boolean;
  memory_enabled: boolean;
  debug: boolean;
}

// ── Tenant (from auth endpoints) ──────────────────────────────
export interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  plan: string;
  language: string;
  created_at: string;
}
