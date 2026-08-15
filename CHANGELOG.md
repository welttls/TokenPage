# Changelog

本文件记录 Token黄页 (TokenPage) 的版本更新。

## v0.5.2（2026-08-15）

### 新增
- **README 顶部版本 badge**：新增 shields.io 版本徽章（version-0.5.2）、Python 与 License 徽章，安装后一眼可辨版本
- **README `plans.json` 示例**：配置表补上 `plans.json` 行，并新增「官方订阅套餐折算」小节——含真实字段示例（`fee` / `quota_type` / `tokens_in|tokens_out` / `monthly_quota` / `tag` / `estimate` / `models` / `note`）与字段说明表
- **README 项目结构展开 `fetchers/`**：列出全部 9 个抓取器文件及职责（openrouter / openrouter_discount / siliconflow / opencode_go / opencode_zen / coding_plans / official / deepseek / fx）

### 优化
- 版本号升至 v0.5.2（Web 报头 `VOL. 1 · NO. 0.5.2` 与 `tokenpage --version` 同步更新）

---

## v0.5.1（2026-08-15）

### 新增
- **DeepSeek V4 快照显式带日期**：DeepSeek 族从「flash / pro」两行改为 OpenRouter 实际存在的四个带日期快照行——`deepseek-v4-flash-0423`（$0.07546 / $0.15092）、`deepseek-v4-flash-0731`（$0.14 / $0.28）、`deepseek-v4-pro-0423`（$1.168 / $2.336）、`deepseek-v4-pro-0813`（$0.435 / $0.87）。原先的 `deepseek-v4-flash` / `deepseek-v4-pro` 分别对应 0731 快照与 0813 GA（即「最新」档，官方 / 硅基 / Go / Zen / Ollama 均挂此档）；0423 初版仅在 OpenRouter 有价
- **各站映射新增 `go` / `zen` 字段**：Go / Zen 文档模型 ID 不带日期（`deepseek-v4-flash`），经 `_logical_name` 反向映射与 Zen `track` 反查归组到对应日期行，避免改名后产生孤立的 `deepseek-v4-flash` 行或 Zen 整行丢失

---

## v0.5.0（2026-08-15）

### 新增
- **最新 Qwen3.8-27B 上架**：新增 `qwen3.8-27b` 模型（OpenRouter `qwen/qwen3.8-27b`，输入 $0.45 / 输出 $3.20 / 1M，上下文 262K），随每日抓取自动取价（阿里云百炼官方页尚未收录，故暂无「阿里云」官方列）
- **Ollama Cloud 订阅路线（估算等效价）**：新增 `Ollama 云` 订阅路线，覆盖 Ollama Cloud 托管的开源模型（GLM-5.2/5.1、DeepSeek V4 Flash/Pro、Kimi K3/K2.7-Code/K2.6、MiniMax M2.7/M3）
  - Pro $20/月（宣称 50× 免费额度）、Max $100/月（5× Pro，新订阅暂停）；Ollama 按「模型用量等级 1~4」计额度、未公布 token 数 → 等效价为**估算**（假设 Pro ≈ $60 云额度价值 → 3×，标价取 OpenRouter 同模型价），标签标「·估算」，可在 plans.json 调整
  - ZDR 标注：Ollama 承诺不记录、不训练（0 天保留）
- **Claude 订阅（按宣称 5× 折算估算等效价）**：Claude Pro $20/月 官方仅宣称「5× free 使用量」、未公布 token 额度 → 由原来的 ♾️ 改为**估算等效价**（假设 $20 ≈ $100 云额度价值 → 5×，= 官方 API 标价 ÷ 5），标签保留「宣称×5」并标注「·估算」

### 优化
- 订阅套餐配置支持「跨厂商」模型列表（`models` 条目可为 `{"id":..., "family":...}`），套餐本身不必绑定单一模型族（Ollama Cloud 使用）
- 订阅套餐模型条目可自带列表价（prompt/completion）与「估算」标记，供无官方 API 直连的多厂商订阅（如 Ollama）折算等效价

### 修复
- **DeepSeek V4 Pro 路由修正**：`models.json` 中 `deepseek-v4-pro` 的 OpenRouter 映射从错误的 canonical slug `deepseek/deepseek-v4-pro-20260813` 改为真实模型 ID `deepseek/deepseek-v4-pro-0813`，消除矩阵中多余的 `deepseek-v4-pro-0813` 模型行（此前 flash 精确命中显示为 `deepseek-v4-flash`、pro 模糊命中残留日期后缀，造成「flash + pro + pro0813」混排）

---

## v0.4.0（2026-08-15）

