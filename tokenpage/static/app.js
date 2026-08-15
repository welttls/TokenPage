/* Token黄页 — 前端逻辑（原生 JS，无外部依赖） */
"use strict";

const FAMILY_EMOJI = {
  claude: "✳️", kimi: "🪐", glm: "🟦", gpt: "🧠", deepseek: "🔺", qwen: "🐫",
  grok: "🛰️", minimax: "🔮", mimo: "🧬", hy3: "🧪",
};

// 模型族 → 官方商标（全部本地 SVG，static/icons/，无外部 CDN，离线可用）。
// 加载失败时由下方捕获阶段的 error 监听自动回退到 FAMILY_EMOJI。
const FAMILY_LOCAL_ICON = {
  gpt: "openai",
  glm: "zhipu",
  hy3: "hunyuan",
  kimi: "kimi",
  claude: "claude",
  qwen: "qwen",
  deepseek: "deepseek",
  minimax: "minimax",
  grok: "x",
};

// 品牌图标：<img> 加载失败时替换为 emoji（捕获阶段监听，兼容 CSP 禁内联事件）
function brandIcon(family, cls) {
  const emoji = FAMILY_EMOJI[family] || "🧩";
  const local = FAMILY_LOCAL_ICON[family];
  if (!local) return `<span class="${cls}">${emoji}</span>`;
  return (
    `<span class="${cls}">` +
    `<img src="/static/icons/${local}.svg" alt="" loading="lazy" data-emoji="${emoji}">` +
    `</span>`
  );
}

// error 事件不冒泡但可捕获：图标加载失败 → 原位替换为 emoji
document.addEventListener(
  "error",
  (e) => {
    const t = e.target;
    if (t && t.tagName === "IMG" && t.dataset.emoji) {
      const span = document.createElement("span");
      span.textContent = t.dataset.emoji;
      t.replaceWith(span);
    }
  },
  true
);

/* ---------------- 中英文切换（i18n） ---------------- */
const LANG_KEY = "tp.lang";
let lang = "zh"; // "zh" | "en"
try { lang = localStorage.getItem(LANG_KEY) || "zh"; } catch {}

