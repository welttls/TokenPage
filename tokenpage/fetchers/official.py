"""官方 API 直连抓取器（official 路线）。

官方厂商直连价格（$ / 1M tokens）。这些是稳定价目表（非优惠情报），作为比价基准。
DeepSeek 官方已在 fetchers/deepseek.py（含峰谷规则），此处覆盖其余 6 家：
Anthropic / OpenAI / xAI / Moonshot / Zhipu / Alibaba。

价格来源：各厂商公开定价页（与 OpenCode Zen 转售价接近），可在
~/.tokenpage/official.json 覆盖（structure: {provider: {model_id: {...}}}）。
"""

from __future__ import annotations

from tokenpage.config import load_official, provider_labels
from tokenpage.models import PriceQuote, ROUTE_OFFICIAL

# 内置官方价（美元 / 1M tokens）。来源：厂商公开定价页。
# 注：标价可能随厂商调价变化，请以 official.json 覆盖为准。
OFFICIAL_PRICING: dict[str, dict[str, dict]] = {
    "anthropic": {
        "claude-opus-5": {"prompt": 5.00, "completion": 25.00, "family": "claude", "context": 1_000_000},
        "claude-sonnet-5": {"prompt": 2.00, "completion": 10.00, "family": "claude", "context": 1_000_000},
        "claude-sonnet-4-6": {"prompt": 3.00, "completion": 15.00, "family": "claude", "context": 200_000},
        "claude-haiku-4-5": {"prompt": 1.00, "completion": 5.00, "family": "claude", "context": 200_000},
    },
    "openai": {
        "gpt-5.6-sol": {"prompt": 5.00, "completion": 30.00, "family": "gpt", "context": 400_000},
        "gpt-5.5": {"prompt": 5.00, "completion": 30.00, "family": "gpt", "context": 400_000},
    },
    "xai": {
        "grok-4.6": {"prompt": 2.00, "completion": 6.00, "family": "grok", "context": 256_000},
        "grok-4.5": {"prompt": 2.00, "completion": 6.00, "family": "grok", "context": 256_000},
    },
    "moonshot": {
        # 官方 Moonshot/Kimi API 为人民币计价（platform.kimi.com/docs/pricing/*）。
        # prompt=输入(缓存未命中) / cache_read=输入(缓存命中) / completion=输出。
        "kimi-k3": {
            "prompt": 20.00, "completion": 100.00, "cache_read": 2.00,
            "family": "kimi", "context": 1_000_000, "currency": "CNY",
        },
        "kimi-k2.7-code": {
            "prompt": 6.50, "completion": 27.00, "cache_read": 1.30,
            "family": "kimi", "context": 262_144, "currency": "CNY",
        },
        "kimi-k2.6": {
            "prompt": 6.50, "completion": 27.00, "cache_read": 1.10,
            "family": "kimi", "context": 262_144, "currency": "CNY",
        },
    },
    "zhipu": {
        "glm-5.3": {"prompt": 1.40, "completion": 4.40, "family": "glm", "context": 200_000},
        "glm-5.2": {"prompt": 1.40, "completion": 4.40, "family": "glm", "context": 200_000},
        "glm-5.1": {"prompt": 1.40, "completion": 4.40, "family": "glm", "context": 200_000},
    },
    "alibaba": {
        "qwen3.8-max": {"prompt": 2.50, "completion": 7.50, "family": "qwen", "context": 250_000},
        "qwen3.7-max": {"prompt": 2.50, "completion": 7.50, "family": "qwen", "context": 250_000},
        "qwen3.7-plus": {"prompt": 0.40, "completion": 1.60, "family": "qwen", "context": 256_000},
    },
}

# official.json 覆盖合并后的最终表
_OVERRIDDEN: dict | None = None


def _merged() -> dict[str, dict[str, dict]]:
    global _OVERRIDDEN
    if _OVERRIDDEN is not None:
        return _OVERRIDDEN
    merged: dict[str, dict[str, dict]] = {}
    for prov, models in OFFICIAL_PRICING.items():
        merged.setdefault(prov, {}).update(models)
    # 用户覆盖（official.json）：仅接受 dict 值（价格字段），忽略字符串映射
    user = load_official()
    for prov, models in user.items():
        for mid, meta in models.items():
            if not isinstance(meta, dict):
                continue
            merged.setdefault(prov, {})[mid] = {**merged.get(prov, {}).get(mid, {}), **meta}
    _OVERRIDDEN = merged
    return merged


def fetch() -> list[PriceQuote]:
    from tokenpage.config import load_fx

    fx = load_fx()
    try:
        cny_per_usd = float(fx.get("CNY_per_USD", 7.2))
    except (TypeError, ValueError):
        cny_per_usd = 7.2

    def _to_usd(cur: str, v):
        """CNY 计价按 fx 汇率折算 USD；USD 原样返回。"""
        if v is None:
            return None
        return round(v / cny_per_usd, 6) if cur == "CNY" else v

    quotes: list[PriceQuote] = []
    for provider, models in _merged().items():
        label = provider_labels().get(provider, provider)
        for mid, m in models.items():
            cur = m.get("currency", "USD")
            quotes.append(
                PriceQuote(
                    provider=provider,
                    provider_label=label,
                    model_id=mid,
                    route_type=ROUTE_OFFICIAL,
                    family=m.get("family", ""),
                    tier="",
                    prompt_usd_per_1m=_to_usd(cur, m.get("prompt")),
                    completion_usd_per_1m=_to_usd(cur, m.get("completion")),
                    cache_read_usd_per_1m=_to_usd(cur, m.get("cache_read")),
                    cache_write_usd_per_1m=_to_usd(cur, m.get("cache_write")),
                    tiered=m.get("tiered"),
                    context_length=m.get("context"),
                    supports_tools=m.get("tools"),
                    currency=cur,
                    raw_prompt=m.get("prompt"),
                    raw_completion=m.get("completion"),
                )
            )
    return quotes
