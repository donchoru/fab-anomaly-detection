"""룰 평가 엔진 — SQL 실행 + 임계치 비교."""

from __future__ import annotations

import logging
import operator
from typing import Any

from db.oracle import execute

logger = logging.getLogger(__name__)

_OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}


async def evaluate_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """규칙을 평가하고 결과 반환.

    Returns:
        {
            "violated": bool,
            "severity": "warning" | "critical" | None,
            "measured_value": float | None,
            "rows": list[dict],
        }
    """
    check_type = rule.get("check_type", "threshold")

    if check_type == "threshold":
        return await _eval_threshold(rule)
    elif check_type == "delta":
        return await _eval_delta(rule)
    elif check_type == "absence":
        return await _eval_absence(rule)
    elif check_type == "llm":
        return await _eval_llm_delegate(rule)
    else:
        logger.warning("Unknown check_type: %s", check_type)
        return {"violated": False, "severity": None, "measured_value": None, "rows": []}


async def _eval_threshold(rule: dict[str, Any]) -> dict[str, Any]:
    """임계치 비교: 쿼리 결과의 첫 번째 값 vs 임계치."""
    rows = await _execute_rule_query(rule)
    if not rows:
        return {"violated": False, "severity": None, "measured_value": None, "rows": []}

    # 첫 번째 행의 첫 번째 숫자 컬럼 = 측정값
    measured = _extract_numeric(rows[0])
    if measured is None:
        return {"violated": False, "severity": None, "measured_value": None, "rows": rows}

    op_fn = _OPS.get(rule.get("threshold_op", ">"), operator.gt)
    critical_val = rule.get("critical_value")
    warning_val = rule.get("warning_value")

    severity = None
    if critical_val is not None and op_fn(measured, critical_val):
        severity = "critical"
    elif warning_val is not None and op_fn(measured, warning_val):
        severity = "warning"

    return {
        "violated": severity is not None,
        "severity": severity,
        "measured_value": measured,
        "rows": rows,
    }


async def _eval_delta(rule: dict[str, Any]) -> dict[str, Any]:
    """변화율 비교: 쿼리가 변화율(%)을 반환하는 것을 기대."""
    rows = await _execute_rule_query(rule)
    if not rows:
        return {"violated": False, "severity": None, "measured_value": None, "rows": []}

    measured = _extract_numeric(rows[0])
    if measured is None:
        return {"violated": False, "severity": None, "measured_value": None, "rows": rows}

    op_fn = _OPS.get(rule.get("threshold_op", ">"), operator.gt)
    critical_val = rule.get("critical_value")
    warning_val = rule.get("warning_value")

    severity = None
    if critical_val is not None and op_fn(abs(measured), critical_val):
        severity = "critical"
    elif warning_val is not None and op_fn(abs(measured), warning_val):
        severity = "warning"

    return {
        "violated": severity is not None,
        "severity": severity,
        "measured_value": measured,
        "rows": rows,
    }


async def _eval_absence(rule: dict[str, Any]) -> dict[str, Any]:
    """데이터 부재 검사: 쿼리 결과가 비어있으면 이상."""
    rows = await _execute_rule_query(rule)
    violated = len(rows) == 0

    return {
        "violated": violated,
        "severity": "warning" if violated else None,
        "measured_value": 0 if violated else len(rows),
        "rows": rows,
    }


async def _eval_llm_delegate(rule: dict[str, Any]) -> dict[str, Any]:
    """LLM에게 판단 위임: 쿼리 결과만 가져오고 violated=True로 표시.
    실제 판단은 detection_agent가 LLM 분석으로 수행."""
    rows = await _execute_rule_query(rule)
    measured = _extract_numeric(rows[0]) if rows else None

    return {
        "violated": True,  # LLM이 최종 판단
        "severity": "warning",
        "measured_value": measured,
        "rows": rows,
    }


async def _execute_rule_query(rule: dict[str, Any]) -> list[dict[str, Any]]:
    """규칙의 SQL 쿼리 실행."""
    sql = rule.get("query_template", "")
    if not sql:
        return []
    try:
        return await execute(sql)
    except Exception:
        logger.exception("Rule query failed: rule_id=%s", rule.get("rule_id"))
        return []


def _extract_numeric(row: dict[str, Any]) -> float | None:
    """딕셔너리에서 첫 번째 숫자 값 추출."""
    for v in row.values():
        if isinstance(v, (int, float)):
            return float(v)
    return None