const I18N = {
  zh: {
    title: "Token黄页 · 查模型价格",
    brand_suffix: "黄页",
    tagline: "— 模型价格分类簿 · 主流渠道优惠情报 · 一册在手比价不愁 —",
    ad_tag: "本页广告位",
    ad_line: "查价格 · 上黄页",
    status_data: "数据时间",
    status_sources: "收录渠道",
    status_offpeak: "峰谷电价",
    refresh: "↻ 刷新价格",
    force: "⚡ 强制刷新",
    cooling: "⏳ 冷却 {n}",
    force_cooling: "⚡ 强刷 {n}",
    refreshing: "抓取中…",
    force_refreshing: "强制抓取中…",
    panel_title: "模型 × 路线 比价分类栏",
    tab_matrix: "比价矩阵",
    tab_diff: "涨跌情报",
    tab_deals: "限时折扣",
    btn_usd: "$ 美元",
    btn_cny: "¥ 人民币",
    collapse_all: "▸ 全部收起",
    expand_all: "▾ 全部展开",
    hint: "点击族头折叠/展开 · ⠿ 拖拽排序 · 📌 置顶 · 悬停看说明",
    footer: "本簿免费 · 价目每日一印，隔两日作废重排 · 抄自各家公开价目，一翻便知哪家划算",
    no_data_refresh: "（暂无数据，请先刷新）",
    no_data_readonly: "（无数据）",
    no_data_click: "（无数据，请点击「刷新价格」）",
    offpeak_no_rule: "无规则",
    offpeak_on: "🌙 谷时（折扣生效）",
    offpeak_off: "☀️ 峰时（原价）",
    diff_empty_need_two: "暂无涨跌对比：需要至少两次抓取。",
    diff_empty_no_change: "本次抓取与上次相比没有价格变化。",
    diff_down: "↓ 降价 {n}",
    diff_up: "↑ 涨价 {n}",
    diff_new: "🆕 新上架 {n}",
    diff_gone: "❌ 下架 {n}",
    diff_in: "输入 {f}→{t}",
    deals_empty: "暂无限时折扣：请先刷新价格抓取 OpenRouter 折扣。",
    deals_summary: "🎁 共 {n} 个 OpenRouter 限时折扣（Go 清单折扣已并入比价矩阵，此处不再重复）",
    deal_head_off: "折扣",
    deal_head_model: "模型",
    deal_head_family: "族",
    deal_head_price: "输入 / 输出",
    deal_head_tags: "标签",
    matrix_head_route: "路线",
    matrix_head_in: "输入",
    matrix_head_out: "输出",
    matrix_head_cr: "缓存读",
    matrix_head_cw: "缓存写",
    matrix_head_tags: "标签 / ZDR",
    models_count: "{n} 模型",
    empty_readonly: "暂无价格数据。<br>服务端尚未抓取，请等待管理员执行 tokenpage fetch。",
    empty_normal: "暂无价格数据。<br>点击右上角「刷新价格」开始抓取。",
    fetch_error: "部分站点抓取失败：",
    fetch_fail: "抓取失败：",
    force_fetch_fail: "强制刷新失败：",
    free: "🆓 免费",
    route_site: "官网：",
    tip_quota: "订阅/套餐额度折算：等效价 = 官方标价 ÷ 额度倍率（月费对应的额度价值）。按全额度消耗计算（额度用不完实际更贵）",
    tip_claimed: "官方未公布具体 token 额度，按宣称的 N× 使用量估算，不折算等效价",
    tip_unlimited: "官方未公布具体 token 额度，为无限/扩展额度，无法折算等效价",
    tip_promo: "OpenCode Go 限时额度促销（2x usage）：该模型当月使用额度翻倍",
    tip_deal: "OpenRouter 限时折扣：{pct}% off，显示价已为折扣后价",
    tip_zdr: "零数据保留（ZDR）：数据不用于训练、不保留",
    tip_retention: "数据保留 {n} 天",
    tip_tiered: "有阶梯价格：长上下文（超过阈值）单价更高",
    tip_free: "免费 / 限时免费提供",
    tip_offpeak: "谷时计价：当前处于折扣时段（如 DeepSeek 谷时半价）",
    quota_line: "标价 ${list} → 等效 ${eff}（{mult}，${fee}/月 → ${quota} 额度）",
    quota_hint: "※ 等效价按当月额度全量消耗计算；若额度用不完，实际成本会更高。",
    deal_line: "原价 ${list} → 限时折扣 ${eff}",
    quota_mult: "额度×{n}",
    title_cny_off: "当前美元主显（人民币小字），点击切换",
    title_cny_on: "当前人民币主显（美元小字），点击切换",
    title_alpha: "模型族按字母排序：A→Z / Z→A 一键切换",
    title_alpha_reset: "恢复默认顺序",
    title_collapse: "一键收起全部模型族",
    title_expand: "一键展开全部模型族",
    title_force: "冷却期内强制重新抓取（10 分钟一次）",
    title_lang: "切换中英文 / Toggle language",
  },
  en: {
    title: "Token Yellow Pages · Model Price Finder",
    brand_suffix: " Yellow Pages",
    tagline: "— Model Price Directory · Bargain Intel · One Volume, Compare & Conquer —",
    ad_tag: "AD SPACE",
    ad_line: "Compare Prices · on the Pages",
    status_data: "Data Time",
    status_sources: "Sources",
    status_offpeak: "Off-peak",
    refresh: "↻ Refresh",
    force: "⚡ Force",
    cooling: "⏳ Cooldown {n}",
    force_cooling: "⚡ {n}",
    refreshing: "Fetching…",
    force_refreshing: "Force fetching…",
    panel_title: "Models × Routes Price Directory",
    tab_matrix: "Matrix",
    tab_diff: "Price Changes",
    tab_deals: "Deals",
    btn_usd: "$ USD",
    btn_cny: "¥ CNY",
    collapse_all: "▸ Collapse all",
    expand_all: "▾ Expand all",
    hint: "Click a family header to fold · ⠿ drag to sort · 📌 pin · hover for help",
    footer: "Free of charge · prices printed daily, void after two days · compiled from public price lists",
    no_data_refresh: "(no data yet, please refresh)",
    no_data_readonly: "(no data)",
    no_data_click: "(no data, click Refresh)",
    offpeak_no_rule: "No rule",
    offpeak_on: "🌙 Off-peak (discount active)",
    offpeak_off: "☀️ Peak (list price)",
    diff_empty_need_two: "No comparison yet: need at least two fetches.",
    diff_empty_no_change: "No price changes since the last fetch.",
    diff_down: "↓ Price drop {n}",
    diff_up: "↑ Price rise {n}",
    diff_new: "🆕 New {n}",
    diff_gone: "❌ Gone {n}",
    diff_in: "in {f}→{t}",
    deals_empty: "No deals yet: please refresh to fetch OpenRouter discounts.",
    deals_summary: "🎁 {n} OpenRouter limited-time deals (Go-list deals are merged into the matrix)",
    deal_head_off: "Off",
    deal_head_model: "Model",
    deal_head_family: "Family",
    deal_head_price: "In / Out",
    deal_head_tags: "Tags",
    matrix_head_route: "Route",
    matrix_head_in: "In",
    matrix_head_out: "Out",
    matrix_head_cr: "Cache R",
    matrix_head_cw: "Cache W",
    matrix_head_tags: "Tags / ZDR",
    models_count: "{n} models",
    empty_readonly: "No price data yet.<br>The server hasn't fetched; wait for an admin to run tokenpage fetch.",
    empty_normal: "No price data yet.<br>Click Refresh (top right) to fetch.",
    fetch_error: "Some sources failed:",
    fetch_fail: "Fetch failed:",
    force_fetch_fail: "Force refresh failed:",
    free: "🆓 Free",
    route_site: "Site: ",
    tip_quota: "Subscription plan quota: equiv price = list price ÷ multiplier (value of the monthly fee). Assumes FULL monthly quota usage; if unused, the real cost is higher.",
    tip_claimed: "No token quota published; estimated from claimed N× usage, no equivalent price.",
    tip_unlimited: "No token quota published; unlimited/extended usage, no equivalent price.",
    tip_promo: "OpenCode Go limited-time quota promo (2x usage): doubled monthly quota this month",
    tip_deal: "OpenRouter limited-time deal: {pct}% off, shown price is already discounted",
    tip_zdr: "Zero Data Retention (ZDR): data not used for training, not retained",
    tip_retention: "Data retained {n} days",
    tip_tiered: "Tiered pricing: higher unit price for long contexts (above threshold)",
    tip_free: "Free / limited-time free",
    tip_offpeak: "Off-peak pricing: discount period active (e.g. DeepSeek off-peak half price)",
    quota_line: "List ${list} → equiv ${eff} ({mult}, ${fee}/mo → ${quota} quota)",
    quota_hint: "※ Equivalent price assumes FULL monthly quota usage; if unused, the real cost is higher.",
    deal_line: "List ${list} → deal ${eff}",
    quota_mult: "Quota×{n}",
    title_cny_off: "Currently USD primary (CNY small); click to switch",
    title_cny_on: "Currently CNY primary (USD small); click to switch",
    title_alpha: "Sort families A→Z / Z→A",
    title_alpha_reset: "Restore default order",
    title_collapse: "Collapse all families",
    title_expand: "Expand all families",
    title_force: "Force re-fetch during cooldown (once per 10 min)",
    title_lang: "Toggle Chinese / English",
  },
};

