"""DeepSeek 官方抓取器（官方 API 直连路线）。

官方模型目录与定价来自 https://api-docs.deepseek.com/quick_start/pricing。
公开接口未提供免钥 JSON 目录，故内置官方价格表。峰谷规则见
~/.tokenpage/rules.json 的 deepseek 段，由 pricing.apply_offpeak 在比价时计算。

DeepSeek 官方 2026-08-16 16:00 UTC 起切换峰谷计价：生效前按固定价（pre，即官网
当前明确清单价），生效后按 PEAK 基准价（peak，谷时半价）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from tokenpage.config import provider_labels
from tokenpage.models import PriceQuote, ROUTE_OFFICIAL

# 峰谷计价生效时刻（UTC），此前按「生效前固定价」
EFFECTIVE_FROM = "2026-08-16T16:00:00+00:00"

# 官方定价（美元 / 1M tokens），来源官方定价页 https://api-docs.deepseek.com/quick_start/pricing
# - pre  ：峰谷生效前固定价（含缓存命中输入价 cache_read）
# - peak ：峰谷生效后的 PEAK 基准价（谷时半价由 pricing.apply_offpeak 折算）
OFFICIAL_PRICING: dict[str, dict] = {
    "deepseek-v4-flash": {
        "pre": {"prompt": 0.14, "completion": 0.28, "cache_read": 0.0028},
        "peak": {"prompt": 0.44, "completion": 1.32, "cache_read": 0.014},
        "context": 1_000_000, "tools": True, "family": "deepseek",
    },
    "deepseek-v4-pro": {
        "pre": {"prompt": 0.435, "completion": 0.87, "cache_read": 0.003625},
        "peak": {"prompt": 1.32, "completion": 3.96, "cache_read": 0.044},
        "context": 1_000_000, "tools": True, "family": "deepseek",
    },
}


def _price_tier(now_utc: datetime | None = None) -> str:
    """按当前时刻返回生效价档位："peak"（峰谷已生效）/ "pre"（生效前固定价）。"""
    now = now_utc or datetime.now(timezone.utc)
    eff = datetime.fromisoformat(EFFECTIVE_FROM)
    return "peak" if now >= eff else "pre"


def fetch(now_utc: datetime | None = None) -> list[PriceQuote]:
    quotes: list[PriceQuote] = []
    tier = _price_tier(now_utc)
    for mid, p in OFFICIAL_PRICING.items():
        price = p[tier]
        quotes.append(
            PriceQuote(
                provider="deepseek",
                provider_label=provider_labels()["deepseek"],
                model_id=mid,
                route_type=ROUTE_OFFICIAL,
                family=p.get("family", "deepseek"),
                tier="",
                prompt_usd_per_1m=price["prompt"],
                completion_usd_per_1m=price["completion"],
                cache_read_usd_per_1m=price.get("cache_read"),
                context_length=p["context"],
                supports_tools=p["tools"],
                currency="USD",
                raw_prompt=price["prompt"],
                raw_completion=price["completion"],
            )
        )
    return quotes
