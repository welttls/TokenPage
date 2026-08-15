"""tokenpage doctor —— 环境与数据诊断（只读，不改配置/不写库）。

检查项：
  - SQLite 数据库完整性（PRAGMA integrity_check）+ 价格行数/批次/最近抓取
  - 各配置文件 JSON 语法（区分「未配置」与「语法错误」）
  - 上游可达性：OpenRouter API / SiliconFlow 定价页 / DeepSeek 官方
  - fx.json 汇率新鲜度（> 3 天未更新给出提醒）

用法：
  tokenpage doctor              # 全量检查（含网络）
  tokenpage doctor --no-network # 只做本地检查（SQLite / 配置 / 汇率）
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import requests

from tokenpage.config import DATA_DIR, load_fx
from tokenpage.storage import batch_fetched_ats, get_conn, latest_fetched_at

# 待校验的配置文件（缺失不报错——用内置默认；语法错误才报）
CONFIG_FILES = (
    "models.json",
    "rules.json",
    "fx.json",
    "go.json",
    "official.json",
    "plans.json",
)

# 汇率超过该天数未更新则提醒
FX_STALE_DAYS = 3

_HEADERS = {"User-Agent": "tokenpage/doctor (health check)"}


def _ok(msg: str) -> tuple[str, str]:
    return "ok", msg


def _fail(msg: str) -> tuple[str, str]:
    return "fail", msg


def _warn(msg: str) -> tuple[str, str]:
    return "warn", msg


def check_sqlite() -> tuple[str, str]:
    """SQLite 完整性 + 快照概览。"""
    try:
        conn = get_conn()
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            count = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
            batches = len(batch_fetched_ats())
            fetched = latest_fetched_at()
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 - 诊断要兜住一切异常
        return _fail(f"SQLite 异常：{type(e).__name__}: {e}")

    if integrity and integrity[0] != "ok":
        return _fail(f"SQLite integrity_check 失败：{integrity[0]}")
    detail = f"价格 {count} 行 / {batches} 批次"
    if fetched:
        detail += f"，最近抓取 {fetched[:19].replace('T', ' ')}"
    else:
        detail += "，尚无抓取（请先运行 tokenpage fetch）"
    return _ok(f"SQLite 数据库正常（{detail}）")


def check_config_files() -> list[tuple[str, str]]:
    """逐个校验配置 JSON 语法。"""
    results = []
    for name in CONFIG_FILES:
        p = DATA_DIR / name
        if not p.exists():
            results.append(_ok(f"{name} 未配置（用内置默认；tokenpage init 可生成）"))
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            results.append(_fail(f"{name} JSON 语法错误：{e}"))
            continue
        results.append(_ok(f"{name} 格式正确"))
    return results


def check_fx_freshness() -> tuple[str, str]:
    """fx.json 汇率新鲜度（每天 fetch 自动更新，>3 天提醒）。"""
    try:
        fx = load_fx()
    except Exception as e:  # noqa: BLE001
        return _fail(f"fx.json 读取失败：{e}")
    fetched_at = fx.get("fetched_at")
    cny = fx.get("CNY_per_USD")
    if not fetched_at:
        return _warn(
            "fx.json 无自动抓取时间戳（可能是手动维护的旧文件；每次 fetch 会自动更新）"
        )
    try:
        dt = datetime.fromisoformat(fetched_at)
    except ValueError:
        return _warn(f"fx.json fetched_at 无法解析：{fetched_at!r}")
    days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    rate = f"（CNY_per_USD={cny}）" if cny else ""
    if days > FX_STALE_DAYS:
        return _warn(
            f"fx.json 汇率 {days:.0f} 天未更新{rate}（建议超过 {FX_STALE_DAYS} 天重新 fetch）"
        )
    return _ok(f"fx.json 汇率 {days:.1f} 天前更新{rate}")


def _http_status(url: str, timeout: int = 15) -> tuple[int | None, str | None]:
    """GET 一个 URL，返回 (HTTP 状态码 或 None, 异常信息 或 None)。"""
    try:
        r = requests.get(url, timeout=timeout, headers=_HEADERS)
        return r.status_code, None
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def check_openrouter() -> tuple[str, str]:
    status, err = _http_status("https://openrouter.ai/api/v1/models")
    if status is not None and status < 500:
        return _ok(f"OpenRouter 可访问（HTTP {status}）")
    return _fail(f"OpenRouter 不可访问（HTTP {status or '—'}）{err or ''}".strip())


def check_siliconflow() -> tuple[str, str]:
    status, err = _http_status("https://siliconflow.cn/pricing")
    if status == 403:
        return _fail("SiliconFlow 抓取失败（HTTP 403，可能被限流，稍后再试）")
    if status is not None and status < 500:
        return _ok(f"SiliconFlow 可访问（HTTP {status}）")
    return _fail(f"SiliconFlow 不可访问（HTTP {status or '—'}）{err or ''}".strip())


def check_deepseek() -> tuple[str, str]:
    status, err = _http_status("https://api-docs.deepseek.com/quick_start/pricing")
    if status is not None and status < 500:
        return _ok(f"DeepSeek 官方正常（HTTP {status}）")
    return _fail(f"DeepSeek 官方不可访问（HTTP {status or '—'}）{err or ''}".strip())


def run(no_network: bool = False) -> int:
    """执行诊断并输出 ✓/✗/! 三态结果；返回退出码（有失败为 1）。"""
    from rich.console import Console

    console = Console()
    statuses: list[tuple[str, str]] = [
        check_sqlite(),
        *check_config_files(),
        check_fx_freshness(),
    ]
    if not no_network:
        statuses += [check_openrouter(), check_siliconflow(), check_deepseek()]

    exit_code = 0
    for st, msg in statuses:
        if st == "ok":
            console.print(f"[green]✓[/] {msg}")
        elif st == "fail":
            console.print(f"[red]✗[/] {msg}")
            exit_code = 1
        else:
            console.print(f"[yellow]![/] {msg}")
    return exit_code
