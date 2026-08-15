"""SiliconFlow 抓取器：公开定价页 HTML 解析（人民币 ¥/1M）。

- https://siliconflow.cn/pricing 为公开定价页（无需 Key）
- 模型价格为人民币，换算成美元存 USD 字段，原始价保留在 raw_*
- 只抓配置中跟踪的目标模型（Go 页清单映射到硅基流动的 ID）
- 解析不到目标模型时跳过该模型（不报错）；整页解析失败则抛异常由上层降级

跨站映射容错：精确词边界匹配失败时，用归一化名 + 编辑距离在页面里找最接近的
模型名兜底（命中打 warning 提示固化 models.json，不自动回写）。
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from tokenpage.config import load_fx, provider_labels, station_meta_map
from tokenpage.matching import best_fuzzy_match
from tokenpage.models import PriceQuote, ROUTE_METERED

log = logging.getLogger("tokenpage")

PRICING_URL = "https://siliconflow.cn/pricing"

# 页面中可能的模型名 token（字母开头，含 - . _ 等分隔符）
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.\-_]{2,}")


def _sf_base_name(model_id: str) -> str:
    """SiliconFlow 模型 ID 形如 zai-org/GLM-5.2，取末段作为定价页匹配名。"""
    return model_id.split("/")[-1]


def _find_price(text: str, base: str) -> tuple[float, float] | None:
    """在页面文本中定位「模型名 ... ¥输入 ¥输出」，返回 (输入, 输出) 人民币价。

    模型名加词边界（前后不能是字母/数字/./-），避免 GLM-5.2 误命中
    GLM-5.25、GLM-5.2.5 这类更长型号的位置。
    """
    m = re.search(rf"(?<![\w.\-]){re.escape(base)}(?![\w.\-])", text)
    if not m:
        return None
    tail = text[m.start() : m.start() + 300]
    nums = re.findall(r"¥\s*([\d.]+)", tail)
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    return None


def _find_price_fuzzy(text: str, base: str) -> tuple[float, float] | None:
    """精确匹配失败后的兜底：在页面里找与 base 归一化后最相近的模型名再取价。

    返回 None 表示没找到足够接近的名字（不强行入库）。
    """
    cands = sorted({m.group() for m in _TOKEN_RE.finditer(text)})
    best, sim = best_fuzzy_match(base, cands)
    if best is None:
        return None
    hit = _find_price(text, best)
    if hit is None:
        return None
    log.warning(
        "SiliconFlow 精确名未命中 %s，模糊匹配到 %s（相似度 %.2f）——疑似改名，建议固化到 models.json",
        base, best, sim,
    )
    return hit


def fetch() -> list[PriceQuote]:
    meta = station_meta_map("siliconflow")
    if not meta:
        return []

    r = requests.get(
        PRICING_URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    fx = load_fx()
    try:
        cny_per_usd = float(fx.get("CNY_per_USD", 7.2))
    except (TypeError, ValueError):
        cny_per_usd = 7.2

    quotes: list[PriceQuote] = []
    for mid, (lm, fam) in meta.items():
        base = _sf_base_name(mid)
        found = _find_price(text, base) or _find_price_fuzzy(text, base)
        if not found:
            continue
        prompt_cny, completion_cny = found
        quotes.append(
            PriceQuote(
                provider="siliconflow",
                provider_label=provider_labels()["siliconflow"],
                model_id=mid,
                route_type=ROUTE_METERED,
                family=fam,
                tier="",
                prompt_usd_per_1m=round(prompt_cny / cny_per_usd, 6),
                completion_usd_per_1m=round(completion_cny / cny_per_usd, 6),
                context_length=None,
                supports_tools=None,
                currency="CNY",
                raw_prompt=prompt_cny,
                raw_completion=completion_cny,
            )
        )
    return quotes