function t(key, params) {
  let s = (I18N[lang] && I18N[lang][key] != null) ? I18N[lang][key] : (I18N.zh[key] != null ? I18N.zh[key] : key);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      s = s.split("{" + k + "}").join(v);
    }
  }
  return s;
}

// 渠道展示名英文映射（后端 label 为中文/原名，按 provider key 翻译）
const PROVIDER_LABEL_EN = {
  openrouter: "OpenRouter",
  openrouter_deals: "OpenRouter Deals",
  siliconflow: "SiliconFlow",
  opencode_go: "OpenCode Go",
  opencode_zen: "OpenCode Zen",
  deepseek: "DeepSeek Official",
  official: "Official API",
  anthropic: "Anthropic",
  openai: "OpenAI",
  xai: "xAI",
  moonshot: "Moonshot",
  zhipu: "Zhipu",
  alibaba: "Aliyun",
  anthropic_plan: "Claude Sub",
  openai_plan: "ChatGPT Sub",
  zhipu_plan: "GLM Sub",
  alibaba_plan: "Qoder Sub",
  moonshot_plan: "Kimi Sub",
};
function plabel(provider, zhLabel) {
  if (lang !== "en") return zhLabel;
  return PROVIDER_LABEL_EN[provider] || zhLabel;
}

// 后端标签（中文）在英文模式下翻译显示（如 额度×6 → Quota×6）
function translateTag(tag) {
  if (lang !== "en") return tag;
  let s = tag;
  s = s.replace(/额度×/g, "Quota×");
  s = s.replace(/限时×/g, "Promo×");
  s = s.replace(/阶梯/g, "Tiered");
  s = s.replace(/🆓限免/g, "🆓Free");
  s = s.replace(/🌙谷时/g, "🌙Off-peak");
  s = s.replace(/宣称×/g, "Claimed×");
  s = s.replace(/♾️无限/g, "♾️Unlimited");
  s = s.replace(/♾️扩展额度/g, "♾️Extended");
  return s;
}

// 静态文本（data-i18n）按当前语言更新
function applyStaticLang() {
  document.title = t("title");
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  const btn = $("#btnLang");
  if (btn) {
    btn.classList.toggle("on", lang === "en");
    btn.setAttribute("aria-pressed", String(lang === "en"));
    btn.title = t("title_lang");
  }
}

// 切语言：静态文本 + 动态面板整体重渲染 + 按钮同步
function applyLang() {
  applyStaticLang();
  if (lastOverview) {
    renderProviders(lastOverview.providers);
    renderOffpeak(lastOverview.rules);
    renderMatrix(lastOverview.matrix);
    renderDiffs(lastOverview.diffs);
    renderDeals(lastOverview.deals);
  }
  syncAlphaBtn();
  syncCnyBtn();
  syncCollapseAllBtn();
  syncRefreshButtons();
  tickClock();
}

function toggleLang() {
  lang = lang === "zh" ? "en" : "zh";
  try { localStorage.setItem(LANG_KEY, lang); } catch {}
  applyLang();
}

const ROUTE_CLASS = {
  opencode_go: "opencode_go",
  openrouter: "openrouter",
  siliconflow: "siliconflow",
  opencode_zen: "opencode_zen",
  official: "official",
  anthropic: "official",
  openai: "official",
  xai: "official",
  moonshot: "official",
  zhipu: "official",
  alibaba: "official",
  deepseek: "deepseek",
  anthropic_plan: "plan",
  openai_plan: "plan",
  zhipu_plan: "plan",
  alibaba_plan: "plan",
  moonshot_plan: "plan",
};

// 折叠/排序/置顶状态（纯本地 localStorage）
const UI_KEY = "tp.matrix.ui";
let uiState = { order: [], pinned: [], collapsed: [], alpha: 0, cny: false };

let currentMatrix = null;
let currentProviderMeta = {};
let currentFx = null; // { CNY_per_USD: 7.2, ... }
let dragFam = null;
let lastOverview = null; // 最近一次 /api/overview 原始数据（切语言时重渲染用）

