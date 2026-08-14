"""Web 版（Flask）：浏览器查看模型×路线比价矩阵、涨跌情报、峰谷状态与 ZDR。

启动：tokenpage web [--host 127.0.0.1] [--port 8765] [--readonly]
100% 本地资源：无外部 CDN/字体，纯本地渲染。

安全（面向「发布到公网」的场景）：
- 只读模式：--readonly 或 TOKENPAGE_READONLY=1 时禁用 /api/fetch（访客绝不触发爬取）；
  监听非回环地址时默认启用只读（TOKENPAGE_READONLY=0 可显式关闭）
- Host 白名单：回环/内网地址 + TOKENPAGE_ALLOWED_HOSTS（公网域名），防 DNS Rebinding
- POST 校验 Sec-Fetch-Site / Origin，防跨站触发抓取（CSRF）
- CSP 等安全响应头：脚本仅限同源、禁内联脚本，配合前端转义防 XSS
"""

from __future__ import annotations

import ipaddress
import os
import threading
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request

from tokenpage import __version__
from tokenpage.config import ensure_config, load_fx, provider_labels, provider_meta
from tokenpage.fetchers.openrouter_discount import _is_in_go_list
from tokenpage.pricing import apply_offpeak_live, offpeak_status
from tokenpage.recommender import recommend
from tokenpage.storage import (
    get_meta,
    latest_deals,
    latest_fetched_at,
    latest_quotes,
    price_diffs,
    set_meta,
)
from tokenpage.sync import fetch_and_save

app = Flask(__name__)
# 只读模式：环境变量先行，CLI 可覆盖（见 cli.cmd_web）
app.config["READONLY"] = os.environ.get("TOKENPAGE_READONLY") == "1"

# 抓取冷却：默认 24 小时内不再全量爬取（返回缓存）
FETCH_COOLDOWN_SECONDS = 24 * 3600
# 强制刷新冷却：force=1 强刷后的最短间隔（防高频爬取被上游判定为攻击）
FORCE_COOLDOWN_SECONDS = 600

# 抓取串行锁：防止并发请求同时通过冷却检查（配合 meta 先占位）
_fetch_lock = threading.Lock()


def _fmt_price(v: float | None) -> float | None:
    return None if v is None else round(v, 6)


def _cooldown_remaining(last_iso: str | None, seconds: int) -> int:
    """返回距下次可执行（抓取/强刷）的剩余秒数；无记录或解析失败返回 0 = 可执行。"""
    if not last_iso:
        return 0
    try:
        last_dt = datetime.fromisoformat(last_iso)
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
        return max(0, int(seconds - elapsed))
    except ValueError:
        return 0


# ---------------- 请求防护（公网部署安全） ----------------


def _allowed_hosts() -> set[str]:
    """Host 白名单：回环 + 本机名 + TOKENPAGE_ALLOWED_HOSTS（逗号分隔，公网域名）。"""
    hosts = {"localhost", "127.0.0.1", "::1", "[::1]"}
    env = os.environ.get("TOKENPAGE_ALLOWED_HOSTS", "")
    hosts.update(h.strip().lower() for h in env.split(",") if h.strip())
    return hosts


def _is_private_hostname(hostname: str) -> bool:
    """内网 IP（RFC1918/回环/链路本地）放行，供 LAN 访问 --host 0.0.0.0 的场景。"""
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def _host_allowed(hostname: str) -> bool:
    if not hostname:
        return False
    return hostname in _allowed_hosts() or _is_private_hostname(hostname)


@app.before_request
def _guard_request():
    """Host 白名单（防 DNS Rebinding）+ POST 跨站校验（防 CSRF 触发抓取）。"""
    hostname = (urlsplit("//" + (request.host or "")).hostname or "").lower()
    if not _host_allowed(hostname):
        return jsonify({"ok": False, "error": "host_not_allowed"}), 403
    if request.method == "POST":
        site = request.headers.get("Sec-Fetch-Site")
        if site and site not in ("same-origin", "none"):
            return jsonify({"ok": False, "error": "cross_site_blocked"}), 403
        origin = request.headers.get("Origin")
        if origin:
            ohn = (urlsplit(origin).hostname or "").lower()
            if not _host_allowed(ohn):
                return jsonify({"ok": False, "error": "cross_origin_blocked"}), 403
    return None


@app.after_request
def _security_headers(resp):
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'self'",
    )
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    return resp


# ---------------- 数据序列化 ----------------


def _route_json(r) -> dict:
    return {
        "provider": r.provider,
        "provider_label": r.provider_label,
        "model_id": r.model_id,
        "route_type": r.route_type,
        "prompt": _fmt_price(r.prompt),
        "completion": _fmt_price(r.completion),
        "cache_read": _fmt_price(r.cache_read),
        "cache_write": _fmt_price(r.cache_write),
        "tiered": r.tiered,
        "is_offpeak": r.is_offpeak,
        "discount_type": r.discount_type,
        "quota": r.quota.__dict__ if r.quota else None,
        "zdr": r.zdr.__dict__ if r.zdr else None,
        "deal_tag": r.deal_tag,
        "tags": r.price_tags,
        "currency": r.raw_currency,
        "raw_prompt": _fmt_price(r.raw_prompt),
        "raw_completion": _fmt_price(r.raw_completion),
        "list_prompt": _fmt_price(r.list_prompt),
        "list_completion": _fmt_price(r.list_completion),
        "is_openrouter_deal": r.is_openrouter_deal,
        "source_url": r.source_url,
    }


