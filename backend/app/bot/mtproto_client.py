"""MTProto client for 24/7 group monitoring."""
import asyncio
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from ..config import settings
from ..database import get_db_session
from ..models import Lead, MonitoredGroup, LeadSource, LeadStatus
from .ai_filter import AIFilter
import structlog

logger = structlog.get_logger()

PHONE_PATTERN = re.compile(r'(?:\+7|8)[\s\-\(]?\d{3}[\s\-\)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}')
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
USERNAME_PATTERN = re.compile(r'@([a-zA-Z0-9_]{5,32})')


class MTProtoMonitor:
    def __init__(self):
        self.client = TelegramClient(
            StringSession(settings.TELETHON_SESSION),
            settings.API_ID,
            settings.API_HASH,
            connection_retries=5,
            retry_delay=5,
            auto_reconnect=True,
            flood_sleep_threshold=60
        )
        self.ai_filter = AIFilter()
        self._running = False
        self._message_buffer = []
        self._buffer_lock = asyncio.Lock()

    async def start(self):
        await self.client.start(phone=settings.PHONE_NUMBER)
        logger.info("MTProto client started", user=await self.client.get_me())
        self._register_handlers()
        self._running = True
        asyncio.create_task(self._flush_buffer_loop())

    def _register_handlers(self):
        @self.client.on(events.NewMessage(chats=settings.MONITORED_GROUPS))
        async def handle_new_message(event):
            try:
                await self._process_message(event)
            except FloodWaitError as e:
                logger.warning("FloodWait", seconds=e.seconds)
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error("Message processing error", error=str(e))

    async def _process_message(self, event):
        message = event.message
        chat = await event.get_chat()

        if message.sender and getattr(message.sender, 'bot', False):
            return

        text = message.text or message.raw_text or ""
        if not text or len(text) < 10:
            return

        if not self._keyword_match(text):
            return

        ai_result = await self.ai_filter.analyze(text)

        if ai_result["score"] < settings.AI_CONFIDENCE_THRESHOLD:
            logger.debug("Message filtered by AI", score=ai_result["score"])
            return

        contacts = self._extract_contacts(text)

        async with self._buffer_lock:
            self._message_buffer.append({
                "raw_text": text,
                "source_group_id": chat.id,
                "source_message_id": message.id,
                "source_chat_id": message.chat_id,
                "telegram_username": contacts.get("username"),
                "phone": contacts.get("phone"),
                "email": contacts.get("email"),
                "ai_score": ai_result["score"],
                "ai_category": ai_result["category"],
                "ai_summary": ai_result["summary"],
                "ai_keywords_matched": ai_result["keywords"],
                "extracted_name": contacts.get("name"),
                "status": LeadStatus.NEW,
                "priority": self._calculate_priority(ai_result)
            })

        logger.info(
            "Lead captured",
            group=chat.title,
            score=ai_result["score"],
            category=ai_result["category"]
        )

    def _keyword_match(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in settings.KEYWORDS)

    def _extract_contacts(self, text: str) -> dict:
        result = {}
        phones = PHONE_PATTERN.findall(text)
        if phones:
            result["phone"] = phones[0].replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        emails = EMAIL_PATTERN.findall(text)
        if emails:
            result["email"] = emails[0]

        usernames = USERNAME_PATTERN.findall(text)
        if usernames:
            result["username"] = usernames[0]

        lines = text.split('\n')
        for line in lines[:3]:
            if any(kw in line.lower() for kw in ["меня зовут", "я ", "имя", "контакт"]):
                result["name"] = line.strip()[:100]
                break

        return result

    def _calculate_priority(self, ai_result: dict) -> int:
        score = ai_result["score"]
        category = ai_result["category"]

        priority = 0
        if score > 0.9:
            priority += 2
        elif score > 0.8:
            priority += 1

        if category in ["buy_urgent", "sell_urgent", "rent_urgent"]:
            priority += 2

        return min(priority, 5)

    async def _flush_buffer_loop(self):
        while self._running:
            await asyncio.sleep(5)

            async with self._buffer_lock:
                if not self._message_buffer:
                    continue
                batch = self._message_buffer.copy()
                self._message_buffer.clear()

            async with get_db_session() as session:
                for data in batch:
                    lead = Lead(**data)
                    session.add(lead)

                for data in batch:
                    await self._send_notification(data)

    async def _send_notification(self, lead_data: dict):
        from aiogram import Bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

        bot = Bot(token=settings.BOT_TOKEN)

        try:
            async with get_db_session() as session:
                from sqlalchemy import select
                from ..models import User

                result = await session.execute(
                    select(User).where(User.is_admin == True, User.is_active == True)
                )
                admins = result.scalars().all()

                for admin in admins:
                    if admin.id:
                        text = (
                            f"🔔 <b>New Lead!</b>\n\n"
                            f"📊 AI Score: {lead_data['ai_score']:.2f}\n"
                            f"📂 Category: {lead_data['ai_category']}\n"
                            f"📝 Message: {lead_data['raw_text'][:200]}...\n"
                        )
                        if lead_data.get("phone"):
                            text += f"📞 Phone: {lead_data['phone']}\n"
                        if lead_data.get("email"):
                            text += f"📧 Email: {lead_data['email']}\n"

                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="📋 Open in CRM",
                                web_app=WebAppInfo(url=f"{settings.MINI_APP_URL}/index.html")
                            )],
                            [InlineKeyboardButton(
                                text="✅ Take Lead",
                                callback_data=f"assign_lead:new"
                            )]
                        ])

                        await bot.send_message(
                            admin.id,
                            text,
                            parse_mode="HTML",
                            reply_markup=kb
                        )
        except Exception as e:
            logger.error("Notification failed", error=str(e))
        finally:
            await bot.session.close()

    async def stop(self):
        self._running = False
        async with self._buffer_lock:
            if self._message_buffer:
                async with get_db_session() as session:
                    for data in self._message_buffer:
                        session.add(Lead(**data))
                self._message_buffer.clear()

        await self.client.disconnect()
        logger.info("MTProto client stopped")


monitor = MTProtoMonitor()