// 抓取冷却状态（秒），由 /api/overview 下发，倒计时驱动刷新按钮禁用
let cooldownRemaining = 0;      // 普通刷新冷却剩余
let forceCooldownRemaining = 0; // 强制刷新冷却剩余
let cooldownTimer = null;
let readonlyMode = false;       // 只读模式（公开部署）：服务端禁用 /api/fetch
let fetching = false;           // 普通刷新进行中：syncRefreshButtons 不覆盖「抓取中…」状态
let forceFetching = false;      // 强制刷新进行中：syncRefreshButtons 不覆盖「强制抓取中…」状态

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function fmtNum(v) {
  if (v == null) return "—";
  // 逐步提高精度，避免极小价（如 ¥0.007）被舍成 0
  for (const d of [2, 3, 4]) {
    const s = v.toFixed(d);
    if (Number(s) > 0) return String(Number(s));
  }
  return String(Number(v.toPrecision(6)));
}

function fmtPrice(v) {
  if (v == null) return "—";
  if (v <= 0) return t("free");
  // 逐步提高精度，避免极小价（如 $0.004）显示成 $0.00
  for (const d of [2, 3, 4, 6]) {
    const s = v.toFixed(d);
    if (Number(s) > 0) return `$${s}`;
  }
  return `$${v.toExponential(2)}`;
}

function badge(provider) {
  return ROUTE_CLASS[provider] || "";
}

// 浮窗：inner 上带 data-tip，CSS hover 显示
function tip(inner, help) {
  return help ? `<span class="tip" data-tip="${esc(help)}">${inner}</span>` : inner;
}

function loadUI() {
  try {
    const s = JSON.parse(localStorage.getItem(UI_KEY) || "{}");
    uiState = { order: [], pinned: [], collapsed: [], alpha: 0, cny: false, ...s };
    // 兼容旧版布尔 alpha：true→1(A-Z)，false→0(默认)
    if (uiState.alpha === true) uiState.alpha = 1;
    if (uiState.alpha === false) uiState.alpha = 0;
  } catch {
    uiState = { order: [], pinned: [], collapsed: [], alpha: 0, cny: false };
  }
}
function saveUI() {
  try { localStorage.setItem(UI_KEY, JSON.stringify(uiState)); } catch {}
}

function tagHelp(tag) {
  if (tag.startsWith("额度"))
    return t("tip_quota");
  if (tag.includes("限时×"))
    return t("tip_promo");
  if (tag.startsWith("宣称"))
    return t("tip_claimed");
  if (tag.startsWith("♾️"))
    return t("tip_unlimited");
  if (tag.startsWith("🎁")) {
    const m = tag.match(/(\d+)%off/);
    return t("tip_deal", { pct: m ? m[1] : "?" });
  }
  if (tag === "🔒ZDR") return t("tip_zdr");
  if (/^\d+d$/.test(tag)) return t("tip_retention", { n: tag.slice(0, -1) });
  if (tag === "阶梯") return t("tip_tiered");
  if (tag === "🆓限免") return t("tip_free");
  if (tag === "🌙谷时") return t("tip_offpeak");
  return "";
}

function renderTags(tags) {
  if (!tags || tags.length === 0) return "";
  return tags
    .map((t) => {
      const help = tagHelp(t);
      let cls = "badge-tiny green";
      if (t.startsWith("🎁")) cls = "badge-tiny orange";
      else if (t === "🌙谷时") cls = "badge-tiny blue";
      else if (t === "🔒ZDR") cls = "badge-tiny purple";
      return tip(`<span class="${cls}">${esc(translateTag(t))}</span>`, help);
    })
    .join(" ");
}

// 单个价格格：人民币/美元互斥显示（按钮切换），折扣行划线原价同币种折算
function priceCell(r, kind) {
  const usd = r[kind];
  const list = kind === "prompt" ? r.list_prompt : kind === "completion" ? r.list_completion : null;
  const raw = kind === "prompt" ? r.raw_prompt : kind === "completion" ? r.raw_completion : null;
  const rate = currentFx && currentFx.CNY_per_USD;
  const isDeal = list != null && usd != null && Math.abs(list - usd) > 1e-9;

  // 当前币种值：人民币主显时 CNY 来源用原始人民币价，其余按汇率折算；美元主显直接用 usd
  let val = null;
  if (usd != null && usd > 0) {
    val = uiState.cny
      ? (r.currency === "CNY" && raw != null ? raw : rate ? usd * rate : null)
      : usd;
  }
  const main = usd == null
    ? (r.unlimited && (kind === "prompt" || kind === "completion") ? "♾️" : "—")
    : usd <= 0 ? t("free") : (uiState.cny ? `¥${fmtNum(val)}` : fmtPrice(usd));

  if (!isDeal) return main;

  // 折扣行：划线原价按当前币种折算
  let lval = null;
  if (list != null) {
    lval = uiState.cny
      ? (r.currency === "CNY" ? list : rate ? list * rate : null)
      : list;
  }
  const listMain = lval != null ? (uiState.cny ? `¥${fmtNum(lval)}` : fmtPrice(lval)) : "";
  return `<s class="list">${listMain}</s> ${main}`;
}

