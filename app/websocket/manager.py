import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.user_roles: Dict[int, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, role: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections[user_id].add(websocket)
            self.user_roles[user_id] = role
        logger.info(f"User {user_id} connected. Total users online: {len(self.active_connections)}")

    async def disconnect(self, user_id: int, websocket: WebSocket):
        async with self._lock:
            conns = self.active_connections.get(user_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    self.active_connections.pop(user_id, None)
                    self.user_roles.pop(user_id, None)
        logger.info(f"User {user_id} disconnected")

    async def send_personal(self, user_id: int, message: dict):
        conns = list(self.active_connections.get(user_id, set()))
        payload = json.dumps(message, ensure_ascii=False, default=str)
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                logger.debug(f"Failed to send to user {user_id}")

    async def broadcast_to_role(self, role: str, message: dict):
        targets = [uid for uid, r in self.user_roles.items() if r == role or r == "super_admin"]
        for uid in targets:
            await self.send_personal(uid, message)

    async def broadcast_to_conversation(
        self, member_ids: list[int], message: dict, exclude: Optional[set[int]] = None
    ):
        exclude = exclude or set()
        for uid in member_ids:
            if uid not in exclude:
                await self.send_personal(uid, message)

    def is_online(self, user_id: int) -> bool:
        return bool(self.active_connections.get(user_id))

    def online_user_ids(self) -> list[int]:
        return list(self.active_connections.keys())


manager = ConnectionManager()