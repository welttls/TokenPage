"""配置加载：~/.tokenpage/{models.json, rules.json, fx.json, go.json, official.json}。

- models.json：模型族标签 + 手动覆盖/追加（可空，模型清单默认跟随 OpenCode Go 页）
- rules.json ：峰谷规则（内置 DeepSeek 官方，用户可覆盖）
- fx.json    ：人民币兑美元汇率（SiliconFlow 比价换算）
- go.json    ：OpenCode Go 订阅配置（月费、额度、模型级额度倍率）
- official.json：官方 API 直连模型的 family 映射
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DATA_DIR = Path(os.environ.get("TOKENPAGE_HOME", Path.home() / ".tokenpage"))

# 轻量配置：模型族标签 + 跨站模型 ID 映射。
# 模型清单默认跟随 OpenCode Go 页面，这里补充标签与「逻辑模型 → 各站 ID」映射，
# 供 OpenRouter / 硅基流动抓取器定位目标模型。抓不到可容错跳过，用户可覆盖。
DEFAULT_MODELS: dict = {
    "families": {
        "claude": {"label": "Claude"},
        "kimi": {"label": "Kimi"},
        "glm": {"label": "GLM"},
        "gpt": {"label": "GPT"},
        "deepseek": {"label": "DeepSeek"},
        "qwen": {"label": "Qwen"},
        "grok": {"label": "Grok"},
        "minimax": {"label": "MiniMax"},
        "mimo": {"label": "MiMo"},
        "hy3": {"label": "Hy3"},
    },
    # 逻辑模型（Go 页清单）→ 各站 ID。family 必填；openrouter/siliconflow 可缺省。
    "models": {
        # DeepSeek V4 四个快照（OpenRouter 实体）显式带日期；latest 档带
        # go/zen 站 ID（Go/Zen 文档模型 ID 不带日期，需经 _logical_name 反查回退）
        "deepseek-v4-flash-0423": {
            "family": "deepseek",
            "openrouter": "deepseek/deepseek-v4-flash",
        },
        "deepseek-v4-flash-0731": {
            "family": "deepseek",
            "openrouter": "deepseek/deepseek-v4-flash-0731",
            "siliconflow": "deepseek-ai/DeepSeek-V4-Flash",
            "go": "deepseek-v4-flash",
            "zen": "deepseek-v4-flash",
        },
        "deepseek-v4-pro-0423": {
            "family": "deepseek",
            "openrouter": "deepseek/deepseek-v4-pro",
        },
        "deepseek-v4-pro-0813": {
            "family": "deepseek",
            "openrouter": "deepseek/deepseek-v4-pro-0813",
            "siliconflow": "deepseek-ai/DeepSeek-V4-Pro",
            "go": "deepseek-v4-pro",
            "zen": "deepseek-v4-pro",
        },
        "glm-5.3": {"family": "glm", "openrouter": "z-ai/glm-5.3", "siliconflow": "zai-org/GLM-5.3"},
        "glm-5.2": {"family": "glm", "openrouter": "z-ai/glm-5.2", "siliconflow": "zai-org/GLM-5.2"},
        "glm-5.1": {"family": "glm", "openrouter": "z-ai/glm-5.1", "siliconflow": "zai-org/GLM-5.1"},
        "kimi-k3": {"family": "kimi", "openrouter": "moonshotai/kimi-k3", "siliconflow": "moonshotai/Kimi-K3"},
        "kimi-k2.7-code": {"family": "kimi", "openrouter": "moonshotai/kimi-k2.7-code", "siliconflow": "moonshotai/Kimi-K2.7-Code"},
        "kimi-k2.6": {"family": "kimi", "openrouter": "moonshotai/kimi-k2.6", "siliconflow": "moonshotai/Kimi-K2.6"},
        "qwen3.8-max": {"family": "qwen", "openrouter": "qwen/qwen3.8-max"},
        "qwen3.8-27b": {"family": "qwen", "openrouter": "qwen/qwen3.8-27b"},
        "qwen3.7-max": {"family": "qwen", "openrouter": "qwen/qwen3.7-max"},
        "qwen3.7-plus": {"family": "qwen", "openrouter": "qwen/qwen3.7-plus"},
        "qwen3.6-plus": {"family": "qwen", "openrouter": "qwen/qwen3.6-plus"},
        "grok-4.5": {"family": "grok", "openrouter": "x-ai/grok-4.5"},
        "gpt-5.6-luna": {"family": "gpt", "openrouter": "openai/gpt-5.6-luna"},
        "minimax-m3": {"family": "minimax"},
        "minimax-m2.7": {"family": "minimax"},
        "mimo-v2.5": {"family": "mimo"},
        "mimo-v2.5-pro": {"family": "mimo"},
        "hy3": {"family": "hy3"},
        # Claude 补抓（OpenCode Zen / 官方 API）
        "claude-opus-5": {"family": "claude", "openrouter": "anthropic/claude-opus-5"},
        "claude-sonnet-5": {"family": "claude", "openrouter": "anthropic/claude-sonnet-5"},
        "claude-sonnet-4-6": {"family": "claude", "openrouter": "anthropic/claude-sonnet-4.6"},
        "claude-haiku-4-5": {"family": "claude", "openrouter": "anthropic/claude-haiku-4.5"},
    },
}

DEFAULT_RULES: dict = {
    "deepseek": {
        "peak_hours_utc": [["01:00", "04:00"], ["06:00", "10:00"]],
        "offpeak_multiplier": 0.5,
        "note": "DeepSeek 官方峰谷计价（2026-08-16 生效）：峰时 01:00-04:00 & 06:00-10:00 UTC，其余谷时半价",
        "effective_from": "2026-08-16T16:00:00Z",
    }
}

DEFAULT_FX: dict = {
    "CNY_per_USD": 7.2,
    "note": "人民币兑美元汇率，用于 SiliconFlow 比价换算，可自行调整",
}

# OpenCode Go 订阅配置（来源 docs/go 页，可被抓取结果覆盖）
DEFAULT_GO: dict = {
    "monthly_fee": 10.0,          # 月费 USD（首月 $5 可单独标注）
    "base_quota": 60.0,           # 基础月额度 USD（Go 给「6 倍于月费」的额度）
    "windows": {"5h": 12.0, "week": 30.0, "month": 60.0},
    "note": "OpenCode Go 订阅：$10/月 → $60 额度（6 倍基础），模型级额度见抓取结果",
    # 限时额度促销（营销页 opencode.ai/go 的「2x usage」徽标，docs 表不包含）
    # 自动抓取到会覆盖此处；抓不到则用本配置兜底。
    "promo": {
        "gpt-5.6-luna": {"multiplier": 2.0, "note": "限时 2x usage", "source_url": "https://opencode.ai/go"},
        "deepseek-v4-flash": {"multiplier": 2.0, "note": "限时 2x usage", "source_url": "https://opencode.ai/go"},
    },
}

# 官方 API 直连模型 → family 映射（official 抓取器使用；可手动覆盖）
DEFAULT_OFFICIAL: dict = {
    "deepseek": {
        "deepseek-v4-pro-0813": "deepseek",
        "deepseek-v4-flash-0731": "deepseek",
    },
    "anthropic": {
        "claude-opus-5": "claude",
        "claude-sonnet-5": "claude",
        "claude-sonnet-4-6": "claude",
        "claude-haiku-4-5": "claude",
    },
    "openai": {
        "gpt-5.6-sol": "gpt",
        "gpt-5.5": "gpt",
    },
    "xai": {
        "grok-4.6": "grok",
        "grok-4.5": "grok",
    },
    "moonshot": {
        "kimi-k3": "kimi",
        "kimi-k2.7-code": "kimi",
        "kimi-k2.6": "kimi",
    },
    "zhipu": {
        "glm-5.2": "glm",
        "glm-5.1": "glm",
        "glm-5.3": "glm",
    },
    "alibaba": {
        "qwen3.8-max": "qwen",
        "qwen3.7-max": "qwen",
        "qwen3.7-plus": "qwen",
    },
}

# 官方订阅套餐（coding plan）配置。
# 每个计划折算成「等效每 1M token 价」加进比价矩阵对应模型族下：
#   等效价(模型 M) = 官方 API 标价(M) ÷ 倍率，倍率 = 套餐月额度价值 ÷ 月费
# quota_type：
#   - "tokens"：明确的每月 token 额度（tokens_in/tokens_out）→ 按各模型官方价折算成价值
#   - "value" ：明确的每月额度价值（如 Qoder Credits × 单价）→ 直接作为价值
#   - "none"  ：无公开 token 额度（Claude/ChatGPT）→ 不折算数字，仅标 ♾️/宣称倍率
DEFAULT_PLANS: dict = {
    "anthropic_plan": {
        "label": "Claude 订阅",
        "label_en": "Claude Sub",
        "url": "https://www.anthropic.com/pricing",
        "currency": "USD",
        "family": "claude",
        "fee": 20.0,
        "quota_type": "value",
        "monthly_quota": 100.0,        # 估算：按官方「宣称 5×」折算 → 假设 $20 ≈ $100 云额度价值（×5）
        "estimate": True,              # 估算标记：标签/等效价加「估算」
        "tag": "宣称×5",               # 保留宣称口径，作为标签基础（显示为 宣称×5·估算）
        "models": ["claude-opus-5", "claude-sonnet-5", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "note": "Claude Pro $20/月：官方宣称「5× free 使用量」但未公布 token 额度 → 等效价按「宣称 5×」估算（假设 $20 ≈ $100 云额度价值，= 标价 ÷ 5），仅数量级参考。更高档：Max 5× $100、Max 20× $200。",
        "note_en": "Claude Pro $20/mo: officially '5× free usage' but no token quota published → equivalent price estimated by claimed 5× (assumes $20 ≈ $100 cloud value, = list ÷ 5), order-of-magnitude only. Higher tiers: Max 5× $100, Max 20× $200.",
    },
    "openai_plan": {
        "label": "ChatGPT 订阅",
        "label_en": "ChatGPT Sub",
        "url": "https://openai.com/chatgpt/pricing",
        "currency": "USD",
        "family": "gpt",
        "fee": 20.0,
        "quota_type": "none",
        "tag": "♾️扩展额度",
        "models": ["gpt-5.6-sol", "gpt-5.5"],
        "note": "ChatGPT Plus $20/月：官方仅称「更多使用额度」，未公布具体 token 额度，故不折算等效价。Pro $200/月为接近无限额度。",
        "note_en": "ChatGPT Plus $20/mo: officially 'more usage', no token quota published, so no equivalent price. Pro $200/mo is near-unlimited.",
    },
    "zhipu_plan": {
        "label": "GLM 订阅",
        "label_en": "GLM Sub",
        "url": "https://bigmodel.cn/glm-coding",
        "currency": "CNY",
        "family": "glm",
        "fee": 94.4,                       # Lite 连续包月价
        "quota_type": "tokens",
        "tokens_in": 250_000_000,          # 每月约 2.8 亿（每周 0.43~0.87 亿 × 4.33，取中值按 90/10 拆）
        "tokens_out": 30_000_000,
        "models": ["glm-5.3", "glm-5.2", "glm-5.1"],
        "note": "GLM Coding Plan Lite ¥94.4/月（连续包月）：每周 10,000 积分 → 约 0.43~0.87 亿 tokens/周（GLM-5.3，90.9% 缓存命中）。取区间中值折算，可按需在 plans.json 调整。更高档：Pro ¥538（6×）、Max ¥1078（14×）。",
        "note_en": "GLM Coding Plan Lite ¥94.4/mo: 10k credits/week → ~0.43-0.87×10⁸ tokens/wk (GLM-5.3, 90.9% cache hit). Mid-range estimate; adjust in plans.json. Higher: Pro ¥538 (6×), Max ¥1078 (14×).",
    },
    "alibaba_plan": {
        "label": "通义订阅",
        "label_en": "Qoder Sub",
        "url": "https://help.aliyun.com/zh/lingma/product-overview/billing-description",
        "currency": "CNY",
        "family": "qwen",
        "fee": 59.0,                        # 个人专业版 Pro
        "quota_type": "value",
        "monthly_quota": 80.0,             # 2,000 Credits × ¥0.04（资源包单价 ¥40/1,000）
        "models": ["qwen3.8-max", "qwen3.7-max", "qwen3.7-plus"],
        "note": "Qoder CN（通义灵码）个人专业版 ¥59/月：2,000 Credits/月，按资源包单价 ¥40/1,000 Credits 折算价值 ¥80。更高档：Pro+ ¥169（6,000 Credits）。",
        "note_en": "Qoder CN (Tongyi Lingma) Pro ¥59/mo: 2,000 credits/mo, valued ¥80 (resource pack ¥40/1,000 credits). Higher: Pro+ ¥169 (6,000 credits).",
    },
    "moonshot_plan": {
        "label": "Kimi 订阅",
        "label_en": "Kimi Sub",
        "url": "https://www.kimi.com/code",
        "currency": "CNY",
        "family": "kimi",
        "fee": 79.0,                        # Moderato 连续包月价
        "quota_type": "tokens",
        "tokens_in": 27_000_000,           # 估算值：官网未公布具体 token 数（仅称每周更新使用额度）
        "tokens_out": 3_000_000,
        "models": ["kimi-k3", "kimi-k2.7-code", "kimi-k2.6"],
        "note": "Kimi Code Plan Moderato ¥79/月：官网未公布具体 token 额度（仅称每周更新使用额度），此值按 K3 官方价折算的估算（约 10× 价值），请以 plans.json 为准调整。更高档：Allegretto ¥199（4×）、Allegro ¥699（10×）。",
        "note_en": "Kimi Code Plan Moderato ¥79/mo: no official token quota published (weekly refreshed usage); estimate (~10× value at K3 list prices) — adjust in plans.json. Higher: Allegretto ¥199 (4×), Allegro ¥699 (10×).",
    },
    "ollama_plan": {
        "label": "Ollama 云",
        "label_en": "Ollama Cloud",
        "url": "https://ollama.com/pricing",
        "currency": "USD",
        "family": "",                       # 跨厂商：模型各自带 family（见 models 内 dict 条目）
        "fee": 20.0,                        # Pro 月费；Max $100/月（新订阅暂停）
        "quota_type": "value",
        "monthly_quota": 60.0,              # 估算：假设 Pro $20 ≈ $60 云额度价值（≈3×；Ollama 未公布 token 额度）
        "estimate": True,                    # 估算标记：等效价/标签加「估算」
        "zdr": True,
        "models": [
            {"id": "glm-5.2", "family": "glm", "prompt": 0.49, "completion": 1.54},
            {"id": "glm-5.1", "family": "glm", "prompt": 0.966, "completion": 3.036},
            {"id": "deepseek-v4-flash-0731", "family": "deepseek", "prompt": 0.14, "completion": 0.28},
            {"id": "deepseek-v4-pro-0813", "family": "deepseek", "prompt": 0.435, "completion": 0.87},
            {"id": "kimi-k3", "family": "kimi", "prompt": 3.00, "completion": 15.00},
            {"id": "kimi-k2.7-code", "family": "kimi", "prompt": 0.71, "completion": 3.50},
            {"id": "kimi-k2.6", "family": "kimi", "prompt": 0.65, "completion": 3.41},
            {"id": "minimax-m2.7", "family": "minimax", "prompt": 0.30, "completion": 1.20},
            {"id": "minimax-m3", "family": "minimax", "prompt": 0.30, "completion": 1.20},
        ],
        "note": "Ollama Cloud 订阅：Pro $20/月（宣称 50× 免费）、Max $100/月（5× Pro，新订阅暂停）。Ollama 按模型「用量等级 1~4」计额度、未公布 token 数，故等效价为估算：假设 Pro ≈ $60 云额度价值（≈3×），标价取 OpenRouter 同模型价；重型模型实际额度更少，仅供参考，可在 plans.json 调整。ZDR：不记录、不训练。",
        "note_en": "Ollama Cloud sub: Pro $20/mo (claimed 50× Free), Max $100/mo (5× Pro, new subs paused). No token quota published (metered by model 'usage level 1-4') → equivalent price is an ESTIMATE: assumes Pro ≈ $60 cloud value (~3×), list prices from OpenRouter; heavy models get fewer tokens. Adjustable in plans.json. ZDR: no logging, no training.",
    },
}

# Web 用户偏好默认值（~/.tokenpage/user_prefs.json）。
# 与价格数据（SQLite）分离，落盘到本机文件——同一台机器的不同浏览器可共享；
# 前端仍以 localStorage 作离线/静态托管兜底。
DEFAULT_USER_PREFS: dict = {
    "lang": "zh",        # 界面语言（zh / en）
    "order": [],          # 模型族拖拽排序
    "pinned": [],         # 📌 置顶的模型族
    "collapsed": [],      # 折叠的模型族
    "alpha": 0,           # 字母排序：0 默认 / 1 A-Z / 2 Z-A
    "cny": False,         # 币种：False=美元主显 / True=人民币主显
}

def ensure_config() -> None:
    """首次运行时在 ~/.tokenpage 生成默认配置文件。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("models.json", DEFAULT_MODELS),
        ("rules.json", DEFAULT_RULES),
        ("fx.json", DEFAULT_FX),
        ("go.json", DEFAULT_GO),
        ("official.json", DEFAULT_OFFICIAL),
        ("plans.json", DEFAULT_PLANS),
    ):
        p = DATA_DIR / name
        if not p.exists():
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load(name: str, default: dict) -> dict:
    p = DATA_DIR / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        # 用户改配置写坏语法时明确提示，避免静默回退默认值难排查
        print(
            f"[tokenpage] 警告：{p} 解析失败（{e}），已回退内置默认值，请检查 JSON 语法",
            file=sys.stderr,
        )
        return default


