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
        "deepseek-v4-flash": {
            "family": "deepseek",
            "openrouter": "deepseek/deepseek-v4-flash-0731",
            "siliconflow": "deepseek-ai/DeepSeek-V4-Flash",
        },
        "deepseek-v4-pro": {
            "family": "deepseek",
            "openrouter": "deepseek/deepseek-v4-pro-20260813",
            "siliconflow": "deepseek-ai/DeepSeek-V4-Pro",
        },
        "glm-5.3": {"family": "glm", "openrouter": "z-ai/glm-5.3", "siliconflow": "zai-org/GLM-5.3"},
        "glm-5.2": {"family": "glm", "openrouter": "z-ai/glm-5.2", "siliconflow": "zai-org/GLM-5.2"},
        "glm-5.1": {"family": "glm", "openrouter": "z-ai/glm-5.1", "siliconflow": "zai-org/GLM-5.1"},
        "kimi-k3": {"family": "kimi", "openrouter": "moonshotai/kimi-k3", "siliconflow": "moonshotai/Kimi-K3"},
        "kimi-k2.7-code": {"family": "kimi", "openrouter": "moonshotai/kimi-k2.7-code", "siliconflow": "moonshotai/Kimi-K2.7-Code"},
        "kimi-k2.6": {"family": "kimi", "openrouter": "moonshotai/kimi-k2.6", "siliconflow": "moonshotai/Kimi-K2.6"},
        "qwen3.8-max": {"family": "qwen", "openrouter": "qwen/qwen3.8-max"},
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
        "deepseek-v4-pro": "deepseek",
        "deepseek-v4-flash": "deepseek",
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


def ensure_config() -> None:
    """首次运行时在 ~/.tokenpage 生成默认配置文件。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("models.json", DEFAULT_MODELS),
        ("rules.json", DEFAULT_RULES),
        ("fx.json", DEFAULT_FX),
        ("go.json", DEFAULT_GO),
        ("official.json", DEFAULT_OFFICIAL),
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


def load_go() -> dict:
    """加载 OpenCode Go 订阅配置。"""
    return _load("go.json", DEFAULT_GO)


def load_official() -> dict:
    """加载官方 API 模型映射 {provider: {model_id: family}}。"""
    return _load("official.json", DEFAULT_OFFICIAL)


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
    }


def provider_meta() -> dict[str, dict]:
    """各路线/渠道的官网 URL 与说明（前端浮窗用）。"""
    return {
        "openrouter": {
            "url": "https://openrouter.ai/models",
            "note": "OpenRouter 聚合平台（按量付费）。公开 API 实时抓取；有限时折扣时本列显示折扣后价（原价见浮窗/划掉）。",
            "route_type": "metered",
        },
        "openrouter_deals": {
            "url": "https://openrouter.ai/models?discount=true",
            "note": "OpenRouter 限时折扣（前端端点抓取，折扣后价）。仅非 Go 清单的折扣模型在此展示。",
            "route_type": "metered",
        },
        "siliconflow": {
            "url": "https://siliconflow.cn/pricing",
            "note": "硅基流动（人民币计价，按 fx.json 汇率折算美元显示）。",
            "route_type": "metered",
        },
        "opencode_go": {
            "url": "https://opencode.ai/docs/zh-cn/go/",
            "note": "OpenCode Go 订阅：$10/月 → $60 基础额度（6 倍）。本列显示「额度折算后等效价」= 标价 ÷ 额度倍率；含限时 2x usage 促销。",
            "route_type": "subscription",
        },
        "opencode_zen": {
            "url": "https://opencode.ai/docs/zh-cn/zen/",
            "note": "OpenCode Zen 按量付费网关（OpenCode 团队）。",
            "route_type": "metered",
        },
        "deepseek": {
            "url": "https://api-docs.deepseek.com/quick_start/pricing",
            "note": "DeepSeek 官方 API（峰谷计价：谷时半价）。",
            "route_type": "official",
        },
        "anthropic": {
            "url": "https://docs.anthropic.com/en/docs/about-claude/pricing",
            "note": "Anthropic 官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "route_type": "official",
        },
        "openai": {
            "url": "https://developers.openai.com/api/docs/pricing",
            "note": "OpenAI 官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "route_type": "official",
        },
        "xai": {
            "url": "https://docs.x.ai/docs/models",
            "note": "xAI 官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "route_type": "official",
        },
        "moonshot": {
            "url": "https://platform.kimi.com/docs/pricing/chat-k3",
            "note": "Moonshot/Kimi 官方 API（人民币计价，双显示 ¥ / $）。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "route_type": "official",
        },
        "zhipu": {
            "url": "https://open.bigmodel.cn/pricing",
            "note": "智谱开放平台官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "route_type": "official",
        },
        "alibaba": {
            "url": "https://help.aliyun.com/zh/model-studio/pricing",
            "note": "阿里云百炼官方 API。静态基准价，非实时抓取，可在 official.json 覆盖。",
            "route_type": "official",
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
