"""CLI 入口：tokenpage 子命令。

    tokenpage init    —— 生成 ~/.tokenpage 默认配置
    tokenpage fetch   —— 抓取各路线的模型价格并入库（只留两天）
    tokenpage show    —— 模型 × 路线 比价矩阵（--json 纯输出）
    tokenpage deals   —— 查看 OpenRouter 限时折扣（--json 纯输出）
    tokenpage diff    —— 对比最近两次抓取，标记降价/涨价/新上架/下架
    tokenpage rules   —— 查看峰谷规则与当前谷/峰状态
    tokenpage doctor  —— 环境与数据诊断（SQLite/配置/上游可达性/汇率新鲜度）
    tokenpage web     —— 启动本地 Web 版界面
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from rich.console import Console

from tokenpage import __version__
from tokenpage.config import DATA_DIR, ensure_config, load_rules, provider_labels
from tokenpage.output import console, dump_json, print_deals, print_matrix
from tokenpage.pricing import apply_offpeak_live, offpeak_status
from tokenpage.recommender import recommend
from tokenpage.storage import (
    latest_deals,
    latest_fetched_at,
    latest_quotes,
    price_diffs,
)
from tokenpage.sync import fetch_and_save


def cmd_init(_args) -> int:
    ensure_config()
    console.print(f"[green]✓[/] 默认配置已生成于 {DATA_DIR}")
    return 0


def cmd_fetch(_args) -> int:
    ensure_config()
    console.print("抓取中…（OpenRouter / 硅基流动 / OpenCode Go / OpenCode Zen / 官方）")
    summary = fetch_and_save()

    for provider, n in summary["counts"].items():
        console.print(f"  [cyan]{provider_labels().get(provider, provider)}[/]: {n} 条")
    if summary["carried"]:
        console.print(
            f"  [yellow]⚠ {summary['carried']} 条沿用上一批快照（本次抓取失败的站）[/]"
        )
    errors = summary["errors"]
    if errors:
        for provider, msg in errors.items():
            console.print(f"  [yellow]⚠ {provider_labels().get(provider, provider)} 抓取失败[/]: {msg}")

    if not summary["saved"]:
        console.print("[red]✗ 没有抓到任何价格，请检查网络或配置。[/]")
        return 1

    console.print(f"[green]✓[/] 已入库 {summary['saved']} 条价格快照（仅保留最近 2 天）")
    return 0


def _rows() -> list[dict]:
    rows = latest_quotes()
    if not rows:
        console.print("[red]数据库为空，请先运行 tokenpage fetch。[/]")
        sys.exit(1)
    return rows


def cmd_show(args) -> int:
    rows = _rows()
    views = recommend(rows)
    # 展示时按当前时刻实时应用峰谷
    for fv in views:
        for mv in fv.models:
            for r in mv.routes:
                apply_offpeak_live(r)
    if args.json:
        # Windows GBK 终端下强制 UTF-8 输出，避免中文/emoji 编码错误
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(dump_json(views))
    else:
        print_matrix(views, fetched_at=latest_fetched_at())
    return 0


def _pf(v) -> str:
    if v is None:
        return "—"
    return f"${v:g}"


def cmd_diff(_args) -> int:
    diff = price_diffs()
    # 首用体验：区分「空库」与「只抓过一次」
    if diff["current"] is None:
        console.print("[red]数据库为空，请先运行 tokenpage fetch。[/]")
        return 0
    if not diff["previous"]:
        console.print("这是第一次抓取，尚无历史数据对比。明天再跑 diff 就能看到涨跌了。")
        return 0
    if not diff["changes"]:
        console.print(f"[bold cyan]涨跌情报[/]（对比 {diff['previous']} → {diff['current']}）")
        console.print("  本次抓取与上次相比没有价格变化。")
        return 0
    console.print(f"[bold cyan]涨跌情报[/]（对比 {diff['previous']} → {diff['current']}）")
    s = diff["summaries"]
    console.print(
        f"  [green]↓ 降价 {s['down']}[/]  [red]↑ 涨价 {s['up']}[/]  "
        f"[magenta]🆕 新上架 {s['new']}[/]  [dim]❌ 下架 {s['gone']}[/]"
    )
    for c in diff["changes"]:
        prov = provider_labels().get(c["provider"], c["provider"])
        if c["action"] == "down":
            mark, style = "↓", "green"
        elif c["action"] == "up":
            mark, style = "↑", "red"
        elif c["action"] == "new":
            mark, style = "🆕", "magenta"
        else:
            mark, style = "❌", "dim"
        console.print(
            f"  [{style}]{mark}[/] {c['family'] or ''} {c['model_id']} "
            f"[dim]({prov})[/] 输入 {_pf(c['prompt_from'])}→{_pf(c['prompt_to'])}  "
            f"输出 {_pf(c['completion_from'])}→{_pf(c['completion_to'])}"
        )
    return 0


def cmd_deals(args) -> int:
    rows = latest_deals()
    if not rows:
        console.print("[red]暂无折扣数据，请先运行 tokenpage fetch。[/]")
        return 0
    if args.json:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        import json as _json

        print(
            _json.dumps(
                [
                    {
                        "model_id": r["model_id"],
                        "family": r.get("family"),
                        "prompt_usd_per_1m": r.get("prompt_usd"),
                        "completion_usd_per_1m": r.get("completion_usd"),
                        "cache_read_usd_per_1m": r.get("cache_read_usd"),
                        "deal_tag": r.get("deal_tag"),
                    }
                    for r in rows
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_deals(rows)
    return 0


def cmd_rules(_args) -> int:
    ensure_config()
    rules = load_rules()
    if not rules:
        console.print("暂无峰谷规则。")
        return 0
    now = datetime.now(timezone.utc)
    console.print(f"当前时间（UTC）：{now.strftime('%Y-%m-%d %H:%M')}\n")
    for provider, rule in rules.items():
        label = provider_labels().get(provider, provider)
        console.print(f"[bold]{label}[/]")
        console.print(f"  峰时(UTC)：{'、'.join(f'{s}-{e}' for s, e in rule.get('peak_hours_utc', [])) or '—'}")
        console.print(f"  谷时折扣：{float(rule.get('offpeak_multiplier', 1.0)):.0%}")
        if note := rule.get("note"):
            console.print(f"  说明：{note}")
        off, mult = offpeak_status(provider, now)
        status = "🌙 谷时（当前折扣生效）" if off else ("☀️ 峰时（原价）" if off is False else "—")
        console.print(f"  当前：{status}\n")
    return 0


def cmd_doctor(args) -> int:
    """运行环境与数据诊断（只读，不写库/不改配置）。"""
    from tokenpage.doctor import run as doctor_run

    return doctor_run(no_network=args.no_network)


def cmd_web(args) -> int:
    """启动 Web 版界面。Flask 延迟导入，避免缺依赖时拖垮其他命令。"""
    ensure_config()
    try:
        from tokenpage.web import app
    except ImportError:
        console.print("[red]缺少 Flask，请先安装：pip install flask[/]")
        return 1
    # 只读模式（公开部署防爬保护）：
    # - --readonly / TOKENPAGE_READONLY=1 显式开启
    # - 监听非回环地址时默认开启（TOKENPAGE_READONLY=0 显式关闭）
    readonly = bool(args.readonly) or os.environ.get("TOKENPAGE_READONLY") == "1"
    loopback = args.host in ("127.0.0.1", "localhost", "::1")
    if not readonly and not loopback and os.environ.get("TOKENPAGE_READONLY") != "0":
        readonly = True
        console.print(
            "[yellow]⚠ 监听非回环地址，已默认启用只读模式（禁用 /api/fetch，访客不触发爬取）。[/]\n"
            "  公网部署请设置 TOKENPAGE_ALLOWED_HOSTS=你的域名；确需服务端开放抓取设 TOKENPAGE_READONLY=0。"
        )
    app.config["READONLY"] = readonly
    mode = "只读模式" if readonly else "可抓取"
    console.print(
        f"[green]Token黄页 Web 版[/] 已启动：http://{args.host}:{args.port}  （{mode}，Ctrl+C 停止）"
    )
    app.run(host=args.host, port=args.port, debug=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokenpage",
        description="Token黄页 — 主流模型价格优惠情报（桌宠式比价工具）",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="生成默认配置文件")
    sub.add_parser("fetch", help="抓取各路线的模型价格并写入 SQLite")
    p_show = sub.add_parser("show", help="展示模型×路线比价矩阵")
    p_show.add_argument("--json", action="store_true", help="纯 JSON 输出")
    p_deals = sub.add_parser("deals", help="查看 OpenRouter 限时折扣")
    p_deals.add_argument("--json", action="store_true", help="纯 JSON 输出")
    sub.add_parser("diff", help="对比最近两次抓取的涨跌")
    sub.add_parser("rules", help="查看峰谷规则与当前状态")
    p_doctor = sub.add_parser(
        "doctor", help="环境与数据诊断（SQLite/配置/上游可达性/汇率新鲜度）"
    )
    p_doctor.add_argument(
        "--no-network", action="store_true", help="跳过网络检查（只做本地检查）"
    )
    p_web = sub.add_parser("web", help="启动 Web 版界面（浏览器查看）")
    p_web.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    p_web.add_argument("--port", type=int, default=8765, help="监听端口（默认 8765）")
    p_web.add_argument(
        "--readonly",
        action="store_true",
        help="只读模式：禁用 /api/fetch（公开部署时访客绝不触发爬取）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "init": cmd_init,
        "fetch": cmd_fetch,
        "show": cmd_show,
        "deals": cmd_deals,
        "diff": cmd_diff,
        "rules": cmd_rules,
        "doctor": cmd_doctor,
        "web": cmd_web,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
