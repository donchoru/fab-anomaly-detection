"use client";

import { useEffect, useState } from "react";
import { getBusMetrics, getBusMessages, type BusMetrics, type BusMessage } from "@/lib/api";

export default function BusPage() {
  const [metrics, setMetrics] = useState<BusMetrics | null>(null);
  const [messages, setMessages] = useState<BusMessage[]>([]);
  const [selected, setSelected] = useState<BusMessage | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const load = async () => {
    const [m, msgs] = await Promise.all([getBusMetrics(), getBusMessages(100)]);
    setMetrics(m);
    setMessages(msgs.messages);
  };

  useEffect(() => {
    load();
    if (!autoRefresh) return;
    const id = setInterval(load, 3_000);
    return () => clearInterval(id);
  }, [autoRefresh]);

  const topicColors: Record<string, string> = {
    "anomaly.detected": "bg-red-900/50 text-red-300 border-red-800",
    "rca.completed": "bg-blue-900/50 text-blue-300 border-blue-800",
    "alert.request": "bg-amber-900/50 text-amber-300 border-amber-800",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">토픽 버스 모니터링</h1>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="rounded"
          />
          자동 새로고침 (3초)
        </label>
      </div>

      {/* 토픽별 메트릭 카드 */}
      {metrics && (
        <div className="grid md:grid-cols-3 gap-4">
          {Object.entries(metrics.topics).map(([topic, t]) => (
            <div key={topic} className={`border rounded-lg p-4 ${topicColors[topic] ?? "bg-gray-900 border-gray-800"}`}>
              <div className="text-xs font-bold mb-3 tracking-wide">{topic}</div>
              <div className="grid grid-cols-3 gap-y-2 text-sm">
                <div>
                  <div className="text-xl font-bold">{t.published}</div>
                  <div className="text-xs opacity-60">발행</div>
                </div>
                <div>
                  <div className="text-xl font-bold">{t.delivered}</div>
                  <div className="text-xs opacity-60">처리</div>
                </div>
                <div>
                  <div className="text-xl font-bold">{t.failed}</div>
                  <div className="text-xs opacity-60">실패</div>
                </div>
              </div>
              {t.avg_processing_ms > 0 && (
                <div className="mt-3 text-xs opacity-60">
                  처리시간: 평균 {t.avg_processing_ms.toFixed(0)}ms
                  {t.min_processing_ms != null && ` / 최소 ${t.min_processing_ms.toFixed(0)}ms`}
                  {t.max_processing_ms != null && ` / 최대 ${t.max_processing_ms.toFixed(0)}ms`}
                </div>
              )}
              <div className="mt-2 text-xs opacity-50">
                구독자: {metrics.subscribers[topic]?.join(", ") ?? "없음"}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 메시지 흐름 + 상세 */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* 왼쪽: 메시지 목록 */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center">
            <h2 className="text-sm font-semibold text-gray-400">최근 메시지 ({messages.length}건)</h2>
          </div>
          <div className="max-h-[600px] overflow-y-auto divide-y divide-gray-800/50">
            {messages.map((msg, i) => {
              const payload = msg.payload as Record<string, unknown>;
              const severity = (payload.severity as string) ?? "";
              return (
                <button
                  key={i}
                  onClick={() => setSelected(msg)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-800/50 transition text-sm ${
                    selected === msg ? "bg-gray-800" : ""
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs px-1.5 py-0.5 rounded border ${topicColors[msg.topic] ?? "border-gray-700"}`}>
                      {msg.topic.split(".")[1]}
                    </span>
                    {severity && (
                      <span className={`text-xs ${severity === "critical" ? "text-red-400" : "text-amber-400"}`}>
                        {severity.toUpperCase()}
                      </span>
                    )}
                    <span className={`text-xs ml-auto ${msg.status === "failed" ? "text-red-400" : "text-emerald-400"}`}>
                      {msg.status === "failed" ? "FAIL" : `${msg.processing_ms.toFixed(0)}ms`}
                    </span>
                  </div>
                  <div className="text-gray-300 truncate">
                    {(payload.title as string) ?? (payload as Record<string, unknown>).root_cause as string ?? msg.source}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    {new Date(msg.timestamp).toLocaleTimeString("ko-KR")} &middot; {msg.source}
                  </div>
                </button>
              );
            })}
            {messages.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-600 text-sm">메시지 없음</div>
            )}
          </div>
        </div>

        {/* 오른쪽: 선택된 메시지 상세 */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-gray-400">메시지 상세</h2>
          </div>
          {selected ? (
            <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
              <MessageDetail msg={selected} />
            </div>
          ) : (
            <div className="p-8 text-center text-gray-600 text-sm">왼쪽에서 메시지를 선택하세요</div>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageDetail({ msg }: { msg: BusMessage }) {
  const payload = msg.payload as Record<string, unknown>;

  if (msg.topic === "anomaly.detected") {
    const detection = payload.detection as Record<string, unknown> | undefined;
    const threshold = detection?.threshold as Record<string, unknown> | undefined;
    const evidence = (payload.evidence_summary as string[]) ?? [];
    return (
      <>
        <Section title="이상 정보">
          <KV label="ID" value={payload.anomaly_id} />
          <KV label="제목" value={payload.title} />
          <KV label="심각도" value={payload.severity} severity />
          <KV label="카테고리" value={`${payload.category} / ${payload.subcategory ?? ""}`} />
          <KV label="영향 대상" value={payload.affected_entity} />
          <KV label="감지 시각" value={payload.detected_at} time />
        </Section>
        <Section title="감지 규칙">
          <KV label="규칙명" value={detection?.rule_name} />
          <KV label="검사 유형" value={detection?.check_type} />
          <KV label="측정값" value={detection?.measured_value} highlight />
          <KV label="임계치" value={`경고: ${threshold?.warning ?? "N/A"} / 위험: ${threshold?.critical ?? "N/A"} (${threshold?.operator ?? ">"})`} />
          <KV label="신뢰도" value={`${((detection?.confidence as number ?? 0) * 100).toFixed(0)}%`} />
        </Section>
        <Section title="감지 에이전트 분석">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">{payload.analysis as string}</p>
        </Section>
        {evidence.length > 0 && (
          <Section title="근거 데이터">
            {evidence.map((e, i) => (
              <div key={i} className="text-xs text-gray-400 font-mono py-0.5">{e}</div>
            ))}
          </Section>
        )}
      </>
    );
  }

  if (msg.topic === "rca.completed") {
    const anomaly = payload.anomaly as Record<string, unknown> | undefined;
    const rca = payload.rca as Record<string, unknown> | undefined;
    const evidence = (rca?.evidence as string[]) ?? [];
    const actions = (rca?.suggested_actions as string[]) ?? [];
    const related = (rca?.related_entities as string[]) ?? [];
    return (
      <>
        <Section title="원래 이상 정보">
          <KV label="ID" value={anomaly?.anomaly_id} />
          <KV label="제목" value={anomaly?.title} />
          <KV label="심각도" value={anomaly?.severity} severity />
          <KV label="카테고리" value={anomaly?.category} />
          <KV label="영향 대상" value={anomaly?.affected_entity} />
        </Section>
        <Section title="근본원인 분석 (RCA)">
          <div className="bg-gray-800 rounded p-3 mb-3">
            <div className="text-xs text-gray-500 mb-1">근본 원인</div>
            <div className="text-sm text-white font-medium">{rca?.root_cause as string}</div>
          </div>
          <KV label="신뢰도" value={`${((rca?.confidence as number ?? 0) * 100).toFixed(0)}%`} />
          <KV label="영향 범위" value={rca?.impact_scope} />
          {related.length > 0 && <KV label="관련 설비" value={related.join(", ")} />}
        </Section>
        {evidence.length > 0 && (
          <Section title="근거">
            {evidence.map((e, i) => (
              <div key={i} className="text-sm text-gray-300 py-0.5">- {e}</div>
            ))}
          </Section>
        )}
        {actions.length > 0 && (
          <Section title="권장 조치">
            {actions.map((a, i) => (
              <div key={i} className="text-sm text-emerald-300 py-0.5">{i + 1}. {a}</div>
            ))}
          </Section>
        )}
      </>
    );
  }

  if (msg.topic === "alert.request") {
    const detection = payload.detection as Record<string, unknown> | undefined;
    const evidence = (payload.evidence as string[]) ?? [];
    const actions = (payload.suggested_actions as string[]) ?? [];
    const related = (payload.related_entities as string[]) ?? [];
    return (
      <>
        <Section title="알림 대상 이상">
          <KV label="ID" value={payload.anomaly_id} />
          <KV label="제목" value={payload.title} />
          <KV label="심각도" value={payload.severity} severity />
          <KV label="카테고리" value={`${payload.category} / ${payload.subcategory ?? ""}`} />
          <KV label="영향 대상" value={payload.affected_entity} />
          <KV label="감지 시각" value={payload.detected_at} time />
        </Section>
        <Section title="감지 정보">
          <KV label="규칙명" value={detection?.rule_name} />
          <KV label="측정값" value={detection?.measured_value} highlight />
        </Section>
        <Section title="원인 분석">
          <div className="bg-gray-800 rounded p-3 mb-2">
            <div className="text-sm text-white">{payload.root_cause as string}</div>
          </div>
          <KV label="영향 범위" value={payload.impact_scope} />
          <KV label="분석 신뢰도" value={`${((payload.rca_confidence as number ?? 0) * 100).toFixed(0)}%`} />
          {related.length > 0 && <KV label="관련 설비" value={related.join(", ")} />}
        </Section>
        {evidence.length > 0 && (
          <Section title="근거">
            {evidence.map((e, i) => <div key={i} className="text-sm text-gray-300 py-0.5">- {e}</div>)}
          </Section>
        )}
        {actions.length > 0 && (
          <Section title="권장 조치">
            {actions.map((a, i) => <div key={i} className="text-sm text-emerald-300 py-0.5">{i + 1}. {a}</div>)}
          </Section>
        )}
      </>
    );
  }

  // 기타 토픽 — JSON 표시
  return (
    <pre className="text-xs text-gray-400 whitespace-pre-wrap overflow-auto">
      {JSON.stringify(payload, null, 2)}
    </pre>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{title}</h3>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function KV({
  label,
  value,
  severity,
  highlight,
  time,
}: {
  label: string;
  value: unknown;
  severity?: boolean;
  highlight?: boolean;
  time?: boolean;
}) {
  if (value == null || value === "") return null;
  let display = String(value);
  let cls = "text-gray-300";

  if (severity) {
    cls = display === "critical" ? "text-red-400 font-bold" : "text-amber-400 font-bold";
    display = display.toUpperCase();
  }
  if (highlight) cls = "text-white font-bold text-lg";
  if (time) display = new Date(display).toLocaleString("ko-KR");

  return (
    <div className="flex justify-between text-sm py-0.5">
      <span className="text-gray-500">{label}</span>
      <span className={cls}>{display}</span>
    </div>
  );
}
