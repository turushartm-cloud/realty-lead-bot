"""
Разовая генерация Telethon StringSession для MTProto-мониторинга групп.

Запускать ТОЛЬКО локально на своём компьютере (не на Render!) — телефон
запросит SMS-код, который нужно ввести интерактивно.

Использование:
    pip install telethon
    python scripts/generate_session.py

На вопросы ответь своим API_ID, API_HASH (с https://my.telegram.org/apps)
и номером телефона. В конце скрипт напечатает строку — её нужно вставить
в ENV переменную TELETHON_SESSION сервиса realty-api и realty-worker на Render.

⚠️ Эта строка даёт полный доступ к твоему Telegram-аккаунту — храни её
только как секрет в Render, никогда не коммить в git.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("API_ID: ").strip())
api_hash = input("API_HASH: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("Готово! Скопируй строку ниже в ENV TELETHON_SESSION на Render:")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
