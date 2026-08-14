# Changelog

本文件记录 Token黄页 (TokenPage) 的版本更新。

## v0.3.9（2026-08-15，待提交）

### 修复
- 浮窗被卡片边缘/边框遮挡：`.family-card` 的 `overflow:hidden` 改为 `overflow:visible`，保证多标签（如 qwen3.7-plus 的「阶梯」）浮窗能溢出卡片完整显示、盖住边界线（z-index:50 生效）
- 路线浮窗恢复居中：移除 `.route .tip::after` 覆盖规则，路线浮窗与标签浮窗一致水平居中（`left:50% + translateX(-50%)`），靠 `overflow:visible` 保证最上层不被遮挡

---

## v0.3.8（2026-08-15）

### 修复
- ZDR 无有效信息（`retention_days` 为 None）时不再显示 `—` 占位标签，修复 minimax-m2.5 等模型出现横杠的问题（`price_tags`/`discount_tags` 过滤无效 ZDR 标签）

---

## v0.3.7（2026-08-15）

### 修复
- 路线浮窗改为从路线元素向右展开（`.route .tip::after` 用 `left:0` 替代 `right:0`），修复此前右对齐导致浮窗向左跑偏的问题

---

## v0.3.6（2026-08-15）

### 新增
- **实时峰谷**：比价矩阵读取时按当前时刻动态应用峰谷折扣（`pricing.apply_offpeak_live`，以 `raw_*` 为基准价避免重复乘折扣），DeepSeek 官方价与路线排序随峰/谷自动切换，不再冻结在抓取时刻（Web `/api/overview` 与 CLI `show` 同步生效）

### 修复
- **luna 折扣划线**：OpenRouter 折扣并入矩阵时划线原价改用折扣反推原价（`raw_*`），修复 gpt-5.6-luna 等原价等于折扣价导致不划线的问题
- **折扣标签去「编程」**：deal_tag 去掉 `·编程` 后缀统一为 `🎁xx%off`（含数据库存量数据更新），相关排序/文案同步清理

### 优化
- **路线浮窗靠右**：`.route .tip::after` 右对齐，长内容不再居中遮挡（标签浮窗仍居中）

---

## v0.3.5（2026-08-15）

### 优化
- **人民币 / 美元互斥显示**：价格格只显示当前选中币种（按钮切换），不再「主价+小字」双显；折扣行划线原价同币种折算
- **统一两位小数**：所有价格保留两位小数（极小价如 $0.004 / ¥0.007 保留三位避免显示 0.00）

---

## v0.3.4（2026-08-15）

### 优化
- **折扣行单一币种排版**：OpenRouter 折扣并入矩阵的行，划线原价按主显币种折算，只显示一种币种（美元主显 `~~$1.19~~ $0.49`，人民币主显 `~~¥8.04~~ ¥3.31`），不再「原价+折扣价+双币」三重挤压；非折扣列仍保留主价+小字双显
- **浮窗水平居中**：`.tip::after` 改为 `left:50% + translateX(-50%)` 居中于标签，移除 `.tags`/`.deal-tags` 的右对齐覆盖；`deal-tags` 仍保留 420px 加宽

---

## v0.3.3（2026-08-15）

### 新增
- **每日自动抓取汇率**：新增 `tokenpage/fetchers/fx.py`，随每次抓取顺带更新人民币兑美元汇率（免钥公开 API：`open.er-api.com` 主源 + `api.frankfurter.app` 回退），写回 `fx.json`，前端人民币换算与 SiliconFlow/官方 CNY 折算自动用最新汇率
- `config.save_fx()` 写回 fx.json；`fetch_all()` 集成汇率更新（失败保留原值、计入 errors）

### 修复
- **移除 deepseek-chat**：删除 DeepSeek 官方内置表中的 `deepseek-chat`（V3.x 占位项）并清理 `prices.db` 历史数据，矩阵 DeepSeek 族仅保留 `deepseek-v4-flash` / `deepseek-v4-pro`
- fx.json 历史 note 的 GBK 乱码随 save_fx（UTF-8）覆盖修复

---

## v0.3.2（2026-08-15）

### 修复
- 限时折扣 Tab 标签浮窗右对齐并放宽宽度（`.deal-tags .tip::after` 增加 `right:0` + `max-width:420px`），不再超出视口右缘、长说明不再被压成细长条
- 矩阵控制按钮与操作提示仅比价矩阵页可见：切换「涨跌情报/限时折扣」Tab 时隐藏币种切换、A→Z 排序、全部收起/展开按钮及矩阵操作提示（`.matrix-ctrl` / `.hint`），用 `visibility` 占位保证面板高度恒定、内容不跳

---

## v0.3.1（2026-08-15）

### 新增
- **强刷独立限流**：`/api/fetch?force=1` 增加独立 10 分钟冷却（`FORCE_COOLDOWN_SECONDS`），防止高频爬取被上游判定为攻击
- **刷新冷却倒计时**：冷却期（24h）内刷新按钮禁用并显示「⏳ 冷却 h:mm:ss」倒计时；冷却期出现受控「⚡ 强制刷新」入口（自身受 10 分钟冷却约束）
- **字母排序一键切换**：字母按钮改单按钮双向切换「🔤 A→Z ⇄ Z→A」，首击进入 A→Z，再击切换方向；新增「↩」恢复默认顺序按钮（拖拽族头同样恢复并同步按钮状态）
- **/api/overview 下发冷却字段**：`fetch_cooldown_seconds` / `fetch_cooldown_remaining` / `force_cooldown_seconds` / `force_cooldown_remaining`

### 优化
- 后端 `_cooldown_remaining()` 统一计算冷却剩余秒数；`storage` 新增 `meta` 键值表记录上次强刷时间
- README 增加远期目标：发布页静态化 / 接口分离（本机抓取生成静态快照，访客只读快照不触发爬取）

### 修复
- 刷新按钮禁用态 cursor 由 wait 改为 not-allowed
- 拖拽排序后字母排序按钮状态同步（此前未刷新按钮文案/高亮）

---

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