// 路线浮窗文案：渠道说明 + 官方API/额度折算/折扣说明 + 官网
function routeTooltip(r) {
  const meta = currentProviderMeta[r.provider] || {};
  const parts = [];
  const note = lang === "en" ? (meta.note_en || meta.note) : meta.note;
  if (note) parts.push(note);
  if (r.route_type === "subscription" && r.quota) {
    const mult = r.quota.tag
      ? translateTag(r.quota.tag)
      : (r.quota.effective_multiplier ? t("quota_mult", { n: r.quota.effective_multiplier }) : "");
    parts.push(
      t("quota_line", {
        list: r.raw_prompt,
        eff: r.prompt,
        mult,
        fee: r.quota.monthly_fee,
        quota: r.quota.monthly_quota,
      })
    );
    // 额度折算精度提示：等效价按当月额度全量消耗计算
    parts.push(t("quota_hint"));
  }
  if (r.is_openrouter_deal && r.list_prompt != null) {
    parts.push(t("deal_line", { list: r.list_prompt, eff: r.prompt }));
  }
  if (meta.url) parts.push(t("route_site") + meta.url);
  return parts.join("\n");
}

function renderProviders(providers) {
  const box = $("#providers");
  if (!providers || Object.keys(providers).length === 0) {
    box.innerHTML = `<span class="status-value">${t("no_data_refresh")}</span>`;
    return;
  }
  box.innerHTML = Object.entries(providers)
    .map(([prov, p]) => `<span class="badge ${badge(esc(prov))}">${esc(plabel(prov, p.label))} · ${Number(p.count) || 0}</span>`)
    .join("");
}

function renderOffpeak(rules) {
  const el = $("#offpeak");
  if (!rules || rules.length === 0) {
    el.textContent = t("offpeak_no_rule");
    return;
  }
  el.innerHTML = rules
    .map((r) => {
      const mark = r.is_offpeak === true ? t("offpeak_on") : r.is_offpeak === false ? t("offpeak_off") : "—";
      return `<span class="status-value">${esc(plabel(r.provider, r.provider_label))}: ${mark}</span>`;
    })
    .join(" · ");
}

function renderDiffs(diffs) {
  const el = $("#diffPanel");
  if (!diffs || !diffs.previous) {
    el.innerHTML = `<div class="empty small">${t("diff_empty_need_two")}</div>`;
    return;
  }
  if (!diffs.changes || diffs.changes.length === 0) {
    el.innerHTML = `<div class="empty small">${t("diff_empty_no_change")}</div>`;
    return;
  }
  const s = diffs.summaries || {};
  const rows = diffs.changes
    .map((c) => {
      const mark =
        c.action === "down" ? "↓" : c.action === "up" ? "↑" : c.action === "new" ? "🆕" : "❌";
      const cls = c.action === "down" ? "down" : c.action === "up" ? "up" : c.action === "new" ? "new" : "gone";
      const pf = c.prompt_from == null ? "—" : `$${c.prompt_from}`;
      const pt = c.prompt_to == null ? "—" : `$${c.prompt_to}`;
      return `<div class="diff-row ${cls}"><span class="diff-mark">${mark}</span> ${esc(c.family || "")} <code>${esc(c.model_id)}</code> <span class="diff-prov">${esc(plabel(c.provider, c.provider_label || c.provider || ""))}</span> ${t("diff_in", { f: pf, t: pt })}</div>`;
    })
    .join("");
  el.innerHTML = `
    <div class="diff-summary">
      <span class="down">${t("diff_down", { n: s.down || 0 })}</span>
      <span class="up">${t("diff_up", { n: s.up || 0 })}</span>
      <span class="new">${t("diff_new", { n: s.new || 0 })}</span>
      <span class="gone">${t("diff_gone", { n: s.gone || 0 })}</span>
    </div>
    ${rows}`;
}

function renderDeals(deals) {
  const el = $("#dealsPanel");
  if (!deals || deals.length === 0) {
    el.innerHTML = `<div class="empty small">${t("deals_empty")}</div>`;
    return;
  }
  const rows = deals
    .map((d) => {
      const m = (d.deal_tag || "").match(/(\d+)%/);
      const pct = m ? m[1] : "?";
      const tag = d.deal_tag ? [d.deal_tag] : [];
      return `
        <div class="deal-row">
          <span class="deal-pct">${pct}% off</span>
          <code class="deal-model">${esc(d.model_id)}</code>
          <span class="deal-family">${esc(d.family || "")}</span>
          <span class="deal-price">${fmtPrice(d.prompt)} / ${fmtPrice(d.completion)}</span>
          <span class="deal-tags">${renderTags(tag)}</span>
        </div>`;
    })
    .join("");
  el.innerHTML = `
    <div class="deal-summary">${t("deals_summary", { n: deals.length })}</div>
    <div class="deal-head"><span>${t("deal_head_off")}</span><span>${t("deal_head_model")}</span><span>${t("deal_head_family")}</span><span style="text-align:right">${t("deal_head_price")}</span><span>${t("deal_head_tags")}</span></div>
    ${rows}`;
}

function sortFamilies(fams) {
  const pinned = uiState.pinned.map((p) => fams.find((f) => f.family === p)).filter(Boolean);
  const pinnedSet = new Set(pinned.map((f) => f.family));
  const rest = fams.filter((f) => !pinnedSet.has(f.family));
  const orderIdx = new Map(uiState.order.map((f, i) => [f, i]));
  rest.sort((a, b) => {
    if (uiState.alpha === 1 || uiState.alpha === 2) {
      const cmp = (a.family_label || a.family).localeCompare(b.family_label || b.family, "zh");
      return uiState.alpha === 1 ? cmp : -cmp;
    }
    const ia = orderIdx.get(a.family);
    const ib = orderIdx.get(b.family);
    if (ia != null && ib != null) return ia - ib;
    if (ia != null) return -1;
    if (ib != null) return 1;
    return 0; // 保持服务器（后端精选）顺序
  });
  return [...pinned, ...rest];
}

