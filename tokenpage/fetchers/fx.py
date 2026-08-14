"""人民币兑美元汇率抓取器（随每日抓取顺带更新 fx.json）。

免钥公开端点（失败自动换下一个）：
1. open.er-api.com —— 开源镜像，带更新时间戳，覆盖全币种
2. api.frankfurter.app —— 欧洲央行数据源，官方基准

抓取失败返回 None，调用方保留 fx.json 原值兜底。
"""

from __future__ import annotations

from datetime import datetime, timezone

import requests

# 与其它抓取器一致的 UA（部分站点对无 UA 请求不友好）
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TokenPage/0.3; +https://github.com/welttls/TokenPage)",
    "Accept": "application/json",
}

FX_ENDPOINTS: list[str] = [
    "https://open.er-api.com/v6/latest/USD",
    "https://api.frankfurter.app/latest?from=USD&to=CNY",
]


def fetch_fx() -> dict | None:
    """抓取 USD→CNY 汇率，成功返回覆盖字段，全部失败返回 None。

    返回示例：{"CNY_per_USD": 6.757, "fetched_at": "...", "note": "自动抓取", "source": "..."}
    """
    for url in FX_ENDPOINTS:
        try:
            r = requests.get(url, timeout=10, headers=_HEADERS)
            r.raise_for_status()
            data = r.json()
            rates = data.get("rates") or {}
            cny = float(rates.get("CNY"))
            if not cny or cny <= 0:
                continue
            return {
                "CNY_per_USD": round(cny, 4),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "note": "每日自动抓取（免钥公开汇率 API）",
                "source": url,
            }
        except Exception:  # noqa: BLE001 - 单端点失败换下一个
            continue
    return None
