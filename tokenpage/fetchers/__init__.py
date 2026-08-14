"""抓取器注册表：统一 fetch() 接口，返回 List[PriceQuote]。

单站抓取失败不中断其他站——由 fetch_all 收集 errors。
"""

from __future__ import annotations

from tokenpage.fetchers import (
    deepseek,
    official,
    opencode_go,
    opencode_zen,
    openrouter,
    openrouter_discount,
    siliconflow,
)

FETCHERS = {
    "openrouter": openrouter.fetch,
    "openrouter_deals": openrouter_discount.fetch,
    "siliconflow": siliconflow.fetch,
    "opencode_go": opencode_go.fetch,
    "opencode_zen": opencode_zen.fetch,
    "deepseek": deepseek.fetch,
    "official": official.fetch,
}


def fetch_all() -> tuple[dict[str, list], dict[str, str]]:
    """运行所有抓取器。

    返回 (results, errors)：
    - results: {provider: [PriceQuote, ...]}
    - errors : {provider: 错误信息}（仅失败的站）
    """
    results: dict[str, list] = {}
    errors: dict[str, str] = {}
    for name, fn in FETCHERS.items():
        try:
            results[name] = fn()
        except Exception as e:  # noqa: BLE001 - 单站失败不中断
            errors[name] = f"{type(e).__name__}: {e}"
    return results, errors
