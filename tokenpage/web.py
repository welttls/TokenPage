"""Web 版（Flask）：浏览器查看模型×路线比价矩阵、涨跌情报、峰谷状态与 ZDR。

启动：tokenpage web [--host 127.0.0.1] [--port 8765]
100% 本地：不依赖任何外部 CDN，纯本地渲染。
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from tokenpage import __version__
from tokenpage.config import ensure_config, load_fx, provider_labels, provider_meta
from tokenpage.fetchers import fetch_all
from tokenpage.fetchers.openrouter_discount import _is_in_go_list
from tokenpage.pricing import apply_offpeak, offpeak_status
from tokenpage.recommender import recommend
from tokenpage.storage import (
    latest_deals,
    latest_fetched_at,
    latest_quotes,
    price_diffs,
    save_quotes,
)

app = Flask(__name__)

# 抓取冷却：默认 24 小时内不再全量爬取（返回缓存）
FETCH_COOLDOWN_SECONDS = 24 * 3600


def _fmt_price(v: float | None) -> float | None:
    return None if v is None else round(v, 4)


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
    out = []
    for fv in views:
        out.append(
            {
                "family": fv.family,
                "family_label": fv.family_label,
                "models": [
                    {"model_id": mv.model_id, "routes": [_route_json(r) for r in mv.routes]}
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
    return jsonify(
        {
            "fetched_at": fetched_at,
            "has_data": fetched_at is not None,
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
    ensure_config()
    force = request.args.get("force") == "1"
    last = latest_fetched_at()
    # 冷却：默认 24h 内不重复全量爬取（除非 force=1）
    if last and not force:
        try:
            last_dt = datetime.fromisoformat(last)
            if (datetime.now(timezone.utc) - last_dt).total_seconds() < FETCH_COOLDOWN_SECONDS:
                return jsonify(
                    {
                        "ok": True,
                        "skipped": True,
                        "reason": "cooldown",
                        "cooldown_seconds": FETCH_COOLDOWN_SECONDS,
                        "fetched_at": last,
                        "counts": {},
                        "errors": {},
                        "saved": 0,
                    }
                )
        except ValueError:
            pass

    results, errors = fetch_all()
    batch_ts = datetime.now(timezone.utc).isoformat()
    quotes = []
    for provider, qs in results.items():
        for q in qs:
            q.fetched_at = batch_ts
            apply_offpeak(q)
            quotes.append(q)
    if quotes:
        save_quotes(quotes)
    return jsonify(
        {
            "ok": True,
            "skipped": False,
            "counts": {provider: len(qs) for provider, qs in results.items()},
            "errors": errors,
            "saved": len(quotes),
            "fetched_at": latest_fetched_at(),
        }
    )