function familyCardHTML(fam) {
  const isPinned = uiState.pinned.includes(fam.family);
  const isCollapsed = uiState.collapsed.includes(fam.family);
  const modelRows = (fam.models || []).map(modelBlockHTML).join("");
  return `
    <div class="family-card${isPinned ? " pinned" : ""}${isCollapsed ? " collapsed" : ""}"
         data-family="${esc(fam.family)}" draggable="true">
      <div class="family-head">
        <span class="f-drag" title="拖拽排序">⠿</span>
        <button class="f-pin${isPinned ? " on" : ""}" data-action="pin" title="置顶/取消置顶">📌</button>
        ${brandIcon(fam.family, "f-logo")}
        <span class="f-name">${esc(fam.family_label || fam.family)}</span>
        <span class="f-count">${t("models_count", { n: (fam.models || []).length })}</span>
        <button class="f-collapse" data-action="collapse" title="收起/展开">${isCollapsed ? "▸" : "▾"}</button>
      </div>
      <div class="matrix-head">
        <span>${t("matrix_head_route")}</span>
        <span style="text-align:right">${t("matrix_head_in")}</span>
        <span style="text-align:right">${t("matrix_head_out")}</span>
        <span style="text-align:right">${t("matrix_head_cr")}</span>
        <span style="text-align:right">${t("matrix_head_cw")}</span>
        <span>${t("matrix_head_tags")}</span>
      </div>
      ${modelRows}
    </div>`;
}

function modelBlockHTML(mv) {
  // 模型内各路线按输入价从低到高排序（无价排最后）
  const routes = (mv.routes || []).slice().sort(
    (a, b) => (a.prompt == null ? Infinity : a.prompt) - (b.prompt == null ? Infinity : b.prompt)
  );
  const routeRows = routes.map(routeRowHTML).join("");
  return `
    <div class="model-block">
      <div class="model-head">${brandIcon(mv.family, "m-logo")}<code>${esc(mv.model_id)}</code></div>
      ${routeRows}
    </div>`;
}

function routeRowHTML(r) {
  const t = routeTooltip(r);
  const prov = `<span class="badge ${badge(r.provider)}">${esc(plabel(r.provider, r.provider_label))}</span>`;
  const routeCell = tip(prov, t)
    + (r.source_url ? ` <a class="src" href="${esc(r.source_url)}" target="_blank" rel="noreferrer" title="${esc(r.source_url)}">🔗</a>` : "");
  return `
    <div class="matrix-row">
      <span class="route">${routeCell}</span>
      <span class="price">${priceCell(r, "prompt")}</span>
      <span class="price">${priceCell(r, "completion")}</span>
      <span class="price muted">${priceCell(r, "cache_read")}</span>
      <span class="price muted">${priceCell(r, "cache_write")}</span>
      <span class="tags">${renderTags(r.tags)}</span>
    </div>`;
}

function renderMatrix(matrix) {
  currentMatrix = matrix;
  syncCollapseAllBtn();
  const box = $("#matrixPanel");
  if (!matrix || matrix.length === 0) {
    box.innerHTML = readonlyMode
      ? `<div class="empty"><span class="big">🗂️</span>${t("empty_readonly")}</div>`
      : `<div class="empty"><span class="big">🗂️</span>${t("empty_normal")}</div>`;
    return;
  }
  const sorted = sortFamilies(matrix);
  box.innerHTML = sorted.map(familyCardHTML).join("");
}

function togglePin(fam) {
  const i = uiState.pinned.indexOf(fam);
  if (i >= 0) uiState.pinned.splice(i, 1);
  else uiState.pinned.push(fam);
  saveUI();
  if (currentMatrix) renderMatrix(currentMatrix);
}

function toggleCollapse(fam) {
  const i = uiState.collapsed.indexOf(fam);
  if (i >= 0) uiState.collapsed.splice(i, 1);
  else uiState.collapsed.push(fam);
  saveUI();
  if (currentMatrix) renderMatrix(currentMatrix);
}

// 一键收起/展开（单按钮 toggle）：有折叠的族就全部展开，否则全部收起
function toggleCollapseAll() {
  if (!currentMatrix) return;
  if (uiState.collapsed.length > 0) {
    uiState.collapsed = []; // 展开全部
  } else {
    uiState.collapsed = currentMatrix.map((f) => f.family); // 收起全部
  }
  saveUI();
  renderMatrix(currentMatrix);
}
function syncCollapseAllBtn() {
  const btn = $("#btnCollapseAll");
  if (!btn) return;
  const hasCollapsed = currentMatrix && uiState.collapsed.length > 0;
  btn.textContent = hasCollapsed ? t("expand_all") : t("collapse_all");
  btn.title = hasCollapsed ? t("title_expand") : t("title_collapse");
}

