"""OpenRouter 抓取器：GET /api/v1/models（公开，无需 Key）。

只抓取配置中跟踪的目标模型（Go 页清单映射到 OpenRouter 的 ID）。
pricing.prompt / completion 单位为「每 token 美元」，×1e6 换算为 $/1M。
缓存价：input_cache_read / input_cache_write。
"""

from __future__ import annotations

import requests

from tokenpage.config import provider_labels, station_meta_map
from tokenpage.models import PriceQuote, ROUTE_METERED

API = "https://openrouter.ai/api/v1/models"


def fetch() -> list[PriceQuote]:
    meta = station_meta_map("openrouter")
    wanted = set(meta.keys())

    r = requests.get(
        API,
        timeout=20,
        headers={"User-Agent": "tokenpage/0.2 (price comparison)"},
    )
    r.raise_for_status()
    data = r.json().get("data", [])

    quotes: list[PriceQuote] = []
    for m in data:
        mid = m.get("id")
        if mid not in wanted:
            continue
        pricing = m.get("pricing") or {}
        try:
            prompt_per_token = float(pricing.get("prompt", 0) or 0)
            completion_per_token = float(pricing.get("completion", 0) or 0)
            cache_read_per_token = float(pricing.get("input_cache_read", 0) or 0)
            cache_write_per_token = float(pricing.get("input_cache_write", 0) or 0)
        except (TypeError, ValueError):
            continue
        # router 类模型价格为 -1，跳过
        if prompt_per_token < 0 or completion_per_token < 0:
            continue
        prompt = prompt_per_token * 1_000_000
        completion = completion_per_token * 1_000_000
        cache_read = cache_read_per_token * 1_000_000 if cache_read_per_token > 0 else None
        cache_write = cache_write_per_token * 1_000_000 if cache_write_per_token > 0 else None
        params = set(m.get("supported_parameters") or [])
        lm, fam = meta[mid]
        # top_provider 为对象；兼容未来字段形态（tiered 布尔或字符串）
        tp = m.get("top_provider")
        if isinstance(tp, dict):
            tiered = bool(tp.get("tiered")) or None
        else:
            tiered = (tp == "tiered") or None
        quotes.append(
            PriceQuote(
                provider="openrouter",
                provider_label=provider_labels()["openrouter"],
                model_id=mid,
                route_type=ROUTE_METERED,
                family=fam,
                tier="",
                prompt_usd_per_1m=round(prompt, 6),
                completion_usd_per_1m=round(completion, 6),
                cache_read_usd_per_1m=round(cache_read, 6) if cache_read else None,
                cache_write_usd_per_1m=round(cache_write, 6) if cache_write else None,
                tiered=tiered,
                context_length=m.get("context_length"),
                supports_tools="tools" in params,
                currency="USD",
                raw_prompt=round(prompt, 6),
                raw_completion=round(completion, 6),
            )
        )
    return quotes
