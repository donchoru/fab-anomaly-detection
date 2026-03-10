"use client";

import { useEffect, useState } from "react";
import {
  getDashboardOverview,
  getStats,
  getHealth,
  getBusMetrics,
  triggerDetection,
  type DashboardOverview,
  type SystemStats,
  type BusMetrics,
} from "@/lib/api";

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [health, setHealth] = useState<{ status: string; db: string } | null>(null);
  const [busMetrics, setBusMetrics] = useState<BusMetrics | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [o, s, h, b] = await Promise.all([
        getDashboardOverview(),
        getStats(),
        getHealth(),
        getBusMetrics(),
      ]);
      setOverview(o);
      setStats(s);
      setHealth(h);
      setBusMetrics(b);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "API 연결 실패");
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, []);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await triggerDetection();
      await load();
    } finally {
      setTriggering(false);
    }
  };

  const a = overview?.anomaly_summary;
  const bus = busMetrics?.totals;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">대시보드</h1>
        <div className="flex items-center gap-4">
          <span className={`text-xs px-2 py-1 rounded ${health?.status === "ok" ? "bg-emerald-900 text-emerald-300" : "bg-red-900 text-red-300"}`}>
            DB {health?.db ?? "..."}
          </span>
          <button
            onClick={handleTrigger}
            disabled={triggering}
            className="px-3 py-1.5 text-sm bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded transition"
          >
            {triggering ? "감지 중..." : "수동 감지 실행"}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-900/50 border border-red-700 rounded p-3 text-sm text-red-300">{error}</div>}

      {/* 이상 현황 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card label="활성 Critical" value={a?.active_critical ?? 0} color="red" />
        <Card label="활성 Warning" value={a?.active_warning ?? 0} color="amber" />
        <Card label="24h 총 이상" value={stats?.anomalies_24h ?? 0} color="gray" />
        <Card label="활성 규칙" value={stats?.active_rules ?? 0} color="emerald" />
      </div>

      {/* 상태별 분포 + 토픽 버스 요약 */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-400 mb-4">이상 상태 분포</h2>
          <div className="space-y-3">
            <StatusBar label="detected" count={a?.detected ?? 0} total={a?.total ?? 1} color="bg-red-500" />
            <StatusBar label="acknowledged" count={a?.acknowledged ?? 0} total={a?.total ?? 1} color="bg-amber-500" />
            <StatusBar label="investigating" count={a?.investigating ?? 0} total={a?.total ?? 1} color="bg-blue-500" />
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-400 mb-4">토픽 버스 현황</h2>
          <div className="grid grid-cols-2 gap-y-3 text-sm">
            <span className="text-gray-500">발행</span>
            <span className="text-right font-medium">{bus?.published ?? 0}</span>
            <span className="text-gray-500">처리 완료</span>
            <span className="text-right font-medium text-emerald-400">{bus?.delivered ?? 0}</span>
            <span className="text-gray-500">실패</span>
            <span className="text-right font-medium text-red-400">{bus?.failed ?? 0}</span>
            <span className="text-gray-500">대기 중</span>
            <span className="text-right font-medium text-amber-400">{bus?.pending ?? 0}</span>
            <span className="text-gray-500">큐 깊이</span>
            <span className="text-right font-medium">{busMetrics?.bus.queue_depth ?? 0}</span>
            <span className="text-gray-500">구독자 수</span>
            <span className="text-right font-medium">{busMetrics?.bus.subscriber_count ?? 0}</span>
          </div>
        </div>
      </div>

      {/* 마지막 사이클 */}
      {overview?.last_cycle && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-400 mb-3">마지막 감지 사이클</h2>
          <div className="flex gap-8 text-sm">
            <span>규칙 평가: <b>{overview.last_cycle.rules_evaluated}</b>개</span>
            <span>이상 발견: <b className="text-amber-400">{overview.last_cycle.anomalies_found}</b>건</span>
            <span>소요 시간: <b>{(overview.last_cycle.duration_ms / 1000).toFixed(1)}</b>초</span>
          </div>
        </div>
      )}
    </div>
  );
}

function Card({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    red: "border-red-800 text-red-400",
    amber: "border-amber-800 text-amber-400",
    gray: "border-gray-700 text-gray-300",
    emerald: "border-emerald-800 text-emerald-400",
  };
  return (
    <div className={`bg-gray-900 border rounded-lg p-4 ${colors[color]}`}>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

function StatusBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span>{count}</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
