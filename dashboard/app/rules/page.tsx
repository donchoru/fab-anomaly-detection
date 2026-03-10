"use client";

import { useEffect, useState } from "react";
import { getRules, testRule, type Rule, type RuleTestResult } from "@/lib/api";

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [selected, setSelected] = useState<Rule | null>(null);
  const [testResult, setTestResult] = useState<RuleTestResult | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    getRules().then(setRules);
  }, []);

  const handleTest = async (ruleId: number) => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testRule(ruleId);
      setTestResult(result);
    } catch (e: unknown) {
      setTestResult({ rule_id: ruleId, rule_name: "", row_count: 0, rows: [{ error: e instanceof Error ? e.message : "오류" }] });
    } finally {
      setTesting(false);
    }
  };

  const categoryColors: Record<string, string> = {
    logistics: "bg-blue-900/50 text-blue-300 border-blue-800",
    wip: "bg-purple-900/50 text-purple-300 border-purple-800",
    equipment: "bg-orange-900/50 text-orange-300 border-orange-800",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">규칙 관리</h1>
        <span className="text-sm text-gray-500">{rules.length}개 규칙</span>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* 목록 */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="max-h-[600px] overflow-y-auto divide-y divide-gray-800/50">
            {rules.map((r) => (
              <button
                key={r.rule_id}
                onClick={() => { setSelected(r); setTestResult(null); }}
                className={`w-full text-left px-4 py-3 hover:bg-gray-800/50 transition ${
                  selected?.rule_id === r.rule_id ? "bg-gray-800" : ""
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${categoryColors[r.category] ?? "border-gray-700"}`}>
                    {r.category}
                  </span>
                  <span className="text-xs text-gray-600">{r.check_type}</span>
                  {r.llm_enabled === 1 && (
                    <span className="text-xs px-1 py-0.5 rounded bg-emerald-900/50 text-emerald-400">AI</span>
                  )}
                  <span className="text-xs text-gray-600 ml-auto">#{r.rule_id}</span>
                </div>
                <div className="text-sm text-gray-200">{r.rule_name}</div>
                <div className="text-xs text-gray-600 mt-1">
                  {r.subcategory ?? ""} &middot; {r.eval_interval}초 간격
                  {r.warning_value != null && ` · 경고>${r.warning_value}`}
                  {r.critical_value != null && ` · 위험>${r.critical_value}`}
                </div>
              </button>
            ))}
            {rules.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-600 text-sm">규칙 없음</div>
            )}
          </div>
        </div>

        {/* 상세 + 테스트 */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          {selected ? (
            <div className="p-5 space-y-4 max-h-[600px] overflow-y-auto">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-1.5 py-0.5 rounded border ${categoryColors[selected.category] ?? "border-gray-700"}`}>
                  {selected.category}
                </span>
                <span className="text-xs text-gray-500">#{selected.rule_id}</span>
              </div>

              <h2 className="text-lg font-bold">{selected.rule_name}</h2>

              <div className="grid grid-cols-2 gap-y-2 text-sm">
                <span className="text-gray-500">검사 유형</span>
                <span>{selected.check_type}</span>
                <span className="text-gray-500">연산자</span>
                <span>{selected.threshold_op}</span>
                <span className="text-gray-500">경고 임계치</span>
                <span className="text-amber-400">{selected.warning_value ?? "-"}</span>
                <span className="text-gray-500">위험 임계치</span>
                <span className="text-red-400">{selected.critical_value ?? "-"}</span>
                <span className="text-gray-500">평가 간격</span>
                <span>{selected.eval_interval}초</span>
                <span className="text-gray-500">LLM 분석</span>
                <span>{selected.llm_enabled ? "활성" : "비활성"}</span>
              </div>

              <button
                onClick={() => handleTest(selected.rule_id)}
                disabled={testing}
                className="w-full py-2 text-sm bg-blue-700 hover:bg-blue-600 disabled:opacity-50 rounded transition"
              >
                {testing ? "실행 중..." : "SQL 테스트 실행"}
              </button>

              {testResult && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">결과: {testResult.row_count}행</div>
                  <div className="bg-gray-950 rounded p-3 max-h-64 overflow-auto">
                    <pre className="text-xs text-gray-400 whitespace-pre-wrap">
                      {JSON.stringify(testResult.rows, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-600 text-sm">왼쪽에서 규칙을 선택하세요</div>
          )}
        </div>
      </div>
    </div>
  );
}