### 新增
- **`tokenpage doctor` 诊断命令**：一键检查 SQLite 完整性/价格快照、各配置文件 JSON 语法、OpenRouter / SiliconFlow / DeepSeek 官方上游可达性、fx.json 汇率新鲜度；`✓/✗/!` 三态输出，`--no-network` 跳过网络检查（只读，不写库/不改配置）
- **用户偏好落盘 `~/.tokenpage/user_prefs.json`**：Web 的模型族排序/置顶/折叠/字母排序/币种/语言从浏览器 localStorage 迁移到本机文件——同一台机器不同浏览器共享，清缓存不丢（前端仍保留 localStorage 作离线/静态托管兜底）
- **跨站模型映射容错**：OpenRouter 先精确 ID 匹配，未命中时用归一化模型 name 匹配，再退到 Levenshtein 编辑距离模糊兜底（命中打 warning 提示「建议固化到 models.json」，不自动回写）；SiliconFlow 同理按页面模型名模糊兜底，减少各站改名/新增导致的手动维护
- **OpenCode Go 营销页抓取容错与告警**：促销抓取失败不再静默，输出 `warning: OpenCode Go 折扣抓取失败，沿用上次数据`；连续失败次数记入 meta，连续 ≥3 天在 Web 状态条显示 ⚠️ 提示

### 优化
- `cmd_diff` 首用体验：区分「数据库为空」与「只抓过一次」两种状态并给出友好提示（明天再跑 diff 就能看到涨跌）
- `diff`/`deals`/`show` 等 CLI 命令不再依赖 Flask（纯 CLI 用户无需安装）

### 工程
- **Flask 改为可选依赖**：`pip install -e .` 只装 CLI；`pip install -e ".[web]"` 才安装 Web 版
- README 重写：特性章节去掉过时版本号、路线图按实际实现校正（未实现项移入「计划中」）、新增项目结构说明、fx.json 标注每日自动更新、静态化补充「公共爬虫代理/封 IP」风险提示

### 修复
- 英文版广告招牌「Compare Prices · on the Pages」拆为两行（`Compare Prices` / `on the Pages`），避免被挤到左侧

---

## v0.3.13（2026-08-15）

### 新增
- **官方订阅套餐（coding plan）纳入比价矩阵**：新增 5 家模型厂商官方编程订阅路线（Claude 订阅 / ChatGPT 订阅 / GLM 订阅 / 通义订阅 / Kimi 订阅），每个套餐只显示在对应模型族下，与按量/官方 API 并排比价
  - **有明确额度 → 折算「等效每 1M token 价」**（= 官方 API 标价 ÷ 额度倍率，复用 `quota.py` 额度折算引擎）：
    - GLM Coding Plan Lite ¥94.4/月（每周 10,000 积分 ≈ 0.43~0.87 亿 tokens/周，GLM-5.3）
    - Qoder CN（通义灵码）个人专业版 ¥59/月（2,000 Credits ≈ ¥80 价值，按资源包单价）
    - Kimi Code Plan Moderato ¥79/月（官网未公布具体 token 数，按 K3 官方价估算约 10×，可在 `plans.json` 调整）
  - **无明确额度 → 只标 ♾️ / 宣称倍率**：Claude Pro「宣称×5」、ChatGPT Plus「♾️扩展额度」，价格列显示 ♾️，不折算数字
- 新增 `~/.tokenpage/plans.json` 配置（套餐月费/额度/覆盖模型/说明，可覆盖、可追加），新抓取器 `fetchers/coding_plans.py`（静态配置，无网络依赖）
- **订阅浮窗泛化**：所有 subscription 路线（含官方订阅套餐）统一显示「标价 → 等效价（额度倍率，月费 → 额度）」与「额度用不完实际更贵」提示；新增「宣称×N」「♾️无限/扩展」标签浮窗说明（中英文）

### 修复
- **报头招牌钉子松动交互**：广告框改成悬挂式酒馆招牌（圆头铁钉 + 麻绳，木纹质感），点击/回车/空格切换「落下 + 晃动」动画并同步 `aria-pressed`（再点恢复）
- **英文版招牌被换行挤到左侧**：`.masthead-mid` 改 `flex-wrap:nowrap`，招牌永远与品牌同一行固定在右；英文 ad-box 收窄为紧凑两行（`html[lang="en"]` 窄宽下保持 2 行）

### 说明
- 套餐价与额度为 2026-08 官网核实值（GLM / Qoder 为公开数据，Kimi 为估算），可随时在 `plans.json` 调整

---

## v0.3.12（2026-08-15）

### 修复
- **强制刷新按钮点击无反馈**：主按钮 24h 冷却期每秒执行的按钮同步会覆盖 `forceRefresh()` 设置的「强制抓取中…」状态，导致第一次点击看似无效、第二次才出现倒计时。新增 `fetching` / `forceFetching` 状态标记保护进行中的抓取反馈，普通刷新在强刷冷却期的同类隐患一并修复
- **DeepSeek 官方价与官网当前价不符**：内置表提前使用 8/16 16:00 UTC 才生效的峰谷 PEAK 价（flash $0.44/$1.32），而官网当前（峰谷未生效）实际价是 $0.14/$0.28。改为「生效前固定价 / 生效后峰谷价」两档，按 `EFFECTIVE_FROM` 自动切换；生效前不再误乘谷时折扣
- **DeepSeek 官方缓存读价缺失**：补上官网明确列出的缓存命中输入价（flash $0.0028 / pro $0.003625；生效后峰时 $0.014 / $0.044）

