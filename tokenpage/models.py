"""核心数据结构。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# 路线类型：聚合站按量 / 订阅折算 / 官方 API 直连
ROUTE_METERED = "metered"
ROUTE_SUBSCRIPTION = "subscription"
ROUTE_OFFICIAL = "official"
ROUTE_TYPES = (ROUTE_METERED, ROUTE_SUBSCRIPTION, ROUTE_OFFICIAL)

# 折扣/优惠类型
DISCOUNT_OFFPEAK = "offpeak"   # 峰谷折扣
DISCOUNT_QUOTA = "quota"       # 订阅额度折算
DISCOUNT_FREE = "free"         # 限免
DISCOUNT_PROMO = "promo"       # 促销
DISCOUNT_TYPES = (DISCOUNT_OFFPEAK, DISCOUNT_QUOTA, DISCOUNT_FREE, DISCOUNT_PROMO)


@dataclass
class ZdrInfo:
    """ZDR（零数据保留）信息：是否用于训练 + 数据保留天数。0 天 = ZDR。"""

    used_for_training: bool | None = None  # True=用于训练 / False=不使用 / None=未声明
    retention_days: int | None = None      # 数据保留天数（0=ZDR / None=未声明）
    note: str | None = None                # 备注（如「ZDR 协议每月续签」）

    @property
    def is_zdr(self) -> bool:
        return self.retention_days == 0

    @property
    def tag(self) -> str:
        """终端/展示用短标签。"""
        if self.is_zdr:
            return "🔒ZDR"
        if self.retention_days is not None:
            return f"{self.retention_days}d"
        return "—"


@dataclass
class QuotaInfo:
    """订阅额度信息（subscription 路线）。

    用于把「固定月费 + 模型额度」折算成等效每 1M token 价：
        等效价 = 标价 × (订阅月费 ÷ 该模型月额度)
    """

    monthly_fee: float | None = None    # 订阅月费（USD）
    monthly_quota: float | None = None  # 该模型每月使用额度（USD 价值）
    window: str | None = None           # 额度窗口描述（如「5h/周/月」）
    note: str | None = None
    tag: str | None = None              # 自定义显示标签（如「额度×6·限时×2」），默认 None 自动生成

    @property
    def effective_multiplier(self) -> float | None:
        """等效折扣倍率（>1 表示划算）。如 $10/$60 → 6 倍。"""
        if not self.monthly_fee or not self.monthly_quota:
            return None
        return self.monthly_quota / self.monthly_fee


@dataclass
class PriceQuote:
    """一条模型价格快照（某路线 × 某模型）。

    prompt_usd_per_1m / completion_usd_per_1m 存「标价」（美元 / 1M tokens）。
    若当前处于谷时且该 provider 有峰谷规则，会乘以 offpeak_multiplier 存入有效价。
    订阅路线额外带 quota 折算倍率。
    """

    provider: str                # openrouter / siliconflow / opencode_go / opencode_zen / deepseek / moonshot / zhipu / xai / openai / anthropic / alibaba
    provider_label: str          # 展示名
    model_id: str                # 该路线模型 ID
    route_type: str = ROUTE_METERED  # metered / subscription / official
    family: str = ""             # claude / kimi / glm / gpt / deepseek / qwen / minimax / mimo / hy3 ...
    tier: str = ""               # 最新 / 次新 等档位（可选）
    prompt_usd_per_1m: float | None = None
    completion_usd_per_1m: float | None = None
    cache_read_usd_per_1m: float | None = None   # 缓存命中输入价
    cache_write_usd_per_1m: float | None = None  # 缓存命中输出价（部分站支持）
    tiered: bool | None = None                   # 是否有阶梯价格（如 >200K 翻倍）
    context_length: int | None = None
    supports_tools: bool | None = None
    currency: str = "USD"
    raw_prompt: float | None = None          # 原始币种价（/1M）
    raw_completion: float | None = None
    offpeak_multiplier: float | None = None  # 谷时折扣倍率（None=无折扣）
    is_offpeak: bool | None = None           # 当前是否谷时
    discount_type: str | None = None         # 折扣类型（offpeak/quota/free/promo）
    quota: QuotaInfo | None = None           # 订阅额度信息（subscription 路线）
    zdr: ZdrInfo | None = None               # ZDR 信息
    deal_tag: str | None = None              # 白嫖/限免/促销标签（如「🆓限免」「🎁促销」）
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def offpeak_tag(self) -> str:
        """终端展示用峰谷标记。"""
        if self.is_offpeak:
            return "🌙谷时"
        if self.offpeak_multiplier is not None or self.is_offpeak is False:
            return "☀️峰时"
        return "—"

    @property
    def discount_tags(self) -> list[str]:
        """聚合所有折扣/优惠标签。"""
        tags: list[str] = []
        if self.is_offpeak:
            tags.append("🌙谷时")
        if self.quota and self.quota.effective_multiplier:
            tags.append(f"额度×{self.quota.effective_multiplier:g}")
        if self.deal_tag:
            tags.append(self.deal_tag)
        if self.zdr and self.zdr.tag and self.zdr.tag != "—":
            tags.append(self.zdr.tag)
        return tags

    @property
    def effective_prompt(self) -> float | None:
        """应用峰谷后的有效输入价。"""
        if self.prompt_usd_per_1m is None:
            return None
        return self.prompt_usd_per_1m

    @property
    def effective_completion(self) -> float | None:
        """应用峰谷后的有效输出价。"""
        if self.completion_usd_per_1m is None:
            return None
        return self.completion_usd_per_1m
