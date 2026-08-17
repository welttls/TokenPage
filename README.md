# Token黄页 (TokenPage)

查模型价格，上 Token 黄页。

![版本](https://img.shields.io/badge/version-0.5.3-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

每天抓取一次主流模型在**各条路线**上的价格与优惠，告诉你现在用哪条路线最划算。
专为程序员设计——像翻优惠券一样，看今天哪家打折、额度翻倍、限免、数据零保留（ZDR）。

## 核心逻辑

**找优惠券心态**：每天抓取一次「时效性情报」，而不是固定价目表。

- **打折**：DeepSeek 官方峰谷半价等
- **额度折算**：OpenCode Go 订阅 $10/月 → $60 额度（6 倍），模型级额度翻倍 → 等效价更低
- **限免**：OpenCode 限时免费模型
- **数据零保留（ZDR）**：标注每个模型是否用于训练 + 数据保留天数

**三类路线横向比价**：

| 路线类型 | 说明 |
| -------- | ---- |
| 聚合站按量 | OpenRouter（聚合国际供给）、硅基流动（国内/人民币） |
| 订阅折算 | OpenCode Go（额度折算成等效每 1M 价） |
| 官方直连 | DeepSeek / Moonshot(Kimi) / 智谱(GLM) / xAI(Grok) / OpenAI(GPT) / Anthropic(Claude) / 阿里云(Qwen) |

**模型清单**：跟随 OpenCode Go 页面「当前支持的模型列表」（OpenCode 团队实测适合编程的模型），每天抓取检测变化；额外补 Claude 闭源模型（从 OpenCode Zen / 官方 API）。

## 特性

- **模型 × 路线 比价矩阵**：每个模型展示各路线的输入价、输出价、缓存读、缓存写
- **折扣并入矩阵**：OpenRouter 限时折扣并入对应模型的 OpenRouter 列（显示折扣后价 + 原价划掉 + 🎁 标签）；非编程清单折扣单独在「限时折扣」Tab
- **OpenCode Go「2x usage」**：自动抓营销页 opencode.ai/go 的「2x usage」徽标（GPT-5.6 Luna、DeepSeek V4 Flash 限时额度翻倍），折算等效价（如 Flash $0.14 → $0.0117）
- **官方 API 人民币/美元双显示**：Moonshot(Kimi) 官方价为人民币（K3 输出 ¥100/1M、输入未命中 ¥20、命中 ¥2），显示 ¥ + $ 双值
- **额度折算**：OpenCode Go 订阅 $10/月 → $60 额度（6 倍），模型级额度差异 → 等效价 = 标价 × (月费 ÷ 额度)
- **峰谷折扣**：内置 DeepSeek 官方峰谷规则，按当前时段计算有效价
- **ZDR 标注**：是否用于训练 + 数据保留天数（0 天 = ZDR）
- **阶梯价格**：标记如 >200K tokens 翻倍的分档定价
- **涨跌情报**：只保留两天数据，标记 ↓降价 / ↑涨价 / 🆕新上架 / ❌下架
- **比价矩阵交互**：模型族折叠/展开、拖拽排序、📌 置顶、「🔤 A→Z / Z→A」一键切换 + ↩ 恢复默认（localStorage 持久化）
- **悬浮说明**：标签解释、路线官网、官方 API 说明、额度折算/折扣浮窗
- **每天一次抓取**：24h 冷却，冷却期刷新按钮禁用并显示倒计时；强制刷新受独立 10 分钟冷却限流（防高频爬取被上游判定攻击）
- **抓取失败兜底**：单站抓取失败时沿用上一批快照（比价矩阵不缺行、涨跌情报不误报「下架」）
- **官方订阅套餐折算**：Claude / ChatGPT / GLM / 通义(Qoder) / Kimi 官方编程订阅折算成等效价并入矩阵（有明确额度折算数字；无额度标 ♾️ / 宣称倍率）
- **中英文切换**：整站一键中英切换（语言偏好本地持久化）
- **每日自动汇率**：`fetch` 时自动更新人民币兑美元汇率（免钥公开 API，失败保留原值）
- **复古黄页 UI**：报纸式刊头、品牌商标图标、折叠/置顶/拖拽排序
- **100% 本地**：所有数据存 `~/.tokenpage/prices.db`，零上传、零上报；Web 界面无外部 CDN/字体，离线可用

## 安装

```bash
# 纯 CLI（init / fetch / show / diff / doctor 等）
pip install -e .

# 需要本地 Web 版时再安装 Flask
pip install -e ".[web]"
```

依赖：`requests`、`rich`、`beautifulsoup4`（Python ≥ 3.9）；Web 版额外依赖 `flask`（通过 `.[web]` 安装）。

## 使用

```bash
tokenpage init      # 首次生成默认配置（~/.tokenpage/*.json）
tokenpage fetch     # 抓取各路线价格并写入 SQLite（只保留两天）
tokenpage show      # 模型 × 路线 比价矩阵（--json 纯输出）
tokenpage deals     # 查看 OpenRouter 限时折扣（--json 纯输出）
tokenpage diff      # 对比最近两次抓取，标记降价/涨价/新上架/下架
tokenpage rules     # 查看峰谷规则与当前谷/峰状态
tokenpage doctor    # 环境与数据诊断（SQLite / 配置 / 上游可达性 / 汇率新鲜度）
tokenpage web       # 启动本地 Web 版界面（浏览器查看）
tokenpage web --host 0.0.0.0 --readonly   # 公开部署：只读模式，访客不触发抓取
```

或用模块方式：`python -m tokenpage show`

### 示例输出

```text
$ tokenpage show
  🤖 Token黄页 — 模型 × 路线 比价矩阵
┌────────┬──────────┬──────────────┬───────┬──────┬──────┬──────┬────────────┐
│ 模型族  │ 模型      │ 路线          │  输入 │ 输出 │ 缓存读 │ 缓存写 │ 标签       │
├────────┼──────────┼──────────────┼───────┼──────┼──────┼──────┼────────────┤
│ Kimi   │ kimi-k2.6│ OpenCode Go  │ $0.16 │$0.67 │$0.16 │  —   │ 额度×6 🔒ZDR│
│        │          │ OpenRouter   │ $0.58 │$2.44 │$0.10 │  —   │            │
│        │          │ 硅基流动      │ $0.90 │$3.75 │  —   │  —   │            │
│        │          │ Moonshot     │ $0.95 │$4.00 │  —   │  —   │            │
│ DeepSeek│ deepseek-v4-flash-0731 │ DeepSeek官方 │ $0.22 │$0.66 │ — │ — │ 🌙谷时   │
│        │          │ OpenCode Go  │ $0.02 │$0.05 │$0.003│ —  │ 额度×6 🔒ZDR│
└────────┴──────────┴──────────────┴───────┴──────┴──────┴──────┴────────────┘
```

> 额度折算示例：Kimi K2.6 在 OpenCode Go 标价 $0.95/1M，额度 $60/月（月费 $10）→ 等效价 $0.95 ÷ 6 ≈ $0.16。

## 项目结构

```text
tokenpage/                  # 核心包
├── __main__.py             # python -m tokenpage 入口
├── cli.py                  # CLI 子命令（init/fetch/show/diff/doctor/rules/web）
├── config.py               # 配置加载（~/.tokenpage/*.json）
├── models.py               # 核心数据结构（PriceQuote / QuotaInfo / ZdrInfo）
├── recommender.py          # 比价矩阵组装与排序
├── storage.py              # SQLite 存取（~/.tokenpage/prices.db）
├── sync.py                 # 统一抓取入库流程
├── pricing.py              # 峰谷规则
├── quota.py                # 订阅额度折算
├── output.py               # 终端表格输出
├── web.py                  # Flask Web 版（单文件）
├── fetchers/               # 各站抓取器
│   ├── openrouter.py           # OpenRouter 聚合站
│   ├── openrouter_discount.py  # OpenRouter 限时折扣
│   ├── siliconflow.py          # 硅基流动（国内/人民币）
│   ├── opencode_go.py          # OpenCode Go 订阅（额度折算 / 2x usage）
│   ├── opencode_zen.py         # OpenCode Zen
│   ├── coding_plans.py         # 官方订阅套餐（Claude/GPT/GLM/Qoder/Kimi/Ollama）
│   ├── official.py             # 官方 API 直连价格
│   ├── deepseek.py             # DeepSeek 峰谷
│   └── fx.py                   # 人民币兑美元汇率
├── static/                 # 前端静态资源（app.js / style.css / icons/）
└── templates/              # Jinja 模板（index.html）

~/.tokenpage/               # 用户配置与数据目录
├── prices.db               # SQLite 数据库（价格快照，只留 2 天）
├── models.json             # 模型族标签 + 跨站模型 ID 映射
├── rules.json              # 峰谷规则
├── fx.json                 # 人民币兑美元汇率（每日自动更新）
├── go.json                 # OpenCode Go 订阅配置
├── official.json           # 官方 API 价格覆盖
├── plans.json              # 官方订阅套餐配置
└── user_prefs.json         # Web 用户偏好（排序/置顶/折叠/语言）
```

## 配置（~/.tokenpage/）

| 文件            | 说明                                                       |
| --------------- | ---------------------------------------------------------- |
| `models.json`   | 模型族标签 + 跨站模型 ID 映射（可覆盖/追加）               |
| `rules.json`    | 峰谷规则（内置 DeepSeek 官方，可覆盖/新增）                |
| `go.json`       | OpenCode Go 订阅配置（月费、基础额度）                     |
| `official.json` | 官方 API 直连模型价格（可覆盖内置价格表）                  |
| `plans.json`    | 官方订阅套餐配置（Claude/ChatGPT/GLM/Qoder/Kimi/Ollama 订阅折算） |
| `fx.json`       | 人民币兑美元汇率（SiliconFlow 比价换算；每次 `fetch` 自动更新，可手动覆盖） |

### `plans.json`：官方订阅套餐折算

把官方编程订阅（Claude / ChatGPT / GLM / 通义 Qoder / Kimi Code / Ollama 云）折算成「等效每 1M token 价」并入比价矩阵：

```json
{
  "claude_plan": {
    "label": "Claude 订阅",
    "label_en": "Claude Sub",
    "url": "https://www.anthropic.com/pricing",
    "currency": "USD",
    "family": "claude",
    "fee": 20.0,
    "quota_type": "value",
    "monthly_quota": 100.0,
    "estimate": true,
    "tag": "宣称×5",
    "models": ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"],
    "note": "Claude Pro $20/月：官方宣称 5× 但未公布 token 额度 → 按标价 ÷ 5 估算等效价"
  }
}
```

关键字段：

| 字段         | 说明                                                                 |
| ------------ | -------------------------------------------------------------------- |
| `fee`        | 月费（按 `currency` 区分 USD / CNY）                                 |
| `quota_type` | 额度口径：`"tokens"` 有明确 token 额度（配 `tokens_in`/`tokens_out`）；`"value"` 有明确额度价值（配 `monthly_quota`）；`"none"` 无公开额度 → 只标 ♾️/宣称倍率，不折算数字 |
| `tag`        | 标签（如「宣称×5」「额度×3」）；不填则按倍率自动生成                |
| `estimate`   | `true` 时等效价/标签加「估算」角标                                    |
| `models`     | 套用的模型：字符串 = 官方 API 价 ÷ 倍率；跨厂商订阅用 `{"id","family","prompt","completion"}` 条目自带标价 |

## 隐私

- 所有价格数据、配置规则仅存储于本地 SQLite
- 零网络上传；价格抓取通过你的网络直连聚合站公开页面
- 零用户行为追踪；Web 界面无外部 CDN/字体/分析脚本
- ZDR 信息来自 OpenCode Go 隐私表及各站声明，仅作展示参考

## Web 安全与公开部署

Web 版默认只监听 `127.0.0.1`，面向本机使用。若要发布到公网/局域网：

```bash
# 只读模式（推荐）：访客只读快照，绝不触发爬取（--host 非回环地址时自动启用）
tokenpage web --host 0.0.0.0 --readonly

# 公网域名需显式加入 Host 白名单（防 DNS Rebinding）
TOKENPAGE_ALLOWED_HOSTS=your.domain.com tokenpage web --host 0.0.0.0 --readonly
```

内置防护：

- **只读模式**：`--readonly` / `TOKENPAGE_READONLY=1`；监听非回环地址时默认开启（`TOKENPAGE_READONLY=0` 显式关闭），此时 `/api/fetch` 返回 403
- **Host 白名单**：回环/内网地址放行，公网域名须配置 `TOKENPAGE_ALLOWED_HOSTS`（逗号分隔）
- **CSRF 防护**：POST 校验 `Sec-Fetch-Site` / `Origin`，跨站请求无法触发抓取
- **XSS 防护**：前端所有第三方数据（模型名/厂商名）HTML 转义 + CSP 响应头（脚本仅同源、禁内联）
- **冷却防竞态**：强刷「检查+占位」原子化，并发请求无法绕过 10 分钟冷却

> 长期方案见路线图「发布页静态化」：定时抓取 → 生成静态快照托管，Web 服务只读快照。注意 Flask 自带开发服务器不适合直接暴露公网，正式发布建议前置反向代理（nginx/caddy）或使用静态快照方案。
>
> ⚠️ 风险提示：把「本机生成的价格快照」托管到公网，本质上等于替所有访客抓取聚合站——你的 IP 会变成公共爬虫代理，聚合站反爬时封的是你的 IP。建议静态化抓取改用 GitHub Actions 的 IP 池，或干脆保持「人人本地运行」。

## 路线图

- [x] v0.1 核心闭环：OpenRouter / DeepSeek官方 / SiliconFlow 抓取、推荐表格、本地 SQLite
- [x] v0.2 重构：模型 × 路线比价矩阵、OpenCode Go/Zen 订阅折算、7 家官方 API、ZDR 标注、涨跌情报（只留两天）
- [x] v0.3 优惠情报深化：限时折扣并入矩阵、OpenCode Go「2x usage」、实时峰谷、官方订阅套餐折算、中英文切换、Web 安全加固（只读模式 / Host 白名单 / CSRF / CSP）、抓取失败快照兜底
- [x] v0.4 复古黄页 UI：报纸式刊头、品牌商标图标、比价矩阵交互打磨（折叠/置顶/拖拽/字母排序）
- [ ] 计划中：谷时开始提醒、降价推送、关注列表
- [ ] 计划中：桌面小组件（桌宠感）、一键配置 AI 编程工具
- [ ] 远期：发布页静态化 / 接口分离——本机或 GitHub Actions 定时抓取 → 生成静态页面/JSON 快照 → 静态托管发布；访客刷新只重读快照、绝不触发爬取，杜绝「公共爬虫代理」与上游封禁风险

## License

MIT