### 优化
- 峰谷规则支持 `effective_from`（生效时刻）：生效前 `offpeak_status` 返回无折扣，峰谷计算对「生效前固定价」不生效

---

## v0.3.11（2026-08-15）

### 新增
- **中英文切换**：报头右上角新增「中文 / EN」分段按钮，一键整站中英文切换（本地 `localStorage` 的 `tp.lang` 持久化，刷新不丢失）。覆盖报头/状态条/选项卡/按钮/操作提示/页脚等全部静态文案，以及比价矩阵、涨跌情报、限时折扣、收录渠道、峰谷状态、标签浮窗与路线浮窗等全部动态内容；`<html lang>`、页面标题、时钟区域随语言联动；渠道名（DeepSeek官方→DeepSeek Official、智谱→Zhipu 等）、标签（额度×6→Quota×6、阶梯→Tiered、谷时→Off-peak 等）一并翻译
- **额度折算精度提示**：OpenCode Go 等效价（= 标价 ÷ 额度倍率）是按「当月额度全量消耗」的理论最优价，若用户没用完额度实际成本更高——在路线浮窗、额度标签浮窗与渠道说明中补充「※ 等效价按当月额度全量消耗计算；若额度用不完，实际成本会更高」提示（中英文各一份）

### 说明
- 未提交 git（用户未要求）。后端 `provider_meta()` 各渠道新增 `note_en` 字段供英文界面读取；前端 `app.js` 新增 i18n 层（`I18N` 字典 + `t()/plabel()/translateTag()/applyLang()`），切语言时基于 `lastOverview` 缓存整体重渲染动态面板

---

## v0.3.10（2026-08-15）

### 安全（面向公开部署）
- **XSS 修复**：涨跌情报/收录渠道/峰谷状态/路线徽章等所有第三方数据（模型名、厂商名）前端 HTML 转义（`esc()`），OpenRouter 折扣 slug 等不可信数据不再直接拼 `innerHTML`；新增 CSP 等安全响应头（脚本仅同源、禁内联、`X-Content-Type-Options`、`Referrer-Policy`）
- **只读模式（发布网站）**：`--readonly` / `TOKENPAGE_READONLY=1` 禁用 `/api/fetch`，访客绝不触发爬取；`--host` 非回环地址时默认开启（`TOKENPAGE_READONLY=0` 显式关闭），前端隐藏抓取按钮
- **Host 白名单**：回环/内网 IP 放行，公网域名须配置 `TOKENPAGE_ALLOWED_HOSTS`（防 DNS Rebinding）
- **CSRF 防护**：POST 校验 `Sec-Fetch-Site` / `Origin`，恶意网页无法跨站触发抓取
- **强刷竞态**：强刷冷却「检查+占位」加锁原子化，并发请求无法绕过 10 分钟冷却高频爬取
- **资源全本地化**：移除 Google Fonts 与 simpleicons CDN，品牌图标全部本地 SVG（新增 claude/qwen/deepseek/minimax/x），兑现「100% 本地、无外部依赖」承诺

### 修复
- **失败站兜底**：单站抓取失败时沿用上一批快照（`storage.carry_forward_providers`），比价矩阵不缺行、涨跌情报不再误报「下架」；CLI/Web 共用 `tokenpage/sync.py` 抓取入库流程
- **峰谷涨跌误报**：涨跌对比对有峰谷规则的 provider 改用 `raw_*` 基准价归一化，两次抓取分别落在峰/谷时段不再误报涨价/降价
- **实时峰谷缓存价**：`apply_offpeak_live` 补齐 cache_read/cache_write 的峰/谷重算（此前只重算输入/输出价）；`raw_prompt` 缺失不再导致输出价漏算
- **tiered 判定**：OpenRouter `top_provider` 为对象，此前 `== "tiered"` 恒 False，改为读对象字段
- **硅基流动精确匹配**：模型名加词边界（`(?<![\w.-])...(?![\w.-])`），`GLM-5.2` 不再误命中 `GLM-5.25` 等更长型号
- **CLI 折扣排序**：`deals` 按折扣力度降序（与注释意图一致，此前误按输入价排）
- **折扣并入守卫**：折扣价缺失（None/0）时不再覆盖矩阵已有有效价；划线原价显式判 None（免费模型 0 价不再误回退）
- **极小价显示**：Web/前端价格精度提高至 6 位，等效价 $0.00003 不再显示为「免费」

### 优化
- OpenCode Go/Zen 文档表格解析异常（结构变化、行无法映射、ZDR 缺失）输出 warning 日志，不再静默丢数据
- 配置文件 JSON 语法错误时输出明确警告（此前静默回退默认值）
- 汇率自动更新不再覆盖 `fx.json` 用户自写的 `note`
- 路线排序对同优先级 provider 加稳定次级键；`_logical_name` 死分支修正（官方直连按 `route_type=official` 判断）

---

## v0.3.9（2026-08-15）

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