// 字母排序单按钮双向切换：A→Z ⇄ Z→A（首击进入 A→Z；恢复默认靠拖拽或 ↩ 按钮）
function toggleAlpha() {
  uiState.alpha = uiState.alpha === 1 ? 2 : 1; // 0→1(A→Z)，1→2(Z→A)，2→1(A→Z)
  if (uiState.alpha !== 0) uiState.order = []; // 字母序优先，清空自定义顺序
  saveUI();
  syncAlphaBtn();
  if (currentMatrix) renderMatrix(currentMatrix);
}
function syncAlphaBtn() {
  const btn = $("#btnAlpha");
  if (!btn) return;
  btn.textContent = uiState.alpha === 2 ? "🔤 Z→A" : "🔤 A→Z";
  btn.classList.toggle("active", uiState.alpha !== 0);
  btn.title = t("title_alpha");
  const reset = $("#btnAlphaReset");
  if (reset) {
    reset.title = t("title_alpha_reset");
    reset.style.display = uiState.alpha !== 0 ? "" : "none";
  }
}
// 恢复默认顺序（退出字母排序）
function resetAlpha() {
  uiState.alpha = 0;
  saveUI();
  syncAlphaBtn();
  if (currentMatrix) renderMatrix(currentMatrix);
}

// 美元/人民币主显切换（双显始终保留，只换主次）
function toggleCny() {
  uiState.cny = !uiState.cny;
  saveUI();
  syncCnyBtn();
  if (currentMatrix) renderMatrix(currentMatrix);
}
function syncCnyBtn() {
  const btn = $("#btnCny");
  if (!btn) return;
  btn.textContent = uiState.cny ? t("btn_cny") : t("btn_usd");
  btn.classList.toggle("active", uiState.cny);
  btn.title = uiState.cny ? t("title_cny_on") : t("title_cny_off");
}

function reorderFamilies(from, to) {
  if (uiState.alpha !== 0) { uiState.alpha = 0; syncAlphaBtn(); } // 拖动后退出字母排序并同步按钮
  const sorted = sortFamilies(currentMatrix);
  const fams = sorted.map((f) => f.family);
  const fi = fams.indexOf(from);
  const ti = fams.indexOf(to);
  if (fi < 0 || ti < 0) return;
  fams.splice(fi, 1);
  const ni = fams.indexOf(to);
  fams.splice(ni, 0, from);
  const pinnedSet = new Set(uiState.pinned);
  uiState.order = fams.filter((f) => !pinnedSet.has(f));
  saveUI();
}

function setupMatrixEvents() {
  const box = $("#matrixPanel");

  // 置顶 / 折叠（点击族头）
  box.addEventListener("click", (e) => {
    const pinBtn = e.target.closest("[data-action='pin']");
    if (pinBtn) {
      const fam = pinBtn.closest(".family-card").dataset.family;
      togglePin(fam);
      return;
    }
    const colBtn = e.target.closest("[data-action='collapse']");
    const head = e.target.closest(".family-head");
    if (colBtn || head) {
      const card = (colBtn || head).closest(".family-card");
      toggleCollapse(card.dataset.family);
    }
  });

  // 拖拽排序
  box.addEventListener("dragstart", (e) => {
    const card = e.target.closest(".family-card");
    if (!card) return;
    dragFam = card.dataset.family;
    e.dataTransfer.effectAllowed = "move";
  });
  box.addEventListener("dragover", (e) => {
    if (!dragFam) return;
    const card = e.target.closest(".family-card");
    if (card) e.preventDefault();
  });
  box.addEventListener("drop", (e) => {
    e.preventDefault();
    const card = e.target.closest(".family-card");
    if (!card || !dragFam || card.dataset.family === dragFam) {
      dragFam = null;
      return;
    }
    reorderFamilies(dragFam, card.dataset.family);
    dragFam = null;
    if (currentMatrix) renderMatrix(currentMatrix);
  });
  box.addEventListener("dragend", () => { dragFam = null; });
}

async function loadOverview() {
  const res = await fetch("/api/overview");
  const data = await res.json();
  lastOverview = data;
  currentProviderMeta = data.provider_meta || {};
  currentFx = data.fx || null;
  readonlyMode = !!data.readonly;
  cooldownRemaining = Math.max(0, Number(data.fetch_cooldown_remaining) || 0);
  forceCooldownRemaining = Math.max(0, Number(data.force_cooldown_remaining) || 0);
  $("#dataTime").textContent = data.has_data ? (data.fetched_at || "—") : (readonlyMode ? t("no_data_readonly") : t("no_data_click"));
  renderProviders(data.providers);
  renderOffpeak(data.rules);
  renderMatrix(data.matrix);
  renderDiffs(data.diffs);
  renderDeals(data.deals);
  syncRefreshButtons();
  startCooldownTimer();
}

