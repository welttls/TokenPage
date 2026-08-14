"""输出层：rich 终端表格（模型 × 路线 矩阵）+ JSON 输出。

比价矩阵展示：模型 → 各路线（OpenCode Go / OpenRouter / 硅基流动 / Zen / 官方）
的输入价、输出价、缓存价、阶梯与优惠标签。
"""

from __future__ import annotations

import json
import re
import sys

from rich.console import Console
from rich.table import Table

from tokenpage.recommender import FamilyView

# Windows 管道/重定向时强制 UTF-8，避免 rich 输出 emoji 触发 GBK 编码错误
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

console = Console()

ROUTE_HEADER = {
    "opencode_go": "OpenCode Go",
    "openrouter": "OpenRouter",
    "siliconflow": "硅基流动",
    "opencode_zen": "OpenCode Zen",
    "official": "官方直连",
}


def _fmt_price(v: float | None) -> str:
    if v is None:
        return "—"
    if v <= 0:
        return "🆓免费"
    return f"${v:.2f}" if v >= 0.005 else f"${v:.3f}"


def _fmt_tags(tags: list[str]) -> str:
    return " ".join(tags) if tags else ""


def render_matrix(views: list[FamilyView], fetched_at: str | None = None) -> Table:
    table = Table(title="🤖 Token黄页 — 模型 × 路线 比价矩阵", show_lines=True)
    table.add_column("模型族", style="bold cyan")
    table.add_column("模型")
    table.add_column("路线", style="bold")
    table.add_column("输入", justify="right")
    table.add_column("输出", justify="right")
    table.add_column("缓存读", justify="right")
    table.add_column("缓存写", justify="right")
    table.add_column("标签", style="yellow")

    for fv in views:
        fam_cell = fv.family_label
        first_in_fam = True
        for mv in fv.models:
            for r in mv.routes:
                route_header = ROUTE_HEADER.get(r.provider, r.provider_label)
                table.add_row(
                    fam_cell if first_in_fam else "",
                    mv.model_id,
                    route_header,
                    _fmt_price(r.prompt),
                    _fmt_price(r.completion),
                    _fmt_price(r.cache_read),
                    _fmt_price(r.cache_write),
                    _fmt_tags(r.price_tags),
                )
                first_in_fam = False

    if fetched_at:
        table.caption = f"数据时间（UTC）：{fetched_at}"
    return table


def print_matrix(views: list[FamilyView], fetched_at: str | None = None) -> None:
    console.print(render_matrix(views, fetched_at))


def render_deals(rows: list[dict]) -> Table:
    """限时折扣列表表格（OpenRouter deals）。"""
    table = Table(title="🎁 OpenRouter 限时折扣 — 找优惠券心态", show_lines=True)
    table.add_column("模型", style="bold cyan")
    table.add_column("族")
    table.add_column("折扣", justify="center", style="green")
    table.add_column("输入", justify="right")
    table.add_column("输出", justify="right")
    table.add_column("缓存读", justify="right")
    table.add_column("标签", style="yellow")

    for r in sorted(rows, key=lambda x: _deal_sort(x)):
        pct = _deal_pct(r.get("deal_tag"))
        table.add_row(
            r["model_id"],
            r.get("family") or "—",
            pct,
            _fmt_price(r.get("prompt_usd")),
            _fmt_price(r.get("completion_usd")),
            _fmt_price(r.get("cache_read_usd")),
            (r.get("deal_tag") or "").replace("🎁", ""),
        )
    return table


def print_deals(rows: list[dict]) -> None:
    console.print(render_deals(rows))


def _deal_sort(r: dict) -> tuple:
    """折扣力度大的排前面（deal_tag 形如 🎁65%off）。"""
    m = re.search(r"(\d+)%", r.get("deal_tag") or "")
    return (-(int(m.group(1)) if m else 0), r.get("model_id") or "")


def _deal_pct(tag: str | None) -> str:
    """从 deal_tag（🎁65%off）提取折扣百分比显示。"""
    if not tag:
        return "—"
    m = re.search(r"(\d+)%", tag)
    return f"{m.group(1)}% off" if m else tag


def dump_json(views: list[FamilyView]) -> str:
    """--json 纯输出：族 → 模型 → 各路线（纯文本标签，无 emoji）。"""
    data = []
    for fv in views:
        fam = {
            "family": fv.family,
            "family_label": fv.family_label,
            "models": [],
        }
        for mv in fv.models:
            routes = []
            for r in mv.routes:
                routes.append(
                    {
                        "provider": r.provider,
                        "provider_label": r.provider_label,
                        "model_id": r.model_id,
                        "route_type": r.route_type,
                        "prompt": r.prompt,
                        "completion": r.completion,
                        "cache_read": r.cache_read,
                        "cache_write": r.cache_write,
                        "tiered": r.tiered,
                        "is_offpeak": r.is_offpeak,
                        "discount_type": r.discount_type,
                        "quota": _quota_json(r),
                        "zdr": _zdr_json(r),
                        "deal_tag": r.deal_tag,
                        "tags": _plain_tags(r),
                    }
                )
            fam["models"].append({"model_id": mv.model_id, "routes": routes})
        data.append(fam)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _quota_json(r) -> dict | None:
    if not r.quota:
        return None
    return {
        "monthly_fee": r.quota.monthly_fee,
        "monthly_quota": r.quota.monthly_quota,
        "effective_multiplier": r.quota.effective_multiplier,
        "window": r.quota.window,
    }


def _zdr_json(r) -> dict | None:
    if not r.zdr:
        return None
    return {
        "used_for_training": r.zdr.used_for_training,
        "retention_days": r.zdr.retention_days,
        "is_zdr": r.zdr.is_zdr,
    }


def _plain_tags(r) -> list[str]:
    """终端/网页用 emoji 标签，JSON 输出替换为纯文本。"""
    tags = []
    if r.is_offpeak:
        tags.append("offpeak")
    if r.discount_type == "quota" and r.quota and r.quota.effective_multiplier:
        tags.append(f"quota_x{r.quota.effective_multiplier:g}")
    if r.deal_tag:
        tags.append("free" if "免费" in r.deal_tag else "promo")
    if r.zdr:
        tags.append("zdr" if r.zdr.is_zdr else f"retention_{r.zdr.retention_days}d")
    if r.tiered:
        tags.append("tiered")
    return tags

