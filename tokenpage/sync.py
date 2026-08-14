"""统一抓取入库流程（CLI 与 Web 共用）。

- 一批抓取共用同一时间戳，便于按「批次」查询最新快照
- 入库前应用峰谷折扣（存储、排序、显示统一用「有效价」）
- 失败的抓取站「沿用上一批次快照」（carry forward）：
  避免某站单次失败导致比价矩阵缺行、涨跌情报误报「下架」
"""

from __future__ import annotations

from datetime import datetime, timezone

from tokenpage.fetchers import fetch_all
from tokenpage.pricing import apply_offpeak
from tokenpage.storage import (
    carry_forward_providers,
    latest_fetched_at,
    save_quotes,
    set_meta,
)


def fetch_and_save() -> dict:
    """执行一次完整抓取并入库。

    返回：
        {"batch_ts", "counts": {provider: n}, "errors": {provider: msg},
         "saved": int, "carried": int}
    """
    # 先记下上一批次时间（失败站兜底数据来源）
    prev_at = latest_fetched_at()
    results, errors = fetch_all()

    # 一批抓取共用同一时间戳，便于按「批次」查询最新快照
    batch_ts = datetime.now(timezone.utc).isoformat()
    quotes = []
    for provider, qs in results.items():
        for q in qs:
            q.fetched_at = batch_ts
            apply_offpeak(q)
            quotes.append(q)

    carried = 0
    if quotes:
        save_quotes(quotes)
        # 普通 24h 冷却以 meta 为准（Web 端读取；对齐 CLI 抓取后的冷却显示）
        set_meta("last_fetch_at", batch_ts)
        # 失败的站沿用上一批快照，保持矩阵完整（仅在本次至少有一站成功时）
        carried = carry_forward_providers(prev_at, sorted(errors.keys()), batch_ts)
    return {
        "batch_ts": batch_ts,
        "counts": {provider: len(qs) for provider, qs in results.items()},
        "errors": errors,
        "saved": len(quotes),
        "carried": carried,
    }