function fmtDur(s) {
  s = Math.max(0, Math.floor(s));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(sec).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

// 依据冷却剩余秒同步刷新按钮：冷却期禁用主按钮并显示倒计时；强刷入口受独立冷却约束
// 只读模式（公开部署）下隐藏全部抓取入口——访客绝不触发爬取
function syncRefreshButtons() {
  const main = $("#btnRefresh");
  const force = $("#btnForce");
  if (!main) return;
  if (readonlyMode) {
    main.style.display = "none";
    if (force) force.style.display = "none";
    return;
  }
  main.style.display = "";
  if (cooldownRemaining > 0) {
    main.disabled = true;
    main.textContent = t("cooling", { n: fmtDur(cooldownRemaining) });
    if (force) {
      force.style.display = "";
      force.title = t("title_force");
      if (forceFetching) {
        force.disabled = true;
        force.textContent = t("force_refreshing");
      } else if (forceCooldownRemaining > 0) {
        force.disabled = true;
        force.textContent = t("force_cooling", { n: fmtDur(forceCooldownRemaining) });
      } else {
        force.disabled = false;
        force.textContent = t("force");
      }
    }
  } else {
    if (fetching) {
      main.disabled = true;
      main.textContent = t("refreshing");
    } else {
      main.disabled = false;
      main.textContent = t("refresh");
    }
    if (force) force.style.display = "none";
  }
}

// 每秒递减冷却倒计时，归零后恢复按钮可点
function startCooldownTimer() {
  if (cooldownTimer) clearInterval(cooldownTimer);
  if (cooldownRemaining <= 0 && forceCooldownRemaining <= 0) return;
  cooldownTimer = setInterval(() => {
    if (cooldownRemaining > 0) cooldownRemaining--;
    if (forceCooldownRemaining > 0) forceCooldownRemaining--;
    syncRefreshButtons();
    if (cooldownRemaining <= 0 && forceCooldownRemaining <= 0) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
    }
  }, 1000);
}

async function refreshPrices() {
  if (readonlyMode) return;
  const btn = $("#btnRefresh");
  fetching = true;
  btn.disabled = true;
  btn.textContent = t("refreshing");
  try {
    const res = await fetch("/api/fetch", { method: "POST" });
    const data = await res.json();
    if (data.skipped && data.reason === "cooldown") {
      cooldownRemaining = Math.max(0, Number(data.cooldown_remaining) || 0);
    }
    if (data.errors && Object.keys(data.errors).length) {
      alert(t("fetch_error") + "\n" + Object.entries(data.errors).map(([k, v]) => `${k}: ${v}`).join("\n"));
    }
    await loadOverview();
  } catch (e) {
    alert(t("fetch_fail") + e.message);
  } finally {
    fetching = false;
    syncRefreshButtons();
  }
}

// 强制刷新（受后端独立强刷冷却约束）
async function forceRefresh() {
  if (readonlyMode) return;
  const btn = $("#btnForce");
  forceFetching = true;
  btn.disabled = true;
  btn.textContent = t("force_refreshing");
  try {
    const res = await fetch("/api/fetch?force=1", { method: "POST" });
    const data = await res.json();
    if (data.skipped && data.reason === "force_cooldown") {
      forceCooldownRemaining = Math.max(0, Number(data.force_cooldown_remaining) || 0);
    }
    if (data.errors && Object.keys(data.errors).length) {
      alert(t("fetch_error") + "\n" + Object.entries(data.errors).map(([k, v]) => `${k}: ${v}`).join("\n"));
    }
    await loadOverview();
  } catch (e) {
    alert(t("force_fetch_fail") + e.message);
  } finally {
    forceFetching = false;
    syncRefreshButtons();
  }
}

function tickClock() {
  const now = new Date();
  $("#now").textContent = now.toLocaleString(lang === "zh" ? "zh-CN" : "en-US", { hour12: false });
}

function setup() {
  loadUI();
  $("#btnRefresh").addEventListener("click", refreshPrices);
  $("#btnForce").addEventListener("click", forceRefresh);
  $("#btnAlpha").addEventListener("click", toggleAlpha);
  $("#btnAlphaReset").addEventListener("click", resetAlpha);
  $("#btnCny").addEventListener("click", toggleCny);
  $("#btnCollapseAll").addEventListener("click", toggleCollapseAll);
  const langBtn = $("#btnLang");
  if (langBtn) langBtn.addEventListener("click", toggleLang);

  // 报头「广告招牌」：点一下钉子松动→招牌垂落晃动，再点恢复原样
  const adBox = $("#adBox");
  if (adBox) {
    const toggleSign = () => {
      adBox.classList.toggle("dropped");
      adBox.setAttribute("aria-pressed", String(adBox.classList.contains("dropped")));
    };
    adBox.addEventListener("click", toggleSign);
    adBox.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleSign(); }
    });
  }

  applyLang();
  syncAlphaBtn();
  syncCnyBtn();
  syncCollapseAllBtn();
  document.querySelectorAll(".tab").forEach((t) => {
    t.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      const tab = t.dataset.tab;
      $("#matrixPanel").style.display = tab === "matrix" ? "" : "none";
      $("#diffPanel").style.display = tab === "diff" ? "" : "none";
      $("#dealsPanel").style.display = tab === "deals" ? "" : "none";
      // 矩阵控制（币种/字母排序/全部收起按钮 + 操作提示）仅比价矩阵页可见；
      // 用 visibility 占位保持面板高度恒定，切换 Tab 时内容不跳
      const ctrl = document.querySelector(".matrix-ctrl");
      if (ctrl) ctrl.style.visibility = tab === "matrix" ? "visible" : "hidden";
      const hint = document.querySelector(".hint");
      if (hint) hint.style.visibility = tab === "matrix" ? "visible" : "hidden";
    });
  });
  setupMatrixEvents();
  tickClock();
  setInterval(tickClock, 1000);
  loadOverview();
}

document.addEventListener("DOMContentLoaded", setup);
