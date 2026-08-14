"""OpenCode Go 抓取器（订阅折算路线）。

数据源：https://opencode.ai/docs/zh-cn/go/ 页面 HTML 表格。
从该页提取：
  - 模型清单（当前支持的模型列表，权威来源）
  - 价格（输入/输出/缓存读取/缓存写入，$ / 1M）
  - 使用额度（每月使用额度 $，用于折算等效价）
  - ZDR 隐私表（是否用于训练 + 数据保留天数）

阶梯价格（如 GPT 5.6 Luna ≤272K / >272K）合并为一条并标记 tiered。
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from tokenpage.config import load_go, provider_labels
from tokenpage.models import PriceQuote, QuotaInfo, ROUTE_SUBSCRIPTION, ZdrInfo

DOC_URL = "https://opencode.ai/docs/zh-cn/go/"
# 营销页（有「限时 2x usage」横幅，docs 表不包含）
MARKET_URL = "https://opencode.ai/go"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def _fetch_promo_multipliers(name_to_id: dict[str, str]) -> dict[str, float]:
    """抓营销页 opencode.ai/go 的「2x usage」徽标 → {逻辑模型ID: 倍率}。

    营销页的额度表为 JS 交互（1x/10x/... 滑块），静态 HTML 里以
    「2x usage / 2 倍使用额度」徽标文本出现，紧邻模型展示名。
    解析失败返回空 dict（由 go.json 配置兜底）。
    """
    try:
        r = requests.get(MARKET_URL, timeout=15, headers=_HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:  # noqa: BLE001 - 促销抓取失败不中断主流程
        return {}

    out: dict[str, float] = {}
    pattern = re.compile(r"2\s*x\s*usage|2\s*倍\s*使用额度", re.I)
    for node in soup.find_all(string=pattern):
        # 向上回溯，在最近的块里找模型展示名（与 docs 展示名一致）
        container = node.parent
        matched = None
        for _ in range(5):
            if container is None:
                break
            text = container.get_text(" ", strip=True)
            if text:
                for name, mid in name_to_id.items():
                    if name in text:
                        matched = mid
                        break
                if matched:
                    break
            container = container.parent
        if matched:
            out[matched] = 2.0
    return out


def _parse_money(s: str) -> float | None:
    """'$2.00' -> 2.0；'-' -> None。"""
    s = s.strip().replace(",", "")
    if not s or s == "-" or s == "—":
        return None
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else None


def _parse_days(s: str) -> int | None:
    """'30 天' -> 30；'0 天' -> 0。"""
    s = s.strip()
    if not s or s == "-" or s == "—":
        return None
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def _cell(tr, i: int) -> str:
    cells = tr.find_all(["th", "td"])
    if i >= len(cells):
        return ""
    return cells[i].get_text(" ", strip=True)


def _tables(soup: BeautifulSoup) -> list:
    return soup.find_all("table")


def fetch() -> list[PriceQuote]:
    r = requests.get(
        DOC_URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    tables = _tables(soup)

    go = load_go()
    monthly_fee = float(go.get("monthly_fee", 10.0))
    base_quota = float(go.get("base_quota", 60.0))

    # ---- table 2：展示名 -> 逻辑模型 ID（= 模型清单）----
    name_to_id: dict[str, str] = {}
    if len(tables) > 2:
        for tr in tables[2].find_all("tr")[1:]:
            name = _cell(tr, 0)
            mid = _cell(tr, 1)
            if name and mid:
                name_to_id[name] = mid
    if not name_to_id:
        return []

    # ---- 限时额度促销（2x usage）：config 兜底 + 营销页自动抓取覆盖 ----
    promo: dict[str, dict] = dict(go.get("promo", {}) or {})
    scraped = _fetch_promo_multipliers(name_to_id)
    for mid, mult in scraped.items():
        promo[mid] = {
            "multiplier": mult,
            "note": "限时 2x usage（自动抓取 opencode.ai/go）",
            "source_url": MARKET_URL,
            "scraped": True,
        }

    # ---- table 1：价格 + 额度 ----
    price_rows: list[dict] = []
    if len(tables) > 1:
        for tr in tables[1].find_all("tr")[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) < 6 or not cells[0]:
                continue
            price_rows.append(
                {
                    "name": cells[0],
                    "prompt": _parse_money(cells[1]),
                    "completion": _parse_money(cells[2]),
                    "cache_read": _parse_money(cells[3]),
                    "cache_write": _parse_money(cells[4]),
                    "quota": _parse_money(cells[5]),
                }
            )

    # ---- table 3：ZDR ----
    zdr_rows: dict[str, dict] = {}
    if len(tables) > 3:
        for tr in tables[3].find_all("tr")[1:]:
            name = _cell(tr, 0)
            if not name:
                continue
            used = _cell(tr, 1)
            days = _parse_days(_cell(tr, 2))
            zdr_rows[name] = {
                "used_for_training": False if "不" in used or "no" in used.lower() else None,
                "retention_days": days,
            }

    # ---- 合并价格行（处理阶梯价格）----
    merged: dict[str, dict] = {}
    for row in price_rows:
        name = row["name"]
        # 阶梯标记：名字含 (≤... / (>... 说明是同一模型分档
        base_name = re.sub(r"\s*[<(（].*", "", name).strip()
        if base_name in name_to_id:
            name = base_name
        if name in merged:
            merged[name]["tiered"] = True
            # 用更贵的档作为展示价（保守），保留缓存等
            cur = merged[name]
            for k in ("prompt", "completion", "cache_read", "cache_write"):
                if row.get(k) and (cur.get(k) is None or row[k] > cur[k]):
                    cur[k] = row[k]
        else:
            merged[name] = {**row, "tiered": False}

    quotes: list[PriceQuote] = []
    for name, row in merged.items():
        mid = name_to_id.get(name)
        if not mid:
            continue
        zdr = zdr_rows.get(name, {})
        base_quota_usd = row["quota"]
        promo_entry = promo.get(mid)
        if promo_entry:
            mult = float(promo_entry.get("multiplier", 1.0))
            eff_quota = base_quota_usd * mult if base_quota_usd else None
            base_mult = base_quota_usd / monthly_fee if base_quota_usd else None
            qtag = f"额度×{base_mult:g}·限时×{mult:g}" if base_mult else f"限时×{mult:g}"
            qnote = (
                f"{monthly_fee:g}$/月 → {eff_quota:g}$ 额度"
                f"（基础×{base_mult:g}·限时×{mult:g}，{promo_entry.get('note', '限时促销')}）"
            )
            quota = QuotaInfo(
                monthly_fee=monthly_fee,
                monthly_quota=eff_quota,
                window="5h/周/月",
                note=qnote,
                tag=qtag,
            )
        else:
            quota = QuotaInfo(
                monthly_fee=monthly_fee,
                monthly_quota=base_quota_usd,
                window="5h/周/月",
                note=f"{monthly_fee:g}$/月 → {base_quota_usd:g}$ 额度",
            )
        quote = PriceQuote(
            provider="opencode_go",
            provider_label=provider_labels()["opencode_go"],
            model_id=mid,
            route_type=ROUTE_SUBSCRIPTION,
            family=_guess_family(mid),
            tier="",
            prompt_usd_per_1m=row["prompt"],
            completion_usd_per_1m=row["completion"],
            cache_read_usd_per_1m=row["cache_read"],
            cache_write_usd_per_1m=row["cache_write"],
            tiered=row["tiered"] or None,
            currency="USD",
            raw_prompt=row["prompt"],
            raw_completion=row["completion"],
            quota=quota,
            zdr=ZdrInfo(**zdr),
            discount_type="quota",
        )
        # 免费/限免模型打标（额度覆盖或零价）
        if row["prompt"] == 0 or (row["quota"] and row["quota"] >= base_quota * 10):
            quote.deal_tag = "🆓限免"
        quotes.append(quote)
    return quotes


def _guess_family(model_id: str) -> str:
    """根据模型 ID 猜测 family。"""
    m = model_id.lower()
    if m.startswith("grok"):
        return "grok"
    if m.startswith("glm"):
        return "glm"
    if m.startswith("gpt"):
        return "gpt"
    if m.startswith("kimi"):
        return "kimi"
    if m.startswith("deepseek"):
        return "deepseek"
    if m.startswith("qwen"):
        return "qwen"
    if m.startswith("mimo"):
        return "mimo"
    if m.startswith("minimax"):
        return "minimax"
    if m.startswith("hy3"):
        return "hy3"
    return ""
