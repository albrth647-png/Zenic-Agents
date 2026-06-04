import type {
  AuditListResponse,
  ChannelPrefsResponse,
  ChannelPrefsUpdate,
  ChannelSendRequest,
  ChannelSendResponse,
  ClientCreate,
  ClientListResponse,
  ClientResponse,
  ClientUpdate,
  CollectorAnswerRequest,
  CollectorSessionResponse,
  CollectorStartRequest,
  ConfigResponse,
  HealthResponse,
  LoginRequest,
  PlanResponse,
  PipelineResponse,
  RegisterRequest,
  StatsResponse,
  TenantResponse,
  TokenResponse,
  UpgradeRequest,
  UsageResponse,
  UserResponse,
} from './types';

const BASE = '/api/v1';

// ── Token management ──────────────────────────────────────────

function getToken(): string | null {
  return localStorage.getItem('zenic_token');
}

function setToken(token: string): void {
  localStorage.setItem('zenic_token', token);
}

function clearToken(): void {
  localStorage.removeItem('zenic_token');
}

function getUser(): UserResponse | null {
  const raw = localStorage.getItem('zenic_user');
  return raw ? JSON.parse(raw) : null;
}

function setUser(user: UserResponse): void {
  localStorage.setItem('zenic_user', JSON.stringify(user));
}

function clearUser(): void {
  localStorage.removeItem('zenic_user');
}

export { getToken, setToken, clearToken, getUser, setUser, clearUser };

// ── Fetch helper ──────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  useAuth = true,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (useAuth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearToken();
    clearUser();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }

  return data as T;
}

// ── Auth ──────────────────────────────────────────────────────

export const auth = {
  login: (payload: LoginRequest) =>
    request<TokenResponse>('POST', '/auth/login', payload, false),

  register: (payload: RegisterRequest) =>
    request<UserResponse>('POST', '/auth/register', payload, false),

  me: () => request<UserResponse>('GET', '/auth/me'),

  tenants: () => request<TenantResponse[]>('GET', '/auth/tenants'),
};

// ── Clients ───────────────────────────────────────────────────

export const clients = {
  list: (search = '') =>
    request<ClientListResponse>('GET', `/clients?search=${encodeURIComponent(search)}`),

  get: (id: string) => request<ClientResponse>('GET', `/clients/${id}`),

  create: (payload: ClientCreate) =>
    request<ClientResponse>('POST', '/clients', payload),

  update: (id: string, payload: ClientUpdate) =>
    request<ClientResponse>('PUT', `/clients/${id}`, payload),

  delete: (id: string) =>
    request<{ ok: boolean; deleted: string }>('DELETE', `/clients/${id}`),

  stats: () => request<StatsResponse>('GET', '/clients/stats'),

  pipeline: () => request<PipelineResponse>('GET', '/clients/pipeline'),
};

// ── Collector ─────────────────────────────────────────────────

export const collector = {
  start: (payload: CollectorStartRequest) =>
    request<CollectorSessionResponse>('POST', '/collector/start', payload),

  questions: (sessionId: string, templateDict: Record<string, unknown> = {}) =>
    request<CollectorSessionResponse>('POST', '/collector/questions', {
      session_id: sessionId,
      template_dict: templateDict,
    }),

  answer: (payload: CollectorAnswerRequest) =>
    request<CollectorSessionResponse>('POST', '/collector/answer', payload),

  answers: (sessionId: string, answers: Record<string, string>) =>
    request<CollectorSessionResponse>('POST', '/collector/answers', {
      session_id: sessionId,
      answers,
    }),

  progress: (sessionId: string) =>
    request<CollectorSessionResponse>('GET', `/collector/${sessionId}/progress`),

  finalize: (sessionId: string) =>
    request<CollectorSessionResponse>('POST', '/collector/finalize', {
      session_id: sessionId,
    }),

  suggestions: (fieldName: string, fieldType = 'text') =>
    request<CollectorSessionResponse>('POST', '/collector/suggestions', {
      field_name: fieldName,
      field_type: fieldType,
    }),
};

// ── Plans ─────────────────────────────────────────────────────

export const plans = {
  list: () => request<PlanResponse[]>('GET', '/plans'),

  usage: () => request<UsageResponse>('GET', '/plans/usage'),

  upgrade: (payload: UpgradeRequest) =>
    request<UsageResponse>('POST', '/plans/upgrade', payload),
};

// ── Channels ──────────────────────────────────────────────────

export const channels = {
  available: () =>
    request<{ slug: string; name: string; priority: number }[]>('GET', '/channels/available'),

  templates: () =>
    request<{ language: string; key: string; preview: string }[]>('GET', '/channels/templates'),

  prefs: () => request<ChannelPrefsResponse>('GET', '/channels/prefs'),

  updatePrefs: (payload: ChannelPrefsUpdate) =>
    request<ChannelPrefsResponse>('PUT', '/channels/prefs', payload),

  send: (payload: ChannelSendRequest) =>
    request<ChannelSendResponse>('POST', '/channels/send', payload),
};

// ── Admin ─────────────────────────────────────────────────────

export const admin = {
  health: () => request<HealthResponse>('GET', '/admin/health'),

  healthAgent: (agent: string) =>
    request<HealthResponse>('GET', `/admin/health/${agent}`),

  unhealthy: () => request<HealthResponse>('GET', '/admin/health/unhealthy'),

  audit: (agentName?: string, count = 20) => {
    const params = new URLSearchParams();
    if (agentName) params.set('agent_name', agentName);
    params.set('count', String(count));
    return request<AuditListResponse>('GET', `/admin/audit?${params}`);
  },

  config: () => request<ConfigResponse>('GET', '/admin/config'),
};
