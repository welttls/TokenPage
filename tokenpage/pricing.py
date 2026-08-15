"""峰谷计算 + 货币换算 + 有效价格。

规则位于 ~/.tokenpage/rules.json，形如：
{
  "deepseek": {
    "peak_hours_utc": [["01:00","04:00"],["06:00","10:00"]],
    "offpeak_multiplier": 0.5,
    "note": "...",
    "effective_from": "2026-08-16T16:00:00Z"
  }
}
"""

from __future__ import annotations

from datetime import datetime, timezone

from tokenpage.config import load_rules


def _parse_hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _minutes_of(now_utc: datetime) -> int:
    return now_utc.hour * 60 + now_utc.minute


def is_in_ranges(minute: int, ranges: list) -> bool:
    """判断 minute（一天内分钟数）是否落在任一 [start,end) 区间，支持跨天。"""
    for start, end in ranges:
        s, e = _parse_hm(start), _parse_hm(end)
        if s <= e:
            if s <= minute < e:
                return True
        else:  # 跨天，如 22:00-02:00
            if minute >= s or minute < e:
                return True
    return False


def offpeak_status(
    provider: str, now_utc: datetime | None = None
) -> tuple[bool | None, float | None]:
    """返回 (是否谷时, 倍率)。该 provider 无规则则返回 (None, None)。

    若规则声明了 effective_from（峰谷生效时刻），生效前一律返回 (None, None)，
    避免对「生效前固定价」误乘折扣。
    """
    rules = load_rules()
    prov = rules.get(provider)
    if not prov:
        return None, None
    now = now_utc or datetime.now(timezone.utc)
    eff = prov.get("effective_from")
    if eff:
        try:
            eff_dt = datetime.fromisoformat(eff.replace("Z", "+00:00"))
            if now < eff_dt:
                return None, None
        except ValueError:
            pass
    peak = prov.get("peak_hours_utc", [])
    minute = _minutes_of(now)
    in_peak = is_in_ranges(minute, peak) if peak else False
    try:
        mult = float(prov.get("offpeak_multiplier", 1.0))
    except (TypeError, ValueError):
        mult = 1.0
    return (not in_peak), mult


def apply_offpeak(quote, now_utc: datetime | None = None):
    """就地给 quote 应用峰谷折扣。

    若当前为谷时且该 provider 有峰谷规则，直接把 prompt_usd_per_1m /
    completion_usd_per_1m 乘以折扣（存储、排序、显示统一用「有效价」），
    原始基准价保留在 raw_prompt / raw_completion。
    """
    off, mult = offpeak_status(quote.provider, now_utc)
    quote.is_offpeak = off
    if off and mult is not None:
        quote.offpeak_multiplier = mult
        quote.discount_type = "offpeak"
        if quote.prompt_usd_per_1m is not None:
            quote.prompt_usd_per_1m = round(quote.prompt_usd_per_1m * mult, 6)
        if quote.completion_usd_per_1m is not None:
            quote.completion_usd_per_1m = round(quote.completion_usd_per_1m * mult, 6)
        if quote.cache_read_usd_per_1m is not None:
            quote.cache_read_usd_per_1m = round(quote.cache_read_usd_per_1m * mult, 6)
        if quote.cache_write_usd_per_1m is not None:
            quote.cache_write_usd_per_1m = round(quote.cache_write_usd_per_1m * mult, 6)
    return quote


def apply_offpeak_live(route, now_utc: datetime | None = None):
    """比价展示时按「当前时刻」实时应用峰谷（route 为 recommender.RouteQuote）。

    - prompt/completion 以 raw_*（原始基准价）为准重新折算，避免对抓取时
      已应用过折扣的有效价重复乘折扣
    - cache_read/cache_write 未存 raw 基准：若入库时应用过折扣（行内
      is_offpeak=True），先除回基准价，再按当前时段重算
    - 无峰谷规则的 provider 只同步 is_offpeak 状态后跳过
    """
    off, mult = offpeak_status(route.provider, now_utc)
    was_off = route.is_offpeak  # 入库时是否谷时（DB 行状态）
    route.is_offpeak = off
    if mult is None:
        return route
    if route.raw_prompt is not None:
        route.prompt = round(route.raw_prompt * mult, 6) if off else round(route.raw_prompt, 6)
    if route.raw_completion is not None:
        route.completion = (
            round(route.raw_completion * mult, 6) if off else round(route.raw_completion, 6)
        )
    for attr in ("cache_read", "cache_write"):
        v = getattr(route, attr, None)
        if v is None:
            continue
        base = v / mult if was_off is True else v
        setattr(route, attr, round(base * mult, 6) if off else round(base, 6))
    if off:
        route.discount_type = "offpeak"
    return route
