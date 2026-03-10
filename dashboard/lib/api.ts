const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8600";

async function fetcher<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── 대시보드 ──
export const getDashboardOverview = () => fetcher<DashboardOverview>("/api/dashboard/overview");
export const getTimeline = (hours = 24) => fetcher<{ timeline: TimelineEntry[] }>(`/api/dashboard/timeline?hours=${hours}`);
export const getHeatmap = () => fetcher<{ heatmap: HeatmapEntry[] }>("/api/dashboard/heatmap");

// ── 토픽 버스 ──
export const getBusMetrics = () => fetcher<BusMetrics>("/api/bus/metrics");
export const getBusMessages = (limit = 50) => fetcher<{ messages: BusMessage[] }>(`/api/bus/messages?limit=${limit}`);

// ── 이상 ──
export const getAnomalies = (status?: string) =>
  fetcher<Anomaly[]>(`/api/anomalies${status ? `?status=${status}` : ""}`);
export const getActiveAnomalies = () => fetcher<Anomaly[]>("/api/anomalies/active");
export const updateAnomalyStatus = (id: number, status: string, resolvedBy?: string) =>
  fetcher<{ anomaly_id: number; status: string }>(`/api/anomalies/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, resolved_by: resolvedBy }),
  });

// ── 규칙 ──
export const getRules = () => fetcher<Rule[]>("/api/rules");
export const testRule = (id: number) => fetcher<RuleTestResult>(`/api/rules/${id}/test`, { method: "POST" });

// ── 시스템 ──
export const getHealth = () => fetcher<{ status: string; db: string }>("/health");
export const getStats = () => fetcher<SystemStats>("/api/stats");
export const triggerDetection = () => fetcher<DetectionResult>("/api/detect/trigger", { method: "POST" });

// ── Types ──
export interface DashboardOverview {
  anomaly_summary: {
    total: number;
    detected: number;
    acknowledged: number;
    investigating: number;
    active_critical: number;
    active_warning: number;
  };
  last_cycle: { cycle_id: number; rules_evaluated: number; anomalies_found: number; duration_ms: number } | null;
}

export interface BusMetrics {
  bus: { running: boolean; started_at: string | null; queue_depth: number; subscriber_count: number };
  totals: { published: number; delivered: number; failed: number; pending: number };
  topics: Record<string, TopicStats>;
  subscribers: Record<string, string[]>;
}

export interface TopicStats {
  published: number;
  delivered: number;
  failed: number;
  pending: number;
  last_published_at: string | null;
  last_delivered_at: string | null;
  avg_processing_ms: number;
  min_processing_ms: number | null;
  max_processing_ms: number | null;
}

export interface BusMessage {
  topic: string;
  source: string;
  timestamp: string;
  status: "delivered" | "failed";
  processing_ms: number;
  payload: Record<string, unknown>;
}

export interface Anomaly {
  anomaly_id: number;
  rule_id: number;
  correlation_id: number | null;
  category: string;
  severity: string;
  title: string;
  description: string;
  measured_value: number;
  threshold_value: number;
  affected_entity: string;
  llm_analysis: string | null;
  llm_suggestion: string | null;
  status: string;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  notes: string | null;
}

export interface Rule {
  rule_id: number;
  rule_name: string;
  category: string;
  subcategory: string | null;
  check_type: string;
  threshold_op: string;
  warning_value: number | null;
  critical_value: number | null;
  eval_interval: number;
  llm_enabled: number;
  enabled: number;
}

export interface RuleTestResult {
  rule_id: number;
  rule_name: string;
  row_count: number;
  rows: Record<string, unknown>[];
}

export interface TimelineEntry { hour_slot: string; category: string; severity: string; count: number }
export interface HeatmapEntry { category: string; severity: string; count: number }
export interface SystemStats { active_rules: number; anomalies_24h: number; cycles_24h: { cnt: number; avg_ms: number } }
export interface DetectionResult { cycle_id: number; rules_evaluated: number; anomalies_found: number; duration_ms: number }
