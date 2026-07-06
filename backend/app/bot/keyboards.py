"""Inline keyboards for bot interactions."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from ..config import settings


def lead_card_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Взять", callback_data=f"lead:assign:{lead_id}"),
            InlineKeyboardButton(text="📞 Позвонить", callback_data=f"lead:call:{lead_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Заметка", callback_data=f"lead:note:{lead_id}"),
            InlineKeyboardButton(text="📤 Экспорт", callback_data=f"lead:export:{lead_id}"),
        ],
        [
            InlineKeyboardButton(
                text="📋 Открыть в CRM",
                web_app=WebAppInfo(url=f"{settings.MINI_APP_URL}/index.html?id={lead_id}")
            ),
        ]
    ])


def status_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    statuses = [
        ("🆕 Новый", "new"),
        ("📞 Связались", "contacted"),
        ("✅ Квалифицирован", "qualified"),
        ("💰 Конвертирован", "converted"),
        ("❌ Отклонен", "rejected"),
    ]
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"status:{lead_id}:{value}")]
        for label, value in statuses
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"page:{current_page - 1}"))
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"page:{current_page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])
