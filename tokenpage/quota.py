"""订阅额度折算引擎。

把「固定月费 + 模型额度」折算成等效每 1M token 价，以便与按量付费横向对比。

通用公式：
    等效价 = 该路线标价 × (订阅月费 ÷ 该模型月额度)

OpenCode Go 基础：月费 $10 → 基础额度 $60（6 倍）。
模型级额度倍率：部分模型额度更高（如 flash 2 倍额度），则总折扣倍率 = 6 × 2 = 12 倍，
等效价 = 标价 × 1/12（对应用户「flashv4 两倍额度 → 价格 1/12」的直觉）。
"""

from __future__ import annotations

from tokenpage.models import PriceQuote, QuotaInfo, ROUTE_SUBSCRIPTION


def apply_quota(
    quote: PriceQuote,
    monthly_fee: float,
    base_quota: float,
    model_quota: float | None = None,
    quota_multiplier: float | None = None,
    window: str | None = None,
) -> PriceQuote:
    """给 subscription 路线的 quote 应用额度折算。

    - monthly_fee: 订阅月费（USD）
    - base_quota: 基础月额度（USD 价值）
    - model_quota: 该模型月额度（USD 价值，优先于倍率计算）
    - quota_multiplier: 模型额度倍率（相对基础额度，如 2.0 = 2 倍额度）
    - window: 额度窗口描述（如「5h/周/月」）

    折算后：
    - quote.quota = QuotaInfo(...)
    - quote.discount_type = "quota"
    - 标价保持不变（保留在 prompt_usd_per_1m），等效价另算。
    """
    quote.route_type = ROUTE_SUBSCRIPTION
    quote.discount_type = "quota"

    if model_quota:
        eff_quota = float(model_quota)
    elif quota_multiplier:
        eff_quota = base_quota * float(quota_multiplier)
    else:
        eff_quota = base_quota

    quote.quota = QuotaInfo(
        monthly_fee=monthly_fee,
        monthly_quota=eff_quota,
        window=window,
        note=f"{monthly_fee:g}$/月 → {eff_quota:g}$ 额度",
    )
    return quote


def effective_prompt(quote: PriceQuote) -> float | None:
    """订阅路线的等效输入价（按量路线返回原价）。"""
    if quote.prompt_usd_per_1m is None:
        return None
    if quote.route_type == ROUTE_SUBSCRIPTION and quote.quota:
        mult = quote.quota.effective_multiplier
        if mult:
            return quote.prompt_usd_per_1m / mult
    return quote.prompt_usd_per_1m


def effective_completion(quote: PriceQuote) -> float | None:
    """订阅路线的等效输出价（按量路线返回原价）。"""
    if quote.completion_usd_per_1m is None:
        return None
    if quote.route_type == ROUTE_SUBSCRIPTION and quote.quota:
        mult = quote.quota.effective_multiplier
        if mult:
            return quote.completion_usd_per_1m / mult
    return quote.completion_usd_per_1m


def quota_label(quote: PriceQuote) -> str:
    """订阅路线的折扣标签。"""
    if quote.quota and quote.quota.effective_multiplier:
        return f"额度×{quote.quota.effective_multiplier:g}"
    return ""
