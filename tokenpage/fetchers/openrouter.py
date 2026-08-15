"""OpenRouter 抓取器：GET /api/v1/models（公开，无需 Key）。

只抓配置中跟踪的目标模型（Go 页清单映射到 OpenRouter 的 ID）。
pricing.prompt / completion 单位为「每 token 美元」，×1e6 换算为 $/1M。
缓存价：input_cache_read / input_cache_write。

跨站映射容错（models.json 保持权威）：
  1. 精确站 ID 匹配（配置优先）
  2. 归一化模型 name 匹配（各站 name 通常比 ID 更统一）
  3. Levenshtein 模糊兜底（ID 失效/改名时找最接近的）
命中 2/3 时打 warning 提示「建议固化到 models.json」，但不自动回写。
"""

from __future__ import annotations

import logging

import requests

from tokenpage.config import provider_labels, station_meta_map
from tokenpage.matching import best_fuzzy_match, normalize
from tokenpage.models import PriceQuote, ROUTE_METERED

log = logging.getLogger("tokenpage")

API = "https://openrouter.ai/api/v1/models"


def _build_quote(m: dict, mid: str, lm: str, fam: str) -> PriceQuote | None:
    """从 OpenRouter 单条模型数据构建 PriceQuote；无法解析返回 None。"""
    pricing = m.get("pricing") or {}
    try:
        prompt_per_token = float(pricing.get("prompt", 0) or 0)
        completion_per_token = float(pricing.get("completion", 0) or 0)
        cache_read_per_token = float(pricing.get("input_cache_read", 0) or 0)
        cache_write_per_token = float(pricing.get("input_cache_write", 0) or 0)
    except (TypeError, ValueError):
        return None
    # router 类模型价格为 -1，跳过
    if prompt_per_token < 0 or completion_per_token < 0:
        return None
    prompt = prompt_per_token * 1_000_000
    completion = completion_per_token * 1_000_000
    cache_read = cache_read_per_token * 1_000_000 if cache_read_per_token > 0 else None
    cache_write = cache_write_per_token * 1_000_000 if cache_write_per_token > 0 else None
    params = set(m.get("supported_parameters") or [])
    # top_provider 为对象；兼容未来字段形态（tiered 布尔或字符串）
    tp = m.get("top_provider")
    if isinstance(tp, dict):
        tiered = bool(tp.get("tiered")) or None
    else:
        tiered = (tp == "tiered") or None
    return PriceQuote(
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

    # 站内索引：id → 模型；归一化 name → 模型（供名称匹配）
    by_id: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for m in data:
        mid = m.get("id")
        if not mid:
            continue
        by_id.setdefault(mid, m)
        nm = normalize(m.get("name"))
        if nm:
            by_name.setdefault(nm, m)

    quotes: list[PriceQuote] = []
    resolved: set[str] = set()  # 已匹配的站 ID（避免同一模型重复入库）
    unmatched: list[str] = []  # 未匹配的逻辑模型

    # 1) 精确站 ID 匹配（models.json 权威）
    for sid in sorted(wanted):
        if sid in by_id:
            lm, fam = meta[sid]
            q = _build_quote(by_id[sid], sid, lm, fam)
            if q:
                quotes.append(q)
            resolved.add(sid)

    # 2)+3) 未命中的逻辑模型：归一化 name → 模糊兜底
    for sid, (lm, fam) in meta.items():
        if sid in resolved:
            continue
        hit: dict | None = None
        hit_id: str | None = None
        # 2) 用逻辑模型 ID 的归一化名匹配站内 name
        hit = by_name.get(normalize(lm))
        if hit:
            hit_id = hit.get("id")
        else:
            # 3) 对配置的站 ID 与所有未命中站 ID 做编辑距离模糊
            cands = [mid for mid in by_id if mid not in resolved]
            best, sim = best_fuzzy_match(sid, cands)
            # 子串约束防版本号误配：逻辑模型归一化名必须包含在候选名里
            #（如 glm-5.3 → 候选 z-ai/glm-5 归一化 'zaiglm5' 不含 'glm53' → 拒绝；
            #   deepseek-v4-pro → 候选 .../v4-pro-0813 含 'deepseekv4pro' → 接受）
            if best and normalize(lm) and normalize(lm) in normalize(best):
                hit = by_id[best]
                hit_id = best
                log.warning(
                    "OpenRouter 精确 ID 未命中 %s（配置 %s），模糊匹配到 %s（相似度 %.2f）"
                    "——疑似改名/新增，建议固化到 models.json",
                    lm, sid, best, sim,
                )
        if hit and hit_id and hit_id not in resolved:
            q = _build_quote(hit, hit_id, lm, fam)
            if q:
                quotes.append(q)
            resolved.add(hit_id)
        else:
            unmatched.append(lm)

    if unmatched:
        log.warning("OpenRouter 未匹配到以下逻辑模型（可能已下架/改名）：%s", "、".join(unmatched))
    return quotes
