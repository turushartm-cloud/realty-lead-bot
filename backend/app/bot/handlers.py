"""Bot command handlers with button menus."""
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo, MenuButtonWebApp
)
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from ..config import settings
import structlog

logger = structlog.get_logger()
router = Router()


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 CRM", web_app=WebAppInfo(url=f"{settings.MINI_APP_URL}/index.html")),
                KeyboardButton(text="📊 Аналитика", web_app=WebAppInfo(url=f"{settings.MINI_APP_URL}/analytics.html")),
            ],
            [
                KeyboardButton(text="⚙️ Настройки", web_app=WebAppInfo(url=f"{settings.MINI_APP_URL}/settings.html")),
                KeyboardButton(text="❓ Помощь"),
            ]
        ],
        resize_keyboard=True,
        persistent=True
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    welcome_text = (
        f"👋 <b>Привет, {user.first_name}!</b>\n\n"
        f"🏠 <b>Realty Lead Bot</b> — ваш персональный помощник "
        f"по сбору лидов из Telegram-групп по недвижимости.\n\n"
        f"✨ <b>Возможности:</b>\n"
        f"• Мониторинг до 100 групп 24/7\n"
        f"• AI-фильтрация сообщений\n"
        f"• Мгновенные уведомления\n"
        f"• Экспорт в Excel/CRM\n"
        f"• Детальная аналитика\n\n"
        f"👇 Используйте меню ниже:"
    )
    await message.bot.set_chat_menu_button(
        chat_id=message.chat.id,
        menu_button=MenuButtonWebApp(text="🚀 CRM", web_app=WebAppInfo(url=settings.MINI_APP_URL))
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu())


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ <b>Добавьте бота в группы</b>\n"
        "   • Добавьте бота администратором\n"
        "   • Бот начнет мониторить автоматически\n\n"
        "2️⃣ <b>Просматривайте лиды</b>\n"
        "   • Нажмите '📋 CRM'\n"
        "   • Фильтруйте по статусу, дате, AI score\n\n"
        "3️⃣ <b>Работайте с лидами</b>\n"
        "   • Назначайте статусы\n"
        "   • Добавляйте заметки\n"
        "   • Экспортируйте в Excel\n\n"
        "4️⃣ <b>Аналитика</b>\n"
        "   • Статистика по группам\n"
        "   • Конверсия лидов\n"
        "   • AI-отчеты"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    from sqlalchemy import func, select
    from ..database import get_db_session
    from ..models import Lead
    async with get_db_session() as session:
        total = await session.scalar(select(func.count()).select_from(Lead))
        new_today = await session.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.created_at >= func.now() - func.text("INTERVAL '1 day'")
            )
        )
    stats_text = (
        f"📊 <b>Статистика:</b>\n\n"
        f"📈 Всего лидов: <code>{total}</code>\n"
        f"🆕 За 24 часа: <code>{new_today}</code>\n"
        f"🤖 AI фильтр: <code>{'ON' if settings.AI_FILTER_ENABLED else 'OFF'}</code>\n"
        f"📡 Групп: <code>{len(settings.MONITORED_GROUPS)}</code>\n"
        f"⚡ Статус: <code>🟢 Активен</code>"
    )
    await message.answer(stats_text, parse_mode=ParseMode.HTML)


@router.message(Command("export"))
async def cmd_export(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel (.xlsx)", callback_data="export:xlsx")],
        [InlineKeyboardButton(text="📄 CSV", callback_data="export:csv")],
        [InlineKeyboardButton(text="📋 JSON", callback_data="export:json")],
    ])
    await message.answer("📤 Выберите формат:", reply_markup=kb)
