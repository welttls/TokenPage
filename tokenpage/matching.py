"""跨站模型 ID 匹配辅助：归一化 + Levenshtein 模糊兜底。

策略（models.json 保持权威）：
  1. 精确站 ID 匹配（各抓取器现有逻辑，优先）
  2. 归一化「模型名称」匹配——各站 name 字段通常比 ID 更统一
  3. 编辑距离模糊兜底——精确/名称都失败时，找最接近的站内 ID/名称

命中 2/3 时抓取器会打 warning 提示「疑似改名，建议固化到 models.json」，
但绝不自动回写配置（避免误配污染 models.json）。
"""

from __future__ import annotations

import re


def normalize(s: str) -> str:
    """归一化模型名/ID：小写 + 去掉所有非字母数字字符。

    例：'Claude Sonnet 4.6' / 'claude-sonnet-4.6' / 'claude_sonnet46'
      → 全部归一化为 'claudesonnet46'。
    """
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def levenshtein(a: str, b: str) -> int:
    """编辑距离（DP，用于小规模字符串，O(n·m)）。"""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(
                min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            )
        prev = cur
    return prev[-1]


def similarity(a: str, b: str) -> float:
    """归一化后的相似度 0~1（1 = 完全相同）。"""
    if not a and not b:
        return 1.0
    d = levenshtein(a, b)
    return 1.0 - d / max(len(a), len(b), 1)


def best_fuzzy_match(
    query: str, candidates: list[str], min_sim: float = 0.85
) -> tuple[str | None, float]:
    """在候选中找与 query 归一化后最接近的一个（相似度 ≥ min_sim）。

    返回 (最佳候选原文, 相似度)；无候选达到阈值返回 (None, 最高相似度)。
    """
    qn = normalize(query)
    if not qn:
        return None, 0.0
    best, best_sim = None, 0.0
    for c in candidates:
        cn = normalize(c)
        if not cn:
            continue
        s = similarity(qn, cn)
        if s > best_sim:
            best, best_sim = c, s
    return (best, best_sim) if best_sim >= min_sim else (None, best_sim)