def _matrix_json() -> list[dict]:
    rows = latest_quotes()
    views = recommend(rows)
    # 读取时按当前时刻实时应用峰谷（DeepSeek 官方价随峰/谷自动折算、排序）
    for fv in views:
        for mv in fv.models:
            for r in mv.routes:
                apply_offpeak_live(r)
    out = []
    for fv in views:
        out.append(
            {
                "family": fv.family,
                "family_label": fv.family_label,
                "models": [
                    {
                        "model_id": mv.model_id,
                        "family": fv.family,
                        "routes": [_route_json(r) for r in mv.routes],
                    }
                    for mv in fv.models
                ],
            }
        )
    return out


def _providers_status() -> dict:
    status: dict = {}
    for row in latest_quotes():
        prov = row["provider"]
        s = status.setdefault(
            prov,
            {
                "label": provider_labels().get(prov, prov),
                "count": 0,
                "families": set(),
            },
        )
        s["count"] += 1
        s["families"].add(row["family"])
    for s in status.values():
        s["families"] = sorted(s["families"])
    return status


def _rules_status() -> list[dict]:
    from tokenpage.config import load_rules

    rules = load_rules()
    now = datetime.now(timezone.utc)
    out = []
    for provider, rule in rules.items():
        off, _mult = offpeak_status(provider, now)
        out.append(
            {
                "provider": provider,
                "provider_label": provider_labels().get(provider, provider),
                "peak_hours_utc": rule.get("peak_hours_utc", []),
                "offpeak_multiplier": rule.get("offpeak_multiplier"),
                "note": rule.get("note"),
                "is_offpeak": off,
                "now_utc": now.strftime("%Y-%m-%d %H:%M"),
            }
        )
    return out


@app.get("/")
def index():
    return render_template("index.html", version=__version__)


@app.get("/api/overview")
def api_overview():
    ensure_config()
    fetched_at = latest_fetched_at()
    diffs = price_diffs()
    labels = provider_labels()
    for c in diffs.get("changes", []):
        c["provider_label"] = labels.get(c.get("provider"), c.get("provider"))
    # 冷却以 meta 记录为准（抓取前占位写入），老安装回退 prices 表时间
    last_fetch = get_meta("last_fetch_at") or fetched_at
    return jsonify(
        {
            "fetched_at": fetched_at,
            "has_data": fetched_at is not None,
            "readonly": bool(app.config.get("READONLY")),
            "fetch_cooldown_seconds": FETCH_COOLDOWN_SECONDS,
            "fetch_cooldown_remaining": _cooldown_remaining(
                last_fetch, FETCH_COOLDOWN_SECONDS
            ),
            "force_cooldown_seconds": FORCE_COOLDOWN_SECONDS,
            "force_cooldown_remaining": _cooldown_remaining(
                get_meta("last_force_fetch_at"), FORCE_COOLDOWN_SECONDS
            ),
            "fx": load_fx(),
            "provider_meta": provider_meta(),
            "providers": _providers_status(),
            "rules": _rules_status(),
            "matrix": _matrix_json(),
            "diffs": diffs,
            "deals": _deals_json(),
        }
    )


def _deals_json() -> list[dict]:
    rows = latest_deals()
    out = []
    for r in rows:
        # 只列「非 Go 清单」的折扣模型（Go 清单折扣已并入矩阵 openrouter 列）
        if _is_in_go_list(r.get("model_id")):
            continue
        out.append(
            {
                "model_id": r.get("model_id"),
                "family": r.get("family"),
                "prompt": _fmt_price(r.get("prompt_usd")),
                "completion": _fmt_price(r.get("completion_usd")),
                "cache_read": _fmt_price(r.get("cache_read_usd")),
                "deal_tag": r.get("deal_tag"),
            }
        )
    # 折扣大的排前面
    import re

    def _pct(x):
        m = re.search(r"(\d+)%", x.get("deal_tag") or "")
        return int(m.group(1)) if m else 0

    out.sort(key=_pct, reverse=True)
    return out


@app.post("/api/fetch")
def api_fetch():
    if app.config.get("READONLY"):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "readonly",
                    "message": "只读模式：访客不可触发抓取（公开部署防爬保护）",
                }
            ),
            403,
        )
    ensure_config()
    force = request.args.get("force") == "1"
    now_ts = datetime.now(timezone.utc).isoformat()

    if force:
        # 强刷冷却：锁内「检查 + 立即占位」，防止并发/竞态绕过冷却高频爬取
        with _fetch_lock:
            fr = _cooldown_remaining(get_meta("last_force_fetch_at"), FORCE_COOLDOWN_SECONDS)
            if fr > 0:
                return jsonify(
                    {
                        "ok": True,
                        "skipped": True,
                        "reason": "force_cooldown",
                        "force_cooldown_seconds": FORCE_COOLDOWN_SECONDS,
                        "force_cooldown_remaining": fr,
                        "fetched_at": latest_fetched_at(),
                        "counts": {},
                        "errors": {},
                        "saved": 0,
                    }
                )
            set_meta("last_force_fetch_at", now_ts)
    else:
        last = get_meta("last_fetch_at") or latest_fetched_at()
        cr = _cooldown_remaining(last, FETCH_COOLDOWN_SECONDS)
        if cr > 0:
            return jsonify(
                {
                    "ok": True,
                    "skipped": True,
                    "reason": "cooldown",
                    "cooldown_seconds": FETCH_COOLDOWN_SECONDS,
                    "cooldown_remaining": cr,
                    "fetched_at": latest_fetched_at(),
                    "counts": {},
                    "errors": {},
                    "saved": 0,
                }
            )

    summary = fetch_and_save()
    return jsonify(
        {
            "ok": True,
            "skipped": False,
            "counts": summary["counts"],
            "errors": summary["errors"],
            "saved": summary["saved"],
            "carried": summary["carried"],
            "fetched_at": latest_fetched_at(),
        }
    )