def load_models() -> dict:
    return _load("models.json", DEFAULT_MODELS)


def load_rules() -> dict:
    return _load("rules.json", DEFAULT_RULES)


def load_fx() -> dict:
    return _load("fx.json", DEFAULT_FX)


def save_fx(fx: dict) -> None:
    """写回 fx.json（如每日自动抓取的汇率）。"""
    (DATA_DIR / "fx.json").write_text(
        json.dumps(fx, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_user_prefs() -> dict:
    """加载 Web 用户偏好（~/.tokenpage/user_prefs.json，缺失返回默认值）。"""
    return _load("user_prefs.json", DEFAULT_USER_PREFS)


def save_user_prefs(prefs: dict) -> None:
    """写回 Web 用户偏好（用户行为数据，非配置模板，仅在有改动时落盘）。"""
    (DATA_DIR / "user_prefs.json").write_text(
        json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_go() -> dict:
    """加载 OpenCode Go 订阅配置。"""
    return _load("go.json", DEFAULT_GO)


def load_official() -> dict:
    """加载官方 API 模型映射 {provider: {model_id: family}}。"""
    return _load("official.json", DEFAULT_OFFICIAL)


def load_plans() -> dict:
    """加载官方订阅套餐配置（coding plan，如 Claude/GLM/Kimi 订阅）。"""
    return _load("plans.json", DEFAULT_PLANS)


def official_meta_map() -> dict[str, dict[str, str]]:
    """返回 {provider: {model_id: family}}，仅保留有效条目。"""
    return load_official()


def provider_labels() -> dict[str, str]:
    return {
        "openrouter": "OpenRouter",
        "openrouter_deals": "OpenRouter 限时折扣",
        "siliconflow": "SiliconFlow",
        "opencode_go": "OpenCode Go",
        "opencode_zen": "OpenCode Zen",
        "deepseek": "DeepSeek官方",
        "official": "官方API",
        "anthropic": "Anthropic",
        "openai": "OpenAI",
        "xai": "xAI",
        "moonshot": "Moonshot",
        "zhipu": "智谱",
        "alibaba": "阿里云",
        "anthropic_plan": "Claude 订阅",
        "openai_plan": "ChatGPT 订阅",
        "zhipu_plan": "GLM 订阅",
        "alibaba_plan": "通义订阅",
        "moonshot_plan": "Kimi 订阅",
        "ollama_plan": "Ollama 云",
    }


def provider_meta() -> dict[str, dict]:
    """各路线/渠道的官网 URL 与说明（前端浮窗用）。"""
    return {
        "openrouter": {
            "url": "https://openrouter.ai/models",
            "note": "OpenRouter 聚合平台（按量付费）。公开 API 实时抓取；有限时折扣时本列显示折扣后价（原价见浮窗/划掉）。",
            "note_en": "OpenRouter aggregation (pay-as-you-go). Real-time from public API; when a limited-time deal is active this column shows the discounted price (original in tooltip / strikethrough).",
            "route_type": "metered",
        },
        "openrouter_deals": {
            "url": "https://openrouter.ai/models?discount=true",
            "note": "OpenRouter 限时折扣（前端端点抓取，折扣后价）。仅非 Go 清单的折扣模型在此展示。",
            "note_en": "OpenRouter limited-time deals (from frontend endpoint, discounted price). Only non-Go-list deal models are listed here.",
            "route_type": "metered",
        },
        "siliconflow": {
            "url": "https://siliconflow.cn/pricing",
            "note": "硅基流动（人民币计价，按 fx.json 汇率折算美元显示）。",
            "note_en": "SiliconFlow (CNY pricing, converted to USD using the fx.json rate).",
            "route_type": "metered",
        },
        "opencode_go": {
            "url": "https://opencode.ai/docs/zh-cn/go/",
            "note": "OpenCode Go 订阅：$10/月 → $60 基础额度（6 倍）。本列显示「额度折算后等效价」= 标价 ÷ 额度倍率；含限时 2x usage 促销。等效价按当月额度全量消耗计算（额度用不完实际更贵）。",
            "note_en": "OpenCode Go subscription: $10/mo → $60 base quota (6×). This column shows the quota-equivalent price = list price ÷ quota multiplier; includes limited-time 2x usage promos. Equivalent price assumes FULL monthly quota usage (if unused, the real cost is higher).",
            "route_type": "subscription",
        },
        "opencode_zen": {
            "url": "https://opencode.ai/docs/zh-cn/zen/",
            "note": "OpenCode Zen 按量付费网关（OpenCode 团队）。",
            "note_en": "OpenCode Zen pay-as-you-go gateway (OpenCode team).",
            "route_type": "metered",
        },
        "deepseek": {
            "url": "https://api-docs.deepseek.com/quick_start/pricing",
            "note": "DeepSeek 官方 API（峰谷计价：谷时半价）。",
            "note_en": "DeepSeek official API (off-peak pricing: half price off-peak).",
            "route_type": "official",
        },
        "anthropic": {
            "url": "https://docs.anthropic.com/en/docs/about-claude/pricing",
            "note": "Anthropic 官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "note_en": "Anthropic official API. Static base prices (not live-fetched); can be overridden in official.json.",
            "route_type": "official",
        },
        "openai": {
            "url": "https://developers.openai.com/api/docs/pricing",
            "note": "OpenAI 官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "note_en": "OpenAI official API. Static base prices (not live-fetched); can be overridden in official.json.",
            "route_type": "official",
        },
        "xai": {
            "url": "https://docs.x.ai/docs/models",
            "note": "xAI 官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "note_en": "xAI official API. Static base prices (not live-fetched); can be overridden in official.json.",
            "route_type": "official",
        },
        "moonshot": {
            "url": "https://platform.kimi.com/docs/pricing/chat-k3",
            "note": "Moonshot/Kimi 官方 API（人民币计价，双显示 ¥ / $）。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "note_en": "Moonshot/Kimi official API (CNY pricing, dual ¥/$ display). Static base prices (not live-fetched); can be overridden in official.json.",
            "route_type": "official",
        },
        "zhipu": {
            "url": "https://open.bigmodel.cn/pricing",
            "note": "智谱开放平台官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "note_en": "Zhipu official API. Static base prices (not live-fetched); can be overridden in official.json.",
            "route_type": "official",
        },
        "alibaba": {
            "url": "https://help.aliyun.com/zh/model-studio/pricing",
            "note": "阿里云百炼官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "note_en": "Alibaba Cloud Bailian official API. Static base prices (not live-fetched); can be overridden in official.json.",
            "route_type": "official",
        },
        "anthropic_plan": {
            "url": "https://www.anthropic.com/pricing",
            "note": "Claude 订阅：官方未公布 token 额度，等效价按「宣称 5×」估算（$20 ≈ $100 云额度价值 → 标价 ÷ 5），仅数量级参考（Claude Pro $20、Max $100/$200）。",
            "note_en": "Claude subscription: no token quota published; equivalent price estimated by claimed 5× ($20 ≈ $100 value → list ÷ 5), order-of-magnitude only (Pro $20, Max $100/$200).",
            "route_type": "subscription",
        },
        "openai_plan": {
            "url": "https://openai.com/chatgpt/pricing",
            "note": "ChatGPT 订阅：官方未公布 token 额度，不折算等效价（Plus $20、Pro $200 近无限）。",
            "note_en": "ChatGPT subscription: no token quota published, no equivalent price (Plus $20; Pro $200 near-unlimited).",
            "route_type": "subscription",
        },
        "zhipu_plan": {
            "url": "https://bigmodel.cn/glm-coding",
            "note": "GLM Coding Plan：有明确积分→token 额度，折算等效价 = 官方 API 标价 ÷ 倍率（Lite ¥94.4/月）。",
            "note_en": "GLM Coding Plan: explicit credit→token quota, equivalent = official API list ÷ multiplier (Lite ¥94.4/mo).",
            "route_type": "subscription",
        },
        "alibaba_plan": {
            "url": "https://help.aliyun.com/zh/lingma/product-overview/billing-description",
            "note": "Qoder CN（通义灵码）个人专业版：明确 Credits 额度，折算等效价 = 官方 API 标价 ÷ 倍率（¥59/月）。",
            "note_en": "Qoder CN (Tongyi Lingma) Pro: explicit Credits quota, equivalent = official API list ÷ multiplier (¥59/mo).",
            "route_type": "subscription",
        },
        "moonshot_plan": {
            "url": "https://www.kimi.com/code",
            "note": "Kimi Code Plan：有每周使用额度，折算等效价 = 官方 API 标价 ÷ 倍率（Moderato ¥79/月，估算）。",
            "note_en": "Kimi Code Plan: weekly refreshed usage quota, equivalent = official API list ÷ multiplier (Moderato ¥79/mo, estimate).",
            "route_type": "subscription",
        },
        "ollama_plan": {
            "url": "https://ollama.com/pricing",
            "note": "Ollama Cloud 订阅：Pro $20/月（宣称 50× 免费）、Max $100/月（5× Pro，新订阅暂停）。Ollama 未公布 token 额度（按模型用量等级 1~4 计），等效价为估算（假设 Pro ≈ $60 云额度价值 → 3×，标价取 OpenRouter）；ZDR（不记录、不训练）。",
            "note_en": "Ollama Cloud sub: Pro $20/mo (claimed 50× Free), Max $100/mo (5× Pro, new subs paused). No token quota published (usage level 1-4) → equivalent is an estimate (~$60 value → 3×, list from OpenRouter); ZDR (no logging, no training).",
            "route_type": "subscription",
        },
    }


def family_labels(models: dict | None = None) -> dict[str, str]:
    models = models or load_models()
    return {
        fam: famdata.get("label", fam)
        for fam, famdata in models.get("families", {}).items()
    }


def logical_models(models: dict | None = None) -> dict[str, dict]:
    """返回 {逻辑模型 ID: {family, openrouter?, siliconflow?}}。"""
    models = models or load_models()
    return models.get("models", {})


def station_meta_map(provider: str, models: dict | None = None) -> dict[str, tuple[str, str]]:
    """返回 {该站模型 ID: (逻辑模型, family)}，供抓取器定位目标模型。

    provider: 'openrouter' / 'siliconflow'
    """
    models = models or load_models()
    out: dict[str, tuple[str, str]] = {}
    for lm, meta in models.get("models", {}).items():
        sid = meta.get(provider)
        if sid:
            out[sid] = (lm, meta.get("family", ""))
    return out
