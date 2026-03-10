"""In-process pub/sub topic bus using asyncio."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Well-known topics
TOPIC_ANOMALY_DETECTED = "anomaly.detected"
TOPIC_RCA_COMPLETED = "rca.completed"
TOPIC_ALERT_REQUEST = "alert.request"


@dataclass
class Message:
    topic: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""


Subscriber = Callable[[Message], Coroutine[Any, Any, None]]


class TopicBus:
    """Simple in-process pub/sub bus.

    Detection agent publishes anomalies → RCA agent subscribes and analyzes.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._queue: asyncio.Queue[Message] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

    def subscribe(self, topic: str, handler: Subscriber) -> None:
        self._subscribers[topic].append(handler)
        logger.info("Subscribed to topic=%s handler=%s", topic, handler.__qualname__)

    def unsubscribe(self, topic: str, handler: Subscriber) -> None:
        if handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, payload: dict[str, Any], source: str = "") -> None:
        msg = Message(topic=topic, payload=payload, source=source)
        await self._queue.put(msg)
        logger.debug("Published topic=%s source=%s", topic, source)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop())
        logger.info("TopicBus started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("TopicBus stopped")

    async def _dispatch_loop(self) -> None:
        while self._running:
            try:
                msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            handlers = self._subscribers.get(msg.topic, [])
            for handler in handlers:
                try:
                    await handler(msg)
                except Exception:
                    logger.exception(
                        "Handler %s failed for topic=%s", handler.__qualname__, msg.topic
                    )


# Singleton
bus = TopicBus()
