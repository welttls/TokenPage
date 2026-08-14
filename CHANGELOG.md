# Changelog

本文件记录 Token黄页 (TokenPage) 的版本更新。

## v0.3.0（2026-08-15）

### 新增
- **模型 × 路线 比价矩阵**：每行展示各路线的输入/输出/缓存读/缓存写价；模型族可折叠/展开、拖拽排序、📌 置顶、「🔤 按字母排序」（localStorage 持久化）
- **折扣并入矩阵**：OpenRouter 限时折扣并入对应模型的 OpenRouter 列（折扣后价 + 原价划掉 + 🎁 标签）；非编程清单折扣单独在「限时折扣」Tab
- **OpenCode Go「2x usage」**：抓取营销页 opencode.ai/go 的「2x usage」徽标，折算等效价（如 DeepSeek V4 Flash $0.14 → $0.0117，标签「额度×6·限时×2」）
- **官方 API 人民币/美元双显示**：Moonshot(Kimi) 官方价改人民币（K3 输入未命中 ¥20 / 命中 ¥2 / 输出 ¥100），显示 ¥ + $ 双值
- **Web 版界面**：本地 Web 服务器（端口 8765），/api/overview 矩阵、/api/fetch 24h 冷却（?force=1 强刷）
- **悬浮提示**：标签解释、路线官网链接、官方 API / 额度折算 / 折扣说明浮窗

### 优化
- OpenRouter 折扣还原：`_undo_discount()` 把折扣后价还原为原价存 raw_*，并入矩阵时划线展示
- 折扣并入逻辑：tracked 模型折扣并入 OpenRouter 列；非 tracked 折扣行仅进 deals Tab
- 精确匹配：OpenCode Go 列表判断改为「斜杠后段 == 逻辑模型 ID」，避免 glm-5 → glm-5.3 子串误配
- 官方渠道元信息：provider_meta 每渠道官网 URL + 说明

### 修复
- 人民币/美元格式化：`fmtNum` 修复（String(Number(v.toFixed(4)))），消除浮点尾差
- 刷新冷却 UX：点击 → skipped → 按钮变「强制刷新」再点 force=1

---

## v0.2.0

### 新增
- **重构为模型 × 路线 比价矩阵**（替代 v0.1 的推荐表格）
- **OpenCode Go / Zen 订阅折算**：$10/月 → $60 额度（6 倍），模型级额度差异 → 等效价
- **7 家官方 API**：DeepSeek / Moonshot(Kimi) / 智谱(GLM) / xAI(Grok) / OpenAI(GPT) / Anthropic(Claude) / 阿里云(Qwen)
- **ZDR 标注**：是否用于训练 + 数据保留天数（0 天 = ZDR）
- **涨跌情报**：只保留两天数据，标记 ↓降价 / ↑涨价 / 🆕新上架 / ❌下架
- **峰谷折扣**：内置 DeepSeek 官方峰谷规则，按当前时段计算有效价

---

## v0.1.0

### 新增
- 核心闭环：OpenRouter / DeepSeek 官方 / SiliconFlow 抓取、推荐表格、本地 SQLite
- 100% 本地：数据存 `~/.tokenpage/prices.db`，零上传、零上报
