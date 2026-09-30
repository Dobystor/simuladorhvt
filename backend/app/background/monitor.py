"""Per-profile RabbitMQ Monitor consumer with reconnection.

Runs permanently regardless of active sessions. Declares a durable, profile-
scoped queue bound to smartflow_event_bus with routing key
HaulageVehicleIntegrationEvent. For each message it persists an event_feed row
and only acks after a successful insert; on failure it nacks (requeue=True).
Reconnection uses exponential backoff (2s -> 60s cap).

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 16.1, 16.2, 16.3, 16.4
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import aio_pika

from app import database
from app.websocket import manager as ws_manager

logger = logging.getLogger("simulator.monitor")

EXCHANGE_NAME = "smartflow_event_bus"
ROUTING_KEY = "HaulageVehicleIntegrationEvent"
INITIAL_BACKOFF = 2
MAX_BACKOFF = 60


class Monitor:
    def __init__(self, profile):
        self.profile = profile
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._stop = asyncio.Event()

    def _amqp_url(self) -> str:
        rmq = self.profile.rabbitmq
        return (
            f"amqp://{rmq.username}:{rmq.password}@{rmq.host}:{rmq.port}/"
            f"{rmq.vhost.lstrip('/')}"
        )

    @property
    def queue_name(self) -> str:
        return f"smartflow_simulator_{self.profile.sanitized_name}"

    async def run(self) -> None:
        backoff = INITIAL_BACKOFF
        while not self._stop.is_set():
            try:
                await self._consume()
                backoff = INITIAL_BACKOFF
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Monitor connection failed for %s at %s: %s; retry in %ss",
                    self.profile.name,
                    datetime.now(timezone.utc).isoformat(),
                    exc,
                    backoff,
                )
                await ws_manager.broadcast_connection_status(
                    self.profile.name, "reconnecting", retry_in_seconds=backoff
                )
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                except asyncio.TimeoutError:
                    pass
                backoff = min(backoff * 2, MAX_BACKOFF)

    async def _consume(self) -> None:
        self._connection = await aio_pika.connect_robust(self._amqp_url())
        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=10)
        # Must match SmartFlow's existing exchange declaration (durable=false).
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=False
        )
        queue = await channel.declare_queue(self.queue_name, durable=True)
        await queue.bind(exchange, routing_key=ROUTING_KEY)

        logger.info(
            "Monitor connected for %s (queue %s)", self.profile.name, self.queue_name
        )
        await ws_manager.broadcast_connection_status(self.profile.name, "connected")

        async with queue.iterator() as it:
            async for message in it:
                if self._stop.is_set():
                    break
                await self._handle_message(message)

    async def _handle_message(self, message: aio_pika.abc.AbstractIncomingMessage):
        raw = message.body.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}

        received_at = datetime.now(timezone.utc).isoformat()
        event_guid = payload.get("Id")
        is_simulated = 0
        if event_guid:
            try:
                is_simulated = int(
                    await database.find_recent_event_log_by_id(
                        self.profile.name, str(event_guid)
                    )
                )
            except Exception:  # noqa: BLE001 — treat as external if lookup fails
                is_simulated = 0

        record = {
            "received_at": received_at,
            "server_profile": self.profile.name,
            "event_id_field": _as_str(payload.get("EventId")),
            "mac_vehicle": payload.get("MACVehicle"),
            "mac_beacon": payload.get("MACBeacon"),
            "mac_operator": payload.get("MACOperator"),
            "status": _as_int(payload.get("Status")),
            "date_status": _as_str(payload.get("DateStatus")),
            "real_time": _as_bool_int(payload.get("RealTime")),
            "is_simulated": is_simulated,
            "raw_payload": raw,
        }

        try:
            row_id = await database.insert_event_feed(record)
        except Exception as exc:  # noqa: BLE001
            logger.error("event_feed insert failed for %s: %s", self.profile.name, exc)
            await message.nack(requeue=True)
            return

        await message.ack()
        await ws_manager.broadcast(
            self.profile.name,
            {"type": "event_feed", "data": {"id": row_id, **record}},
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()


def _as_str(value) -> str | None:
    return None if value is None else str(value)


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool_int(value) -> int | None:
    if value is None:
        return None
    return 1 if value else 0
