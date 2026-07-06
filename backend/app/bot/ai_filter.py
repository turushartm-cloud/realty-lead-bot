"""
Multi-Provider AI Engine with automatic failover.
Priority: Groq → OpenRouter → Gemini → Local heuristic
"""
import openai
import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from ..config import settings
import structlog

logger = structlog.get_logger()


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    base_url: str
    model: str
    rpm: int           # Requests per minute
    rpd: int           # Requests per day
    priority: int      # Lower = higher priority
    enabled: bool = True


class AIFilter:
    """
    AI фильтр с мульти-провайдерной архитектурой и автоматическим fallback.
    Если один провайдер падает/исчерпан — переключается на следующий.
    """

    CATEGORIES = [
        "buy", "sell", "rent", "rent_out", "mortgage",
        "consultation", "spam", "other"
    ]

    # ─── ПРОВАЙДЕРЫ (приоритет от высшего к низшему) ───────────
    PROVIDERS = [
        ProviderConfig(
            name="groq",
            api_key="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",
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            rpm=30,
            rpd=1000,
            priority=1
        ),
        ProviderConfig(
            name="openrouter",
            api_key="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",
            base_url="https://openrouter.ai/api/v1",
            model="deepseek/deepseek-chat-v3.1:free",
            rpm=20,
            rpd=50,
            priority=2
        ),
        ProviderConfig(
            name="gemini",
            api_key="AQ.Ab8RN6Ka_w4JYVX0jYwnyzFZE6gULllEYizqlx-DUui2JO6G3Q",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model="gemini-2.5-flash-lite",
            rpm=15,
            rpd=1500,
            priority=3
        ),
        ProviderConfig(
            name="cerebras",
            api_key="csk-d868e4d4348we5fc8wf63yr8nwetf8km4vjmf4n5kjctcv8x",
            base_url="https://api.cerebras.ai/v1",
            model="llama-3.3-70b",
            rpm=5,
            rpd=1000,
            priority=4
        ),
        ProviderConfig(
            name="mistral",
            api_key="1R3l9pPkDOFj8Z66ahYepaEufbdVtuGx",
            base_url="https://api.mistral.ai/v1",
            model="mistral-small-latest",
            rpm=10,
            rpd=10000,
            priority=5
        ),
    ]

    def __init__(self):
        self._clients: Dict[str, openai.AsyncOpenAI] = {}
        self._counters: Dict[str, dict] = {}
        self._cache: Dict[int, Dict] = {}
        self._init_clients()
        self._start_reset_task()

    def _init_clients(self):
        """Инициализация клиентов для всех провайдеров."""
        for provider in self.PROVIDERS:
            try:
                self._clients[provider.name] = openai.AsyncOpenAI(
                    api_key=provider.api_key,
                    base_url=provider.base_url,
                    timeout=30.0,
                    max_retries=2
                )
                self._counters[provider.name] = {
                    "requests_minute": 0,
                    "requests_day": 0,
                    "last_reset_minute": asyncio.get_event_loop().time(),
                    "last_reset_day": asyncio.get_event_loop().time(),
                    "failures": 0,
                    "disabled_until": 0
                }
                logger.info(f"AI provider initialized: {provider.name}")
            except Exception as e:
                logger.error(f"Failed to init provider {provider.name}: {e}")

    def _start_reset_task(self):
        """Фоновая задача сброса счетчиков."""
        asyncio.create_task(self._reset_counters_loop())

    async def _reset_counters_loop(self):
        """Сброс счетчиков каждую минуту и каждые 24 часа."""
        while True:
            await asyncio.sleep(60)
            now = asyncio.get_event_loop().time()
            for name, counter in self._counters.items():
                # Reset per-minute
                if now - counter["last_reset_minute"] >= 60:
                    counter["requests_minute"] = 0
                    counter["last_reset_minute"] = now
                    counter["failures"] = max(0, counter["failures"] - 1)  # Decay failures
                # Reset per-day (approximate)
                if now - counter["last_reset_day"] >= 86400:
                    counter["requests_day"] = 0
                    counter["last_reset_day"] = now

    def _is_provider_available(self, provider: ProviderConfig) -> bool:
        """Проверка доступности провайдера."""
        counter = self._counters.get(provider.name)
        if not counter:
            return False

        now = asyncio.get_event_loop().time()

        # Check if temporarily disabled
        if now < counter["disabled_until"]:
            return False

        # Check rate limits
        if counter["requests_minute"] >= provider.rpm:
            return False
        if counter["requests_day"] >= provider.rpd:
            return False

        # Check failure threshold
        if counter["failures"] >= 5:
            counter["disabled_until"] = now + 300  # Disable for 5 min
            logger.warning(f"Provider {provider.name} disabled due to failures")
            return False

        return True

    def _get_available_providers(self) -> List[ProviderConfig]:
        """Получить список доступных провайдеров по приоритету."""
        available = []
        for provider in sorted(self.PROVIDERS, key=lambda p: p.priority):
            if self._is_provider_available(provider):
                available.append(provider)
        return available

    async def analyze(self, text: str) -> Dict:
        """
        Анализ сообщения с автоматическим fallback между провайдерами.
        """
        # Check cache
        cache_key = hash(text[:200])
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get available providers
        providers = self._get_available_providers()

        if not providers:
            logger.warning("All AI providers exhausted, using local heuristic")
            result = self._local_analyze(text)
            self._cache[cache_key] = result
            return result

        # Try each provider in order
        last_error = None
        for provider in providers:
            try:
                result = await self._call_provider(provider, text)

                # Update counters
                self._counters[provider.name]["requests_minute"] += 1
                self._counters[provider.name]["requests_day"] += 1
                self._counters[provider.name]["failures"] = max(0, self._counters[provider.name]["failures"] - 1)

                # Cache result
                self._cache[cache_key] = result

                logger.info(
                    "AI analysis completed",
                    provider=provider.name,
                    score=result["score"],
                    category=result["category"]
                )
                return result

            except Exception as e:
                self._counters[provider.name]["failures"] += 1
                last_error = e
                logger.warning(
                    f"Provider {provider.name} failed",
                    error=str(e),
                    failures=self._counters[provider.name]["failures"]
                )
                continue

        # All providers failed
        logger.error("All AI providers failed", last_error=str(last_error))
        result = self._local_analyze(text)
        self._cache[cache_key] = result
        return result

    async def _call_provider(self, provider: ProviderConfig, text: str) -> Dict:
        """Вызов конкретного провайдера."""
        client = self._clients.get(provider.name)
        if not client:
            raise ValueError(f"Client not initialized for {provider.name}")

        prompt = f"""Analyze this real estate message from a Telegram group.
Determine if it is a potential lead (client).

Message: "{text[:1500]}"

Respond STRICTLY in this JSON format:
{{
    "score": float (0-1, relevance to real estate lead),
    "category": str (buy/sell/rent/rent_out/mortgage/consultation/spam/other),
    "summary": str (brief intent in Russian, 1-2 sentences),
    "keywords": [str] (matched keywords),
    "urgency": str (low/medium/high),
    "budget_hint": str (if budget mentioned, else null)
}}
"""

        response = await client.chat.completions.create(
            model=provider.model,
            messages=[
                {"role": "system", "content": "You are a real estate market expert. Respond only in JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        return {
            "score": max(0.0, min(1.0, float(result.get("score", 0)))),
            "category": result.get("category", "other"),
            "summary": result.get("summary", ""),
            "keywords": result.get("keywords", []),
            "urgency": result.get("urgency", "low"),
            "budget_hint": result.get("budget_hint")
        }

    def _local_analyze(self, text: str) -> Dict:
        """Локальная эвристика (fallback без API)."""
        text_lower = text.lower()

        buy_keywords = ["купить", "покупка", "приобрести", "ищу квартиру", "ищу дом", "хочу купить"]
        sell_keywords = ["продать", "продажа", "продаю", "продается", "продам", "сдаю в продажу"]
        rent_keywords = ["снять", "сниму", "аренда", "арендовать", "ищу жилье", "сниму квартиру"]
        rent_out_keywords = ["сдать", "сдаю", "сдается", "арендодатель", "сдам квартиру"]
        mortgage_keywords = ["ипотека", "кредит", "рассрочка", "банк", "одобрение ипотеки"]

        all_keywords = {
            "buy": buy_keywords,
            "sell": sell_keywords,
            "rent": rent_keywords,
            "rent_out": rent_out_keywords,
            "mortgage": mortgage_keywords
        }

        scores = {}
        matched_keywords = []

        for category, keywords in all_keywords.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = count
            matched_keywords.extend([kw for kw in keywords if kw in text_lower])

        best_category = max(scores, key=scores.get) if scores else "other"
        best_score = scores.get(best_category, 0)

        normalized_score = min(best_score * 0.25, 0.95) if best_score > 0 else 0.1

        urgency_markers = ["срочно", "быстро", "сегодня", "сейчас", "asap", "нужно срочно"]
        if any(m in text_lower for m in urgency_markers):
            normalized_score = min(normalized_score + 0.1, 1.0)
            urgency = "high"
        else:
            urgency = "medium" if normalized_score > 0.5 else "low"

        return {
            "score": round(normalized_score, 2),
            "category": best_category if best_score > 0 else "other",
            "summary": f"Local analysis: {best_category}, found {best_score} keywords",
            "keywords": list(set(matched_keywords))[:10],
            "urgency": urgency,
            "budget_hint": None
        }

    def get_provider_status(self) -> List[Dict]:
        """Получить статус всех провайдеров."""
        status = []
        for provider in self.PROVIDERS:
            counter = self._counters.get(provider.name, {})
            status.append({
                "name": provider.name,
                "model": provider.model,
                "available": self._is_provider_available(provider),
                "requests_minute": counter.get("requests_minute", 0),
                "requests_day": counter.get("requests_day", 0),
                "rpm_limit": provider.rpm,
                "rpd_limit": provider.rpd,
                "failures": counter.get("failures", 0)
            })
        return status
