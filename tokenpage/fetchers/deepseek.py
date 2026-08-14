"""DeepSeek 官方抓取器（官方 API 直连路线）。

官方模型目录与定价来自 https://api-docs.deepseek.com/quick_start/pricing。
公开接口未提供免钥 JSON 目录，故内置官方价格表（PEAK 基准价），峰谷规则见
~/.tokenpage/rules.json 的 deepseek 段，由 pricing.apply_offpeak 在比价时计算。
"""

from __future__ import annotations

from tokenpage.config import provider_labels
from tokenpage.models import PriceQuote, ROUTE_OFFICIAL

# 官方定价（生效后 PEAK 基准，美元 / 1M tokens），来源官方定价页（2026-08-16 生效峰谷）
OFFICIAL_PRICING: dict[str, dict] = {
    "deepseek-v4-flash": {
        "prompt": 0.44, "completion": 1.32,
        "context": 1_000_000, "tools": True, "family": "deepseek",
    },
    "deepseek-v4-pro": {
        "prompt": 1.32, "completion": 3.96,
        "context": 1_000_000, "tools": True, "family": "deepseek",
    },
}


def fetch() -> list[PriceQuote]:
    quotes: list[PriceQuote] = []
    for mid, p in OFFICIAL_PRICING.items():
        quotes.append(
            PriceQuote(
                provider="deepseek",
                provider_label=provider_labels()["deepseek"],
                model_id=mid,
                route_type=ROUTE_OFFICIAL,
                family=p.get("family", "deepseek"),
                tier="",
                prompt_usd_per_1m=p["prompt"],
                completion_usd_per_1m=p["completion"],
                context_length=p["context"],
                supports_tools=p["tools"],
                currency="USD",
                raw_prompt=p["prompt"],
                raw_completion=p["completion"],
            )
        )
    return quotes
