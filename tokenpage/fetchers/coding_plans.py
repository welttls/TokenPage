"""官方订阅套餐抓取器（coding plan 路线）。

把模型厂商的官方订阅套餐（Claude/ChatGPT/GLM/通义/Kimi 订阅）折算成
「等效每 1M token 价」，作为 subscription 路线加进比价矩阵对应模型族下。

对标公式：
    等效价(模型 M) = 官方 API 标价(M) ÷ 倍率
    倍率 = 套餐月额度价值 ÷ 月费    （复用 quota.py 的 QuotaInfo 折算）

套餐额度口径（plans.json quota_type）：
- "tokens"：明确的每月 token 额度（tokens_in/tokens_out）→ 按该模型官方价折算成价值
- "value" ：明确的每月额度价值（如 Qoder Credits × 资源包单价）→ 直接作为价值
- "none"  ：无公开 token 额度（Claude/ChatGPT）→ 不折算数字，价格列标 ♾️、标签标宣称倍率

数据来源：plans.json（静态配置，可覆盖/追加）。套餐价不常变，无需实时抓取。
"""

from __future__ import annotations

import logging

from tokenpage.config import load_fx, load_plans, provider_labels
from tokenpage.fetchers.official import _merged as official_merged
from tokenpage.models import PriceQuote, QuotaInfo, ROUTE_SUBSCRIPTION
from tokenpage.quota import fmt_multiplier

log = logging.getLogger("tokenpage")

# plan provider key → official.py 中的厂商 key（用于查官方标价）
_OFFICIAL_PROVIDER = {
    "anthropic_plan": "anthropic",
    "openai_plan": "openai",
    "zhipu_plan": "zhipu",
    "alibaba_plan": "alibaba",
    "moonshot_plan": "moonshot",
}


def _to_usd(cur: str, v, cny: float):
    """CNY 计价按 fx 汇率折算 USD；USD 原样返回。"""
    if v is None:
        return None
    return round(v / cny, 6) if cur == "CNY" else round(v, 6)


def fetch() -> list[PriceQuote]:
    try:
        cny = float(load_fx().get("CNY_per_USD", 7.2))
    except (TypeError, ValueError):
        cny = 7.2
    official = official_merged()  # {provider: {model_id: {...价格字段}}}
    plans = load_plans()
    quotes: list[PriceQuote] = []

    for key, plan in plans.items():
        label = plan.get("label") or provider_labels().get(key, key)
        family = plan.get("family", "")
        cur = plan.get("currency", "USD")
        fee_usd = _to_usd(cur, plan.get("fee"), cny)
        qtype = plan.get("quota_type", "none")
        models = plan.get("models") or []
        op = _OFFICIAL_PROVIDER.get(key)

        for mid in models:
            raw = ((official.get(op) or {}).get(mid) or {}) if op else {}
            if qtype in ("tokens", "value"):
                if not raw.get("prompt") or not raw.get("completion"):
                    log.warning("coding plan %s：未在 official 官方价中找到模型 %s，已跳过", key, mid)
                    continue
                o_cur = raw.get("currency", "USD")
                if qtype == "tokens":
                    tokens_in = float(plan.get("tokens_in", 0) or 0)
                    tokens_out = float(plan.get("tokens_out", 0) or 0)
                    # 额度价值（按该模型官方价，原币种）→ USD
                    qv_native = tokens_in / 1e6 * float(raw["prompt"]) + tokens_out / 1e6 * float(raw["completion"])
                    qv_usd = _to_usd(o_cur, qv_native, cny)
                else:  # value：plans.json 直接给月额度价值（原币种）
                    qv_usd = _to_usd(cur, plan.get("monthly_quota"), cny)
                mult = (qv_usd / fee_usd) if fee_usd and qv_usd else None
                quota = QuotaInfo(
                    monthly_fee=fee_usd,
                    monthly_quota=qv_usd,
                    window=plan.get("window"),
                    note=f"{plan.get('fee')} {cur}/月 → {qv_usd:.2f}$ 额度（折算）",
                    tag=f"额度×{fmt_multiplier(mult)}" if mult else None,
                )
                quotes.append(
                    PriceQuote(
                        provider=key,
                        provider_label=label,
                        model_id=mid,
                        route_type=ROUTE_SUBSCRIPTION,
                        family=family,
                        prompt_usd_per_1m=_to_usd(o_cur, raw.get("prompt"), cny),
                        completion_usd_per_1m=_to_usd(o_cur, raw.get("completion"), cny),
                        cache_read_usd_per_1m=_to_usd(o_cur, raw.get("cache_read"), cny),
                        currency="USD",  # 计划等效价统一按美元展示（价格列显示有效价，¥ 模式按 fx 折算）
                        raw_prompt=_to_usd(o_cur, raw.get("prompt"), cny),   # 浮窗「标价」参考
                        raw_completion=_to_usd(o_cur, raw.get("completion"), cny),
                        quota=quota,
                        discount_type="quota",
                    )
                )
            else:  # "none"：无明确额度 → 不折算数字
                quotes.append(
                    PriceQuote(
                        provider=key,
                        provider_label=label,
                        model_id=mid,
                        route_type=ROUTE_SUBSCRIPTION,
                        family=family,
                        prompt_usd_per_1m=None,
                        completion_usd_per_1m=None,
                        currency="USD",
                        deal_tag=plan.get("tag"),
                        discount_type="unlimited",
                    )
                )
    return quotes
