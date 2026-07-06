"""Middleware: rate limiting, logging, error handling."""
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 60, window: int = 60):
        self.limit = limit
        self.window = window
        self._requests: Dict[int, list] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = datetime.now()
        if user_id not in self._requests:
            self._requests[user_id] = []
        self._requests[user_id] = [
            t for t in self._requests[user_id]
            if now - t < timedelta(seconds=self.window)
        ]
        if len(self._requests[user_id]) >= self.limit:
            await event.answer("⏳ Слишком много запросов. Попробуйте позже.")
            return None
        self._requests[user_id].append(now)
        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        logger.info(
            "Bot event",
            user_id=user.id,
            username=user.username,
            chat_id=event.chat.id,
            text=event.text[:100] if event.text else None,
            timestamp=datetime.now().isoformat()
        )
        return await handler(event, data)
