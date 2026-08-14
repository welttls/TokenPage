"""OpenRouter 限时折扣抓取器（优惠情报，独立于比价矩阵）。

OpenRouter 在 https://openrouter.ai/models?discount=true 提供限时折扣模型。
数据来自前端端点（无需 Key）：
    GET /api/frontend/v1/models/find?active=true&discount=true&fmt=cards

每个折扣模型含 pricing.discount（折扣因子，0.5 = 5 折）与折扣后价格。
本抓取器返回的 quote 用独立 provider 'openrouter_deals'，不混入比价矩阵，
供「限时折扣」面板单独展示。折扣力度存入 deal_tag。
"""

from __future__ import annotations

import requests

from tokenpage.config import logical_models, provider_labels
from tokenpage.models import PriceQuote, ROUTE_METERED

API = "https://openrouter.ai/api/frontend/v1/models/find?active=true&discount=true&fmt=cards"

# 折扣模型 ID 与 Go 清单的匹配：严格按「斜杠后段 == 逻辑模型 ID」精确匹配，
# 避免 glm-5→glm-5.3、hy3-preview→hy3 这类子串误配。
def _is_in_go_list(slug: str) -> bool:
    """判断折扣模型是否属于 OpenCode Go 清单（编程模型高亮用）。"""
    base = (slug or "").split("/")[-1].lower()
    return base in set(logical_models().keys())


def _undo_discount(price: float, discount: float) -> float:
    """折扣后价 → 原价（pricing.discount = 0.65 表示 65% off）。"""
    if discount <= 0 or discount >= 1:
        return price
    return price / (1 - discount)


def fetch() -> list[PriceQuote]:
    r = requests.get(
        API,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    r.raise_for_status()
    payload = r.json()
    models = (payload.get("data") or {}).get("models") or []

    quotes: list[PriceQuote] = []
    for m in models:
        slug = m.get("slug") or m.get("id")
        if not slug:
            continue
        endpoint = m.get("endpoint") or {}
        pricing = endpoint.get("pricing") or {}
        try:
            discount = float(pricing.get("discount", 0) or 0)
        except (TypeError, ValueError):
            discount = 0
        if discount <= 0:
            continue
        try:
            prompt = float(pricing.get("prompt", 0) or 0) * 1_000_000
            completion = float(pricing.get("completion", 0) or 0) * 1_000_000
            cache_read = float(pricing.get("input_cache_read", 0) or 0) * 1_000_000
        except (TypeError, ValueError):
            continue
        if prompt < 0 or completion < 0:
            continue

        pct = round(discount * 100)
        family = _guess_family(slug)
        # raw_* 存「原价」（折扣前），供并入矩阵时显示原价划掉/浮窗
        raw_prompt = _undo_discount(prompt, discount) if prompt else None
        raw_completion = _undo_discount(completion, discount) if completion else None
        quotes.append(
            PriceQuote(
                provider="openrouter_deals",
                provider_label="OpenRouter 限时折扣",
                model_id=slug,
                route_type=ROUTE_METERED,
                family=family,
                tier="",
                prompt_usd_per_1m=round(prompt, 6) if prompt else None,
                completion_usd_per_1m=round(completion, 6) if completion else None,
                cache_read_usd_per_1m=round(cache_read, 6) if cache_read else None,
                cache_write_usd_per_1m=None,
                tiered=None,
                context_length=m.get("context_length"),
                supports_tools=None,
                currency="USD",
                raw_prompt=round(raw_prompt, 6) if raw_prompt else None,
                raw_completion=round(raw_completion, 6) if raw_completion else None,
                discount_type="promo",
                deal_tag=f"🎁{pct}%off",
            )
        )
    return quotes


def _guess_family(model_id: str) -> str:
    """根据模型 ID 猜测 family（用于展示分组）。"""
    base = (model_id or "").lower()
    for key, fam in (
        ("claude", "claude"),
        ("kimi", "kimi"),
        ("glm", "glm"),
        ("grok", "grok"),
        ("gpt", "gpt"),
        ("deepseek", "deepseek"),
        ("qwen", "qwen"),
        ("gemini", "gemini"),
        ("minimax", "minimax"),
        ("hy3", "hy3"),
    ):
        if key in base:
            return fam
    return ""
