// AG-UI Protocol — Agent-Generated UI Type System
// Based on the AG-UI protocol for dynamic agent-to-frontend communication

/** AG-UI Event types */
export type AGUIEventType = "render" | "update" | "action" | "stream" | "approval_request" | "status";

/** Base AG-UI event */
export interface AGUIEvent {
  type: AGUIEventType;
  agentId: string;
  sessionId: string;
  timestamp: number;
  traceId?: string;
  tenantId?: string;
}

/** Component types that agents can render */
export type AGUIComponentType =
  | "form"
  | "dashboard"
  | "chart"
  | "table"
  | "approval-card"
  | "code-block"
  | "status-indicator"
  | "data-grid"
  | "metric-card";

/** AG-UI Component spec — sent from agent to frontend */
export interface AGUIComponent {
  id: string;
  type: AGUIComponentType;
  props: Record<string, unknown>;
  /** Niche DNA defines visual theme */
  nicheStyle?: string;
  /** Whether this component requires human approval */
  hitlRequired?: boolean;
  /** Component title/label */
  title?: string;
  /** Optional description */
  description?: string;
  /** Ordering priority (lower = rendered first) */
  priority?: number;
}

/** Render event — agent requests UI rendering */
export interface AGUIRenderEvent extends AGUIEvent {
  type: "render";
  components: AGUIComponent[];
}

/** Update event — agent updates existing component */
export interface AGUIUpdateEvent extends AGUIEvent {
  type: "update";
  componentId: string;
  updatedProps: Record<string, unknown>;
}

/** Action event — user interaction feedback */
export interface AGUIActionEvent extends AGUIEvent {
  type: "action";
  componentId: string;
  action: string;
  payload: Record<string, unknown>;
}

/** Approval request event */
export interface AGUIApprovalEvent extends AGUIEvent {
  type: "approval_request";
  policyViolation?: string;
  riskLevel: "low" | "medium" | "high" | "critical";
  suggestedAction: string;
  deadline?: string;
  onApprove: string;
  onReject: string;
}

/** Stream event — streaming text/data from agent */
export interface AGUIStreamEvent extends AGUIEvent {
  type: "stream";
  content: string;
  isFinal: boolean;
  componentId?: string;
}

/** Status event — agent status change */
export interface AGUIStatusEvent extends AGUIEvent {
  type: "status";
  status: "thinking" | "executing" | "waiting_approval" | "completed" | "error";
  message?: string;
  progress?: number;
}

/** Union of all AG-UI events */
export type AGUIAnyEvent =
  | AGUIRenderEvent
  | AGUIUpdateEvent
  | AGUIActionEvent
  | AGUIApprovalEvent
  | AGUIStreamEvent
  | AGUIStatusEvent;

/** Form field definition */
export interface AGUIFormField {
  name: string;
  label: string;
  type: "text" | "email" | "number" | "select" | "textarea" | "checkbox" | "date" | "password";
  required?: boolean;
  placeholder?: string;
  defaultValue?: unknown;
  options?: Array<{ label: string; value: string }>;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    message?: string;
  };
}

/** Chart data for agent chart component */
export interface AGUIChartData {
  type: "line" | "bar" | "pie" | "area";
  title?: string;
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    color?: string;
  }>;
}

/** Table column definition */
export interface AGUITableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
}

/** Metric card */
export interface AGUIMetricCard {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: string;
  color?: string;
}

/** Session state for AG-UI */
export interface AGUISession {
  sessionId: string;
  agentId: string;
  createdAt: number;
  lastEventAt: number;
  components: Map<string, AGUIComponent>;
  status: "active" | "completed" | "error";
}
