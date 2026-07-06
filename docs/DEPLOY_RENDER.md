# 🚀 Деплой на Render.com (GitHub + Render + Redis + Telegram)

## Архитектура на Render

```
┌─────────────────────────────────────────────────────────────┐
│                        RENDER.COM                            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  realty-api │  │ realty-worker │  │  realty-beat     │ │
│  │  (Web svc)  │  │   (Worker)    │  │  (Scheduler)     │ │
│  │  FastAPI    │  │   Celery      │  │  Celery Beat     │ │
│  └──────┬──────┘  └──────┬───────┘  └──────────────────┘ │
│         │                │                                  │
│  ┌──────┴────────────────┴──────┐  ┌──────────────────────┐ │
│  │    realty-postgres          │  │   realty-redis      │ │
│  │    (Managed PostgreSQL)     │  │   (Redis Key-Value) │ │
│  └─────────────────────────────┘  └──────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         realty-mini-app (Static Site)               │  │
│  │         Telegram WebApp CRM                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Пошаговая инструкция

### 1. Создание репозитория на GitHub

```bash
# Инициализировать Git
cd realty-lead-bot
git init
git add .
git commit -m "Initial commit: Realty Lead Bot v1.0"

# Создать репозиторий на GitHub (через web или gh CLI)
gh repo create realty-lead-bot --public --source=. --push
# Или:
git remote add origin https://github.com/YOUR_USERNAME/realty-lead-bot.git
git branch -M main
git push -u origin main
```

### 2. Настройка Render Blueprint

1. Зайдите на [render.com](https://render.com) и создайте аккаунт
2. Dashboard → **New** → **Blueprint**
3. Подключите GitHub репозиторий
4. Render автоматически прочитает `render.yaml`

### 3. Настройка Environment Variables

В Render Dashboard для каждого сервиса добавьте **Secret** переменные:

| Переменная | Где получить | Сервисы |
|------------|-------------|---------|
| `BOT_TOKEN` | @BotFather → /newbot | api, worker |
| `API_ID` | https://my.telegram.org/apps | api, worker |
| `API_HASH` | Там же | api, worker |
| `PHONE_NUMBER` | Ваш номер (+7...) | api, worker |
| `OPENAI_API_KEY` | https://platform.openai.com | api, worker |
| `SENTRY_DSN` | https://sentry.io (опционально) | api |

**Важно:** `SECRET_KEY` генерируется автоматически через `generateValue: true`

### 4. Настройка Telegram Bot

#### 4.1 Создание бота
```
@BotFather → /newbot → введите имя → получите BOT_TOKEN
```

#### 4.2 Настройка Mini App
```
@BotFather → /mybots → Выберите бота → Bot Settings → Menu Button
- Menu Button Title: 🚀 CRM
- Menu Button URL: https://realty-mini-app.onrender.com/index.html
```

#### 4.3 Настройка Webhook (опционально)
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook"   -d "url=https://realty-api.onrender.com/webhook"
```

### 5. Настройка MTProto (Telethon)

**Проблема:** Render не поддерживает интерактивный ввод (phone code).

**Решение:** Создайте сессию локально и закоммитьте в репозиторий:

```bash
# Локально (на вашем компьютере)
cd backend
python -c "
from telethon import TelegramClient
client = TelegramClient('sessions/monitor_session', API_ID, API_HASH)
client.start(phone='+79001234567')
print('Session created!')
client.disconnect()
"

# Создастся файл sessions/monitor_session.session
# Добавьте в .gitignore (или закоммитьте для Render)
```

**Альтернатива:** Используйте String Session:
```python
from telethon.sessions import StringSession
from telethon import TelegramClient

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())  # Скопируйте эту строку
```

Затем в `mtproto_client.py` замените:
```python
self.client = TelegramClient(
    StringSession(SESSION_STRING),  # вместо файла
    settings.API_ID,
    settings.API_HASH
)
```

### 6. Добавление групп для мониторинга

1. Добавьте бота администратором в группы
2. Узнайте ID групп через @userinfobot
3. В Render Dashboard → realty-api → Environment:
   ```
   MONITORED_GROUPS=-1001234567890,-1009876543210
   ```
4. Перезапустите сервис

### 7. Проверка работоспособности

```bash
# Health check
curl https://realty-api.onrender.com/health

# Должно вернуть:
# {"status": "healthy", "version": "1.0.0", "environment": "production"}
```

### 8. CI/CD (GitHub Actions)

При каждом push в `main`:
1. Запускаются тесты (`pytest`)
2. При успехе — автодеплой на Render

Настройка secrets в GitHub:
- `RENDER_SERVICE_ID` — ID из Render Dashboard
- `RENDER_API_KEY` — API ключ из Render (Account Settings)

## 💰 Стоимость на Render (Free Tier)

| Сервис | Free Tier | Limitations |
|--------|-----------|-------------|
| Web Service | ✅ | Sleeps after 15 min idle, 512MB RAM |
| Worker | ✅ | 512MB RAM |
| PostgreSQL | ✅ | 1GB storage, 30-day expiry |
| Redis | ✅ | 25MB, 30-day expiry |
| Static Site | ✅ | 100GB bandwidth |

**Для production:** Upgrade до Starter ($7-15/мес за сервис)

## 🔧 Альтернативы Render

| Платформа | Плюсы | Минусы |
|-----------|-------|--------|
| **Railway** | Проще Docker Compose | Дороже |
| **Fly.io** | Глобальные регионы | CLI-first |
| **DigitalOcean** | Полный контроль | Нужно настраивать |
| **Hetzner + Coolify** | Дешево, полный контроль | Self-hosted |

## 🐛 Известные проблемы Render

1. **Sleeping services** — Web service засыпает после 15 мин без запросов
   - Решение: Upptime мониторинг или paid plan

2. **MTProto phone code** — Нельзя ввести код в консоли
   - Решение: String Session (см. выше)

3. **Redis 25MB limit** — Может закончиться память
   - Решение: `maxmemory-policy allkeys-lru` (уже настроено)

4. **PostgreSQL 1GB** — Маловато для больших данных
   - Решение: Regular cleanup или upgrade

## 📞 Поддержка

- Render Docs: https://render.com/docs
- Telegram Bot API: https://core.telegram.org/bots/api
- Telethon: https://docs.telethon.dev
- FastAPI: https://fastapi.tiangolo.com
