"""상관관계 엔진 — 시간·공간·인과 분석."""

from __future__ import annotations

import json
import logging
from typing import Any

from agent.agent_loop import run_agent_loop
from agent.prompts import CORRELATION_SYSTEM
from db import queries
from db.oracle import execute

logger = logging.getLogger(__name__)

# 공정 흐름 순서 (인과 분석용)
PROCESS_FLOW = ["TFT", "CELL", "MODULE"]


async def analyze_correlations() -> list[dict[str, Any]]:
    """최근 미상관 이상들에 대해 상관관계 분석.

    Returns: list of created correlation groups
    """
    # 아직 상관 그룹에 속하지 않은 활성 이상 조회
    uncorrelated = await execute(
        """SELECT * FROM sentinel_anomalies
           WHERE correlation_id IS NULL
             AND status IN ('detected', 'acknowledged', 'investigating')
             AND detected_at >= SYSTIMESTAMP - INTERVAL '1' HOUR
           ORDER BY detected_at"""
    )

    if len(uncorrelated) < 2:
        return []

    groups: list[dict[str, Any]] = []

    # 1. 시간적 상관 (10분 내 동시 발생)
    temporal = _find_temporal_groups(uncorrelated)
    for group in temporal:
        corr = await _create_correlation_group(group, "temporal")
        if corr:
            groups.append(corr)

    # 2. 공간적 상관 (같은 라인/존)
    remaining = [a for a in uncorrelated if not a.get("correlation_id")]
    spatial = _find_spatial_groups(remaining)
    for group in spatial:
        corr = await _create_correlation_group(group, "spatial")
        if corr:
            groups.append(corr)

    # 3. 인과적 상관 (공정 흐름)
    remaining = [a for a in uncorrelated if not a.get("correlation_id")]
    causal = _find_causal_groups(remaining)
    for group in causal:
        corr = await _create_correlation_group(group, "causal")
        if corr:
            groups.append(corr)

    return groups


def _find_temporal_groups(anomalies: list[dict]) -> list[list[dict]]:
    """10분 내 동시 발생 이상 그룹핑."""
    groups: list[list[dict]] = []
    used: set[int] = set()

    for i, a in enumerate(anomalies):
        if a["anomaly_id"] in used:
            continue
        group = [a]
        used.add(a["anomaly_id"])
        t = a["detected_at"]

        for b in anomalies[i + 1:]:
            if b["anomaly_id"] in used:
                continue
            diff = abs((b["detected_at"] - t).total_seconds())
            if diff <= 600:  # 10분
                group.append(b)
                used.add(b["anomaly_id"])

        if len(group) >= 2:
            groups.append(group)

    return groups


def _find_spatial_groups(anomalies: list[dict]) -> list[list[dict]]:
    """같은 affected_entity 접두사를 가진 이상 그룹핑."""
    by_prefix: dict[str, list[dict]] = {}
    for a in anomalies:
        entity = a.get("affected_entity", "")
        if not entity:
            continue
        # 라인 ID 추출 (예: LINE01-EQ001 → LINE01)
        prefix = entity.split("-")[0] if "-" in entity else entity
        by_prefix.setdefault(prefix, []).append(a)

    return [group for group in by_prefix.values() if len(group) >= 2]


def _find_causal_groups(anomalies: list[dict]) -> list[list[dict]]:
    """공정 흐름 기반 인과 상관."""
    by_category: dict[str, list[dict]] = {}
    for a in anomalies:
        cat = a.get("category", "")
        by_category.setdefault(cat, []).append(a)

    # 서로 다른 카테고리 이상이 있으면 인과 관계 후보
    if len(by_category) < 2:
        return []

    group = []
    for cat in by_category:
        group.extend(by_category[cat])

    return [group] if len(group) >= 2 else []


async def _create_correlation_group(
    anomalies: list[dict], corr_type: str
) -> dict[str, Any] | None:
    """상관 그룹 생성 + 이상들에 correlation_id 연결."""
    if len(anomalies) < 2:
        return None

    titles = [a.get("title", "") for a in anomalies]
    title = f"[{corr_type.upper()}] {', '.join(titles[:3])}"
    if len(titles) > 3:
        title += f" 외 {len(titles) - 3}건"

    corr_id = await queries.insert_correlation({
        "title": title[:500],
        "anomaly_count": len(anomalies),
        "correlation_type": corr_type,
    })

    for a in anomalies:
        await queries.set_anomaly_correlation(a["anomaly_id"], corr_id)

    logger.info(
        "Correlation group created: id=%d type=%s count=%d",
        corr_id, corr_type, len(anomalies),
    )

    return {
        "correlation_id": corr_id,
        "type": corr_type,
        "anomaly_count": len(anomalies),
        "title": title,
    }
