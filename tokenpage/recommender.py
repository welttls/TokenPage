"""推荐引擎：模型 × 路线 矩阵。

对每个模型（按 family 分组），列出它在各路线（OpenRouter / 硅基流动 /
OpenCode Go / OpenCode Zen / 官方直连）的报价，标注等效价与优惠标签。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tokenpage.config import family_labels, load_models, provider_labels, provider_meta
from tokenpage.models import QuotaInfo, ZdrInfo
from tokenpage.quota import effective_completion, effective_prompt

# 路线展示顺序（比价矩阵列顺序）
ROUTE_ORDER = ["opencode_go", "openrouter", "siliconflow", "opencode_zen", "official"]

# Claude 补抓模型（Go 无 Claude，来自 Zen / 官方）——与 opencode_zen 保持一致
CLAUDE_MODELS = {
    "claude-opus-5": "claude",
    "claude-sonnet-5": "claude",
    "claude-sonnet-4-6": "claude",
    "claude-haiku-4-5": "claude",
}


@dataclass
class RouteQuote:
    provider: str
    provider_label: str
    model_id: str
    route_type: str
    prompt: float | None            # 有效输入价
    completion: float | None        # 有效输出价
    cache_read: float | None = None
    cache_write: float | None = None
    tiered: bool | None = None
    is_offpeak: bool | None = None
    discount_type: str | None = None
    quota: QuotaInfo | None = None
    zdr: ZdrInfo | None = None
    deal_tag: str | None = None
    raw_currency: str = "USD"
    raw_prompt: float | None = None        # 原始币种标价（如 CNY）
    raw_completion: float | None = None
    list_prompt: float | None = None       # 折扣前原价（并入矩阵时划掉/浮窗用）
    list_completion: float | None = None
    is_openrouter_deal: bool = False       # 是否已并入的 OpenRouter 限时折扣
    source_url: str | None = None          # 该路线官网

    @property
    def price_tags(self) -> list[str]:
        tags: list[str] = []
        if self.is_offpeak:
            tags.append("🌙谷时")
        if self.discount_type == "quota" and self.quota:
            qtag = self.quota.tag
            if not qtag and self.quota.effective_multiplier:
                qtag = f"额度×{self.quota.effective_multiplier:g}"
            if qtag:
                tags.append(qtag)
        if self.deal_tag:
            tags.append(self.deal_tag)
        if self.zdr:
            tags.append(self.zdr.tag)
        if self.tiered:
            tags.append("阶梯")
        return tags


@dataclass
class ModelView:
    model_id: str            # 逻辑模型 ID
    family: str
    family_label: str
    routes: list[RouteQuote] = field(default_factory=list)

    @property
    def best(self) -> RouteQuote | None:
        """按有效输入价升序取最优路线（无价的排最后）。"""
        priced = [r for r in self.routes if r.prompt is not None]
        if not priced:
            return None
        return min(priced, key=lambda r: r.prompt)


@dataclass
class FamilyView:
    family: str
    family_label: str
    models: list[ModelView] = field(default_factory=list)


def _mk_quota(d: dict | None) -> QuotaInfo | None:
    if not d:
        return None
    return QuotaInfo(
        monthly_fee=d.get("monthly_fee"),
        monthly_quota=d.get("monthly_quota"),
        window=d.get("window"),
        note=d.get("note"),
        tag=d.get("tag"),
    )


def _mk_zdr(d: dict | None) -> ZdrInfo | None:
    if not d:
        return None
    return ZdrInfo(
        used_for_training=d.get("used_for_training"),
        retention_days=d.get("retention_days"),
        note=d.get("note"),
    )


def _to_route(row: dict) -> RouteQuote:
    quota = _mk_quota(row.get("quota"))
    zdr = _mk_zdr(row.get("zdr"))
    pseudo = _quote_like(row, quota)
    meta = provider_meta()
    return RouteQuote(
        provider=row["provider"],
        provider_label=provider_labels().get(row["provider"], row["provider"]),
        model_id=row["model_id"],
        route_type=row.get("route_type", "metered"),
        prompt=effective_prompt(pseudo),
        completion=effective_completion(pseudo),
        cache_read=row.get("cache_read_usd"),
        cache_write=row.get("cache_write_usd"),
        tiered=row.get("tiered"),
        is_offpeak=row.get("is_offpeak"),
        discount_type=row.get("discount_type"),
        quota=quota,
        zdr=zdr,
        deal_tag=row.get("deal_tag"),
        raw_currency=row.get("currency", "USD"),
        raw_prompt=row.get("raw_prompt"),
        raw_completion=row.get("raw_completion"),
        source_url=(meta.get(row["provider"]) or {}).get("url"),
    )


def _quote_like(row: dict, quota):
    """构造一个轻量对象，供 quota.effective_prompt/completion 计算。"""
    from types import SimpleNamespace

    return SimpleNamespace(
        prompt_usd_per_1m=row.get("prompt_usd"),
        completion_usd_per_1m=row.get("completion_usd"),
        route_type=row.get("route_type", "metered"),
        quota=quota,
    )


def recommend(rows: list[dict]) -> list[FamilyView]:
    """rows 为 storage.latest_quotes() 输出。

    按 family 分组 → 组内按模型 ID 分组 → 每个模型的各路线报价。
    OpenRouter 限时折扣：tracked 模型（Go 清单 + Claude）的折扣并入其
    openrouter 列；非 tracked 折扣行剔除出矩阵（只进「限时折扣」Tab）。
    """
    models_map = load_models()
    labels = family_labels(models_map)
    tracked_fam = _tracked_family_map(models_map)

    # family -> logical_model -> [routes]
    by_fam: dict[str, dict[str, list[RouteQuote]]] = {}
    deals: dict[str, RouteQuote] = {}  # 逻辑模型 -> 待并入的折扣路由
    for row in rows:
        if row["provider"] == "openrouter_deals":
            lm = _deal_logical(row, tracked_fam)
            if not lm:
                continue  # 非 tracked 模型：剔除矩阵，仅限时折扣 Tab 展示
            fam = tracked_fam.get(lm) or row.get("family") or "其他"
            deals[lm] = _to_route(row)
            by_fam.setdefault(fam, {}).setdefault(lm, [])
            continue
        fam = row.get("family") or "其他"
        lm = _logical_name(row, models_map)
        by_fam.setdefault(fam, {}).setdefault(lm, []).append(_to_route(row))

    out: list[FamilyView] = []
    for fam, models in by_fam.items():
        mv_list: list[ModelView] = []
        for lm, routes in models.items():
            deal = deals.pop(lm, None)
            if deal:
                _merge_deal_into_openrouter(routes, deal)
            routes.sort(key=lambda r: ROUTE_ORDER.index(r.provider) if r.provider in ROUTE_ORDER else 99)
            mv_list.append(
                ModelView(model_id=lm, family=fam, family_label=labels.get(fam, fam), routes=routes)
            )
        mv_list.sort(key=lambda mv: mv.model_id)
        out.append(FamilyView(family=fam, family_label=labels.get(fam, fam), models=mv_list))

    order = {"claude": 0, "kimi": 1, "glm": 2, "grok": 3, "gpt": 4, "deepseek": 5, "qwen": 6}
    out.sort(key=lambda f: (order.get(f.family, 99), f.family_label))
    return out


def _tracked_family_map(models_map: dict) -> dict[str, str]:
    """返回 {逻辑模型ID: family}：Go 清单 + Claude 补抓模型。"""
    out: dict[str, str] = {}
    for lm, meta in (models_map.get("models") or {}).items():
        out[lm] = meta.get("family", "")
    for cid, fam in CLAUDE_MODELS.items():
        out[cid] = fam
    return out


def _deal_logical(row: dict, tracked_fam: dict) -> str | None:
    """把 openrouter_deals 的 slug 归一化为逻辑模型名（仅 tracked）。

    严格按「斜杠后段 == 逻辑模型 ID」精确匹配，避免 glm-5→glm-5.3、
    hy3-preview→hy3 这类子串误配；同时兼容带日期后缀的 OpenRouter slug
    （如 deepseek-v4-pro-20260813 通过 models.json 的 openrouter 映射回退）。
    匹配不到（非 Go/Claude 清单）返回 None。
    """
    slug = row.get("model_id") or ""
    base = slug.split("/")[-1].lower()
    if base in tracked_fam:
        return base
    # 带日期后缀的 slug：按 models.json openrouter 字段反查
    for lm, meta in (load_models().get("models") or {}).items():
        if meta.get("openrouter") == slug and lm in tracked_fam:
            return lm
    return None


def _merge_deal_into_openrouter(routes: list[RouteQuote], deal: RouteQuote) -> None:
    """把限时折扣并入该模型的 openrouter 列（有折扣放折扣）。

    - 有 openrouter 列表价：折扣后价覆盖，原价存 list_prompt/completion。
    - 无列表价：把折扣路由伪装成 openrouter 展示，原价取 raw_*。
    """
    or_idx = next((i for i, r in enumerate(routes) if r.provider == "openrouter"), None)
    if or_idx is not None:
        or_r = routes[or_idx]
        or_r.list_prompt = or_r.prompt
        or_r.list_completion = or_r.completion
        or_r.prompt = deal.prompt
        or_r.completion = deal.completion
        if deal.cache_read is not None:
            or_r.cache_read = deal.cache_read
        or_r.deal_tag = deal.deal_tag
        or_r.discount_type = "promo"
        or_r.is_openrouter_deal = True
        return
    # 无列表价路由：折扣本身作为 OpenRouter 报价展示
    deal.provider = "openrouter"
    deal.provider_label = provider_labels().get("openrouter", "OpenRouter")
    deal.list_prompt = deal.raw_prompt or deal.prompt
    deal.list_completion = deal.raw_completion or deal.completion
    deal.is_openrouter_deal = True
    deal.source_url = (provider_meta().get("openrouter") or {}).get("url")
    routes.append(deal)


def _logical_name(row: dict, models_map: dict) -> str:
    """把各站的模型 ID 归一化为逻辑模型名。

    若该站模型 ID 在 config.models 映射中存在，用逻辑名；否则用模型 ID 本身。
    """
    station_map = models_map.get("models", {})
    # 反向：station_id -> logical
    reverse = {}
    for lm, meta in station_map.items():
        for provider in ("openrouter", "siliconflow"):
            sid = meta.get(provider)
            if sid:
                reverse[sid] = lm
    provider = row["provider"]
    mid = row["model_id"]
    # opencode_go / opencode_zen / official 用模型 ID 本身就是逻辑名
    if provider in ("opencode_go", "opencode_zen", "official") or mid in station_map:
        return mid
    return reverse.get(mid, mid)
