"use client";

import { useEffect, useState } from "react";
import { getAnomalies, updateAnomalyStatus, type Anomaly } from "@/lib/api";

const STATUSES = ["all", "detected", "acknowledged", "investigating", "resolved", "false_positive"];
const NEXT_STATUS: Record<string, string[]> = {
  detected: ["acknowledged", "false_positive"],
  acknowledged: ["investigating", "resolved", "false_positive"],
  investigating: ["resolved", "false_positive"],
};

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState<Anomaly | null>(null);

  const load = async () => {
    const data = await getAnomalies(filter === "all" ? undefined : filter);
    setAnomalies(data);
  };

  useEffect(() => {
    load();
  }, [filter]);

  const handleStatus = async (id: number, status: string) => {
    await updateAnomalyStatus(id, status);
    await load();
    if (selected?.anomaly_id === id) {
      setSelected((prev) => prev ? { ...prev, status } : null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">이상 목록</h1>
        <button onClick={load} className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded transition">
          새로고침
        </button>
      </div>

      {/* 필터 */}
      <div className="flex gap-1">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 text-xs rounded transition ${
              filter === s ? "bg-emerald-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {s === "all" ? "전체" : s}
          </button>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* 목록 */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="max-h-[600px] overflow-y-auto divide-y divide-gray-800/50">
            {anomalies.map((a) => (
              <button
                key={a.anomaly_id}
                onClick={() => setSelected(a)}
                className={`w-full text-left px-4 py-3 hover:bg-gray-800/50 transition ${
                  selected?.anomaly_id === a.anomaly_id ? "bg-gray-800" : ""
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-bold ${a.severity === "critical" ? "text-red-400" : "text-amber-400"}`}>
                    {a.severity.toUpperCase()}
                  </span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{a.status}</span>
                  <span className="text-xs text-gray-600 ml-auto">#{a.anomaly_id}</span>
                </div>
                <div className="text-sm text-gray-200 truncate">{a.title}</div>
                <div className="text-xs text-gray-600 mt-1">
                  {a.category} &middot; {new Date(a.detected_at).toLocaleString("ko-KR")}
                </div>
              </button>
            ))}
            {anomalies.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-600 text-sm">이상 없음</div>
            )}
          </div>
        </div>

        {/* 상세 */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          {selected ? (
            <div className="p-5 space-y-4 max-h-[600px] overflow-y-auto">
              <div className="flex items-center gap-2">
                <span className={`text-sm font-bold ${selected.severity === "critical" ? "text-red-400" : "text-amber-400"}`}>
                  {selected.severity.toUpperCase()}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">{selected.status}</span>
                <span className="text-xs text-gray-600 ml-auto">#{selected.anomaly_id}</span>
              </div>

              <h2 className="text-lg font-bold">{selected.title}</h2>

              <div className="grid grid-cols-2 gap-y-2 text-sm">
                <span className="text-gray-500">카테고리</span>
                <span>{selected.category}</span>
                <span className="text-gray-500">측정값</span>
                <span className="font-bold text-white">{selected.measured_value}</span>
                <span className="text-gray-500">임계치</span>
                <span>{selected.threshold_value}</span>
                <span className="text-gray-500">영향 대상</span>
                <span>{selected.affected_entity || "-"}</span>
                <span className="text-gray-500">감지 시각</span>
                <span>{new Date(selected.detected_at).toLocaleString("ko-KR")}</span>
              </div>

              {selected.description && (
                <div>
                  <h3 className="text-xs font-bold text-gray-500 mb-1">설명</h3>
                  <p className="text-sm text-gray-300 whitespace-pre-wrap">{selected.description}</p>
                </div>
              )}

              {selected.llm_analysis && (
                <div>
                  <h3 className="text-xs font-bold text-gray-500 mb-1">원인 분석 (RCA)</h3>
                  <div className="bg-gray-800 rounded p-3 text-sm text-gray-200 whitespace-pre-wrap">
                    {selected.llm_analysis}
                  </div>
                </div>
              )}

              {selected.llm_suggestion && (
                <div>
                  <h3 className="text-xs font-bold text-gray-500 mb-1">권장 조치</h3>
                  <div className="text-sm text-emerald-300 whitespace-pre-wrap">{selected.llm_suggestion}</div>
                </div>
              )}

              {/* 상태 전이 버튼 */}
              {NEXT_STATUS[selected.status] && (
                <div className="flex gap-2 pt-2 border-t border-gray-800">
                  {NEXT_STATUS[selected.status].map((next) => (
                    <button
                      key={next}
                      onClick={() => handleStatus(selected.anomaly_id, next)}
                      className={`px-3 py-1.5 text-xs rounded transition ${
                        next === "false_positive"
                          ? "bg-gray-700 hover:bg-gray-600 text-gray-300"
                          : "bg-emerald-700 hover:bg-emerald-600 text-white"
                      }`}
                    >
                      → {next}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-600 text-sm">왼쪽에서 이상을 선택하세요</div>
          )}
        </div>
      </div>
    </div>
  );
}
