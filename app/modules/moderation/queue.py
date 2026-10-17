"""صف ساده پردازش نظارت هوشمند (in-process)"""
import asyncio
import logging
from typing import Optional
from app.database.session import AsyncSessionLocal
from app.modules.moderation.service import ModerationService
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


class ModerationQueue:
    def __init__(self, maxsize: int = 100):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue(self, message_id: int, user_id: int, content: str):
        try:
            self._queue.put_nowait((message_id, user_id, content))
        except asyncio.QueueFull:
            logger.warning("Moderation queue full, dropping message")

    async def _worker(self):
        while True:
            try:
                message_id, user_id, content = await self._queue.get()
            except asyncio.CancelledError:
                break

            try:
                async with AsyncSessionLocal() as db:
                    service = ModerationService(db)
                    report = await service.analyze_message(message_id, user_id, content)
                    if report and report.result != "allowed":
                        await manager.broadcast_to_role(
                            "moderator",
                            {
                                "type": "moderation_report",
                                "report_id": report.id,
                                "message_id": message_id,
                                "result": report.result,
                                "severity": report.severity,
                                "category": report.category,
                            },
                        )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Moderation worker error")
            finally:
                self._queue.task_done()


moderation_queue = ModerationQueue()