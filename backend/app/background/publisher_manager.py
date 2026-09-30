"""Per-profile RabbitMQ publisher with reconnection.

One PublisherManager exists per Server_Profile. It owns a single aio-pika
connection used exclusively for publishing. Reconnection uses exponential
backoff (2s -> 60s cap). A publish waits up to 10 seconds for a live channel
before raising PublishError.

Requirements: 7.1, 8.1, 10.2, 12.2, 16.1, 16.3, 16.5, 16.6
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import aio_pika

from app.websocket import manager as ws_manager

logger = logging.getLogger("simulator.publisher")

EXCHANGE_NAME = "smartflow_event_bus"
INITIAL_BACKOFF = 2
MAX_BACKOFF = 60
PUBLISH_WAIT_SECONDS = 10


class PublishError(Exception):
    """Raised when an event cannot be published (no channel within timeout)."""


class PublisherManager:
    def __init__(self, profile):
        self.profile = profile
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()

    def _amqp_url(self) -> str:
        rmq = self.profile.rabbitmq
        return (
            f"amqp://{rmq.username}:{rmq.password}@{rmq.host}:{rmq.port}/"
            f"{rmq.vhost.lstrip('/')}"
        )

    async def run(self) -> None:
        """Background task loop: connect, hold, reconnect on failure."""
        backoff = INITIAL_BACKOFF
        while not self._stop.is_set():
            try:
                await self._connect()
                backoff = INITIAL_BACKOFF
                await ws_manager.broadcast_connection_status(
                    self.profile.name, "connected"
                )
                logger.info("Publisher connected for profile %s", self.profile.name)
                # Wait until connection closes or stop requested.
                await self._wait_until_closed()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self._ready.clear()
                logger.warning(
                    "Publisher connection failed for %s at %s: %s; retrying in %ss",
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

    async def _connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._amqp_url())
        self._channel = await self._connection.channel()
        # SmartFlow declares this exchange as durable=false; we must match it
        # exactly or RabbitMQ rejects the channel with PRECONDITION_FAILED.
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=False
        )
        self._ready.set()

    async def _wait_until_closed(self) -> None:
        assert self._connection is not None
        closed = asyncio.get_event_loop().create_future()

        def _on_close(sender, exc=None):
            if not closed.done():
                closed.set_result(True)

        self._connection.close_callbacks.add(_on_close)
        stop_task = asyncio.create_task(self._stop.wait())
        await asyncio.wait(
            {closed, stop_task}, return_when=asyncio.FIRST_COMPLETED
        )
        stop_task.cancel()
        self._ready.clear()

    async def publish(self, payload: dict, routing_key: str) -> None:
        """Publish a persistent JSON message. Waits up to 10s for a channel."""
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=PUBLISH_WAIT_SECONDS)
        except asyncio.TimeoutError:
            raise PublishError(
                f"RabbitMQ publisher for {self.profile.name} unavailable"
            )

        if self._exchange is None:
            raise PublishError("Publisher exchange not initialised")

        message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        try:
            await self._exchange.publish(message, routing_key=routing_key)
        except Exception as exc:  # noqa: BLE001
            raise PublishError(f"Publish failed: {exc}")

    async def stop(self) -> None:
        self._stop.set()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
