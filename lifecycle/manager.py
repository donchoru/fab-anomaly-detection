"""이상 상태머신 — detected → acknowledged → investigating → resolved/false_positive."""

from __future__ import annotations

import logging
from db import queries

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    "detected": ["acknowledged", "false_positive"],
    "acknowledged": ["investigating", "resolved", "false_positive"],
    "investigating": ["resolved", "false_positive"],
    "resolved": [],
    "false_positive": [],
}


class InvalidTransitionError(Exception):
    pass


async def transition(
    anomaly_id: int,
    new_status: str,
    resolved_by: str | None = None,
) -> str:
    """이상 상태 전이.

    Raises InvalidTransitionError if transition is not allowed.
    """
    anomalies = await queries.get_anomalies(limit=1)
    # anomaly 조회
    from db.oracle import execute
    rows = await execute(
        "SELECT status FROM anomalies WHERE anomaly_id = :id",
        {"id": anomaly_id},
    )
    if not rows:
        raise ValueError(f"Anomaly {anomaly_id} not found")

    current = rows[0]["status"]
    allowed = VALID_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from '{current}' to '{new_status}'. Allowed: {allowed}"
        )

    await queries.update_anomaly_status(anomaly_id, new_status, resolved_by)
    logger.info("Anomaly %d: %s → %s", anomaly_id, current, new_status)
    return new_status
