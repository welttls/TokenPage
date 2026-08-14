"""OpenCode Zen 抓取器（按量付费路线）。

数据源：https://opencode.ai/docs/zh-cn/zen/ 页面 HTML 表格。
Zen 是 OpenCode 团队的按量付费网关，模型含 Claude 闭源模型（Go 里没有）。
本抓取器只保留「Go 清单中的模型 + Claude 模型」，避免与 Go 订阅重复，同时补 Claude。
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from tokenpage.config import logical_models, provider_labels
from tokenpage.models import PriceQuote, ROUTE_METERED, ZdrInfo

DOC_URL = "https://opencode.ai/docs/zh-cn/zen/"

# Zen 中需要额外跟踪的 Claude 模型（Go 无 Claude）
CLAUDE_MODELS = {
    "claude-opus-5": "claude",
    "claude-sonnet-5": "claude",
    "claude-sonnet-4-6": "claude",
    "claude-haiku-4-5": "claude",
}


def _parse_money(s: str) -> float | None:
    s = s.strip().replace(",", "")
    if not s or s in ("-", "—", "Free", "free"):
        return 0.0 if s.lower() == "free" else None
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else None


def _cell(tr, i: int) -> str:
    cells = tr.find_all(["th", "td"])
    if i >= len(cells):
        return ""
    return cells[i].get_text(" ", strip=True)


def fetch() -> list[PriceQuote]:
    r = requests.get(
        DOC_URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        return []

    # ---- table 0：展示名 -> 模型 ID ----
    name_to_id: dict[str, str] = {}
    for tr in tables[0].find_all("tr")[1:]:
        name, mid = _cell(tr, 0), _cell(tr, 1)
        if name and mid:
            name_to_id[name] = mid

    # ---- table 1：价格 ----
    price_rows: dict[str, dict] = {}
    for tr in tables[1].find_all("tr")[1:]:
        name = _cell(tr, 0)
        if not name:
            continue
        prompt = _parse_money(_cell(tr, 1))
        price_rows[name] = {
            "prompt": prompt,
            "completion": _parse_money(_cell(tr, 2)),
            "cache_read": _parse_money(_cell(tr, 3)),
            "cache_write": _parse_money(_cell(tr, 4)),
        }

    # 需要跟踪的逻辑模型（Go 清单）
    track = set(logical_models().keys())
    # 加上 Zen 的 Claude 模型
    for cid in CLAUDE_MODELS:
        track.add(cid)

    quotes: list[PriceQuote] = []
    for name, mid in name_to_id.items():
        # 归一化：比较模型 ID 是否在跟踪列表
        norm = mid.lower()
        if norm not in track:
            continue
        row = price_rows.get(name)
        if not row:
            continue
        family = ""
        if norm in CLAUDE_MODELS:
            family = CLAUDE_MODELS[norm]
        elif norm in track:
            family = (logical_models().get(norm) or {}).get("family", "")
        quote = PriceQuote(
            provider="opencode_zen",
            provider_label=provider_labels()["opencode_zen"],
            model_id=mid,
            route_type=ROUTE_METERED,
            family=family,
            tier="",
            prompt_usd_per_1m=row["prompt"],
            completion_usd_per_1m=row["completion"],
            cache_read_usd_per_1m=row["cache_read"],
            cache_write_usd_per_1m=row["cache_write"],
            tiered=None,
            currency="USD",
            raw_prompt=row["prompt"],
            raw_completion=row["completion"],
        )
        if row["prompt"] == 0:
            quote.deal_tag = "🆓限免"
        quotes.append(quote)
    return quotes
