/* Token黄页 — 前端逻辑（原生 JS，无外部依赖） */
"use strict";

const FAMILY_EMOJI = {
  claude: "✳️", kimi: "🪐", glm: "🟦", gpt: "🧠", deepseek: "🔺", qwen: "🐫",
  grok: "🛰️", minimax: "🔮", mimo: "🧬", hy3: "🧪",
};

// 模型族 → 官方商标。两类来源：
//  - 本地 SVG（static/icons/，已下载到本地，离线可用）：openai/zhipu/hunyuan/kimi
//  - Simple Icons CDN（cdn.simpleicons.org）：claude/qwen/deepseek/minimax/x
// 加载失败时自动回退到 FAMILY_EMOJI
const FAMILY_LOCAL_ICON = {
  gpt: "openai",
  glm: "zhipu",
  hy3: "hunyuan",
  kimi: "kimi",
};
const FAMILY_BRAND = {
  claude: "claude",
  qwen: "qwen",
  deepseek: "deepseek",
  minimax: "minimax",
  grok: "x",
};

// 品牌图标：<img> 加载失败时替换为 emoji，保证离线/无 CDN 时也有图标
function brandIcon(family, cls) {
  const emoji = FAMILY_EMOJI[family] || "🧩";
  const local = FAMILY_LOCAL_ICON[family];
  const slug = FAMILY_BRAND[family];
  const src = local ? `/static/icons/${local}.svg` : slug ? `https://cdn.simpleicons.org/${slug}` : null;
  if (!src) return `<span class="${cls}">${emoji}</span>`;
  return (
    `<span class="${cls}">` +
    `<img src="${src}" alt="" loading="lazy" ` +
    `onerror="this.outerHTML='${emoji}'">` +
    `</span>`
  );
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
};

// 折叠/排序/置顶状态（纯本地 localStorage）
const UI_KEY = "tp.matrix.ui";
let uiState = { order: [], pinned: [], collapsed: [], alpha: 0, cny: false };

let currentMatrix = null;
let currentProviderMeta = {};
let currentFx = null; // { CNY_per_USD: 7.2, ... }
let dragFam = null;

// 抓取冷却状态（秒），由 /api/overview 下发，倒计时驱动刷新按钮禁用
let cooldownRemaining = 0;      // 普通刷新冷却剩余
let forceCooldownRemaining = 0; // 强制刷新冷却剩余
let cooldownTimer = null;

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function fmtNum(v) {
  if (v == null) return "—";
  // 保留最多 4 位小数，再经 Number 去掉小数尾零（¥20 → "20"，¥6.50 → "6.5"）
  return String(Number(Number(v).toFixed(4)));
}

function fmtPrice(v) {
  if (v == null) return "—";
  if (v <= 0) return "🆓 免费";
  return v >= 0.005 ? `$${v.toFixed(2)}` : `$${v.toFixed(3)}`;
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
    return "OpenCode Go 订阅额度折算：等效价 = 标价 ÷ 额度倍率（$10/月对应的额度价值）";
  if (tag.includes("限时×"))
    return "OpenCode Go 限时额度促销（2x usage）：该模型当月使用额度翻倍";
  if (tag.startsWith("🎁")) {
    const m = tag.match(/(\d+)%off/);
    const pct = m ? m[1] : "?";
    const zhe = pct !== "?" ? `约 ${(100 - Number(pct)) / 10} 折` : "";
    return `OpenRouter 限时折扣：${pct}% off${zhe ? "（" + zhe + "）" : ""}，显示价已为折扣后价`;
  }
  if (tag === "🔒ZDR") return "零数据保留（ZDR）：数据不用于训练、不保留";
  if (/^\d+d$/.test(tag)) return `数据保留 ${tag.slice(0, -1)} 天`;
  if (tag === "阶梯") return "有阶梯价格：长上下文（超过阈值）单价更高";
  if (tag === "🆓限免") return "免费 / 限时免费提供";
  if (tag === "🌙谷时") return "谷时计价：当前处于折扣时段（如 DeepSeek 谷时半价）";
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
      return tip(`<span class="${cls}">${esc(t)}</span>`, help);
    })
    .join(" ");
}

// 单个价格格：折扣原价划掉 + 美元/人民币双显（切换主显币种，另一种小字随行）
function priceCell(r, kind) {
  const usd = r[kind];
  const list = kind === "prompt" ? r.list_prompt : kind === "completion" ? r.list_completion : null;
  const raw = kind === "prompt" ? r.raw_prompt : kind === "completion" ? r.raw_completion : null;
  const rate = currentFx && currentFx.CNY_per_USD;
  // 人民币小字：CNY 来源用原始人民币价，其余按汇率折算
  let cnyVal = null;
  if (r.currency === "CNY" && raw != null) cnyVal = raw;
  else if (usd != null && usd > 0 && rate) cnyVal = usd * rate;

  let html;
  if (usd != null && usd <= 0) {
    html = "🆓 免费";
  } else if (uiState.cny && cnyVal != null) {
    // 人民币主显，美元小字
    html = `¥${fmtNum(cnyVal)} <small class="usd">${fmtPrice(usd)}</small>`;
  } else {
    html = fmtPrice(usd);
    if (cnyVal != null) html += ` <small class="cny">¥${fmtNum(cnyVal)}</small>`;
  }
  if (list != null && usd != null && Math.abs(list - usd) > 1e-9) {
    html = `<s class="list">${fmtPrice(list)}</s> ${html}`;
  }
  return html;
}

// 路线浮窗文案：渠道说明 + 官方API/额度折算/折扣说明 + 官网
function routeTooltip(r) {
  const meta = currentProviderMeta[r.provider] || {};
  const parts = [];
  if (meta.note) parts.push(meta.note);
  if (r.provider === "opencode_go" && r.quota) {
    const mult = r.quota.tag || (r.quota.effective_multiplier ? `额度×${r.quota.effective_multiplier}` : "");
    parts.push(
      `标价 $${r.raw_prompt} → 等效 $${r.prompt}（${mult}，$${r.quota.monthly_fee}/月 → $${r.quota.monthly_quota} 额度）`
    );
  }
  if (r.is_openrouter_deal && r.list_prompt != null) {
    parts.push(`原价 $${r.list_prompt} → 限时折扣 $${r.prompt}`);
  }
  if (meta.url) parts.push("官网：" + meta.url);
  return parts.join("\n");
}

function renderProviders(providers) {
  const box = $("#providers");
  if (!providers || Object.keys(providers).length === 0) {
    box.innerHTML = `<span class="status-value">（暂无数据，请先刷新）</span>`;
    return;
  }  box.innerHTML = Object.values(providers)
    .map((p) => `<span class="badge ${badge(p.provider)}">${p.label} · ${p.count}</span>`)
    .join("");
}

function renderOffpeak(rules) {
  const el = $("#offpeak");
  if (!rules || rules.length === 0) {
    el.textContent = "无规则";
    return;
  }
  el.innerHTML = rules
    .map((r) => {
      const mark = r.is_offpeak === true ? "🌙 谷时（折扣生效）" : r.is_offpeak === false ? "☀️ 峰时（原价）" : "—";
      return `<span class="status-value">${r.provider_label}: ${mark}</span>`;
    })
    .join(" · ");
}

function renderDiffs(diffs) {
  const el = $("#diffPanel");
  if (!diffs || !diffs.previous) {
    el.innerHTML = `<div class="empty small">暂无涨跌对比：需要至少两次抓取。</div>`;
    return;
  }
  if (!diffs.changes || diffs.changes.length === 0) {
    el.innerHTML = `<div class="empty small">本次抓取与上次相比没有价格变化。</div>`;
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
      return `<div class="diff-row ${cls}"><span class="diff-mark">${mark}</span> ${c.family || ""} ${c.model_id} <span class="diff-prov">${c.provider_label || c.provider}</span> 输入 ${pf}→${pt}</div>`;
    })
    .join("");
  el.innerHTML = `
    <div class="diff-summary">
      <span class="down">↓ 降价 ${s.down || 0}</span>
      <span class="up">↑ 涨价 ${s.up || 0}</span>
      <span class="new">🆕 新上架 ${s.new || 0}</span>
      <span class="gone">❌ 下架 ${s.gone || 0}</span>
    </div>
    ${rows}`;
}

function renderDeals(deals) {
  const el = $("#dealsPanel");
  if (!deals || deals.length === 0) {
    el.innerHTML = `<div class="empty small">暂无限时折扣：请先刷新价格抓取 OpenRouter 折扣。</div>`;
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
    <div class="deal-summary">🎁 共 ${deals.length} 个 OpenRouter 限时折扣（非编程清单；编程清单折扣已并入比价矩阵）</div>
    <div class="deal-head"><span>折扣</span><span>模型</span><span>族</span><span style="text-align:right">输入 / 输出</span><span>标签</span></div>
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
        <span class="f-count">${(fam.models || []).length} 模型</span>
        <button class="f-collapse" data-action="collapse" title="收起/展开">${isCollapsed ? "▸" : "▾"}</button>
      </div>
      <div class="matrix-head">
        <span>路线</span>
        <span style="text-align:right">输入</span>
        <span style="text-align:right">输出</span>
        <span style="text-align:right">缓存读</span>
        <span style="text-align:right">缓存写</span>
        <span>标签 / ZDR</span>
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
  const prov = `<span class="badge ${badge(r.provider)}">${r.provider_label}</span>`;
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
    box.innerHTML = `<div class="empty"><span class="big">🗂️</span>暂无价格数据。<br>点击右上角「刷新价格」开始抓取。</div>`;
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
  btn.textContent = hasCollapsed ? "▾ 全部展开" : "▸ 全部收起";
  btn.title = hasCollapsed ? "一键展开全部模型族" : "一键收起全部模型族";
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
  const reset = $("#btnAlphaReset");
  if (reset) reset.style.display = uiState.alpha !== 0 ? "" : "none";
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
  btn.textContent = uiState.cny ? "¥ 人民币" : "$ 美元";
  btn.classList.toggle("active", uiState.cny);
  btn.title = uiState.cny ? "当前人民币主显（美元小字），点击切换" : "当前美元主显（人民币小字），点击切换";
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
  currentProviderMeta = data.provider_meta || {};
  currentFx = data.fx || null;
  cooldownRemaining = Math.max(0, Number(data.fetch_cooldown_remaining) || 0);
  forceCooldownRemaining = Math.max(0, Number(data.force_cooldown_remaining) || 0);
  $("#dataTime").textContent = data.has_data ? (data.fetched_at || "—") : "（无数据）";
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
function syncRefreshButtons() {
  const main = $("#btnRefresh");
  const force = $("#btnForce");
  if (!main) return;
  if (cooldownRemaining > 0) {
    main.disabled = true;
    main.textContent = `⏳ 冷却 ${fmtDur(cooldownRemaining)}`;
    if (force) {
      force.style.display = "";
      if (forceCooldownRemaining > 0) {
        force.disabled = true;
        force.textContent = `⚡ 强刷 ${fmtDur(forceCooldownRemaining)}`;
      } else {
        force.disabled = false;
        force.textContent = "⚡ 强制刷新";
      }
    }
  } else {
    main.disabled = false;
    main.textContent = "↻ 刷新价格";
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
  const btn = $("#btnRefresh");
  btn.disabled = true;
  btn.textContent = "抓取中…";
  try {
    const res = await fetch("/api/fetch", { method: "POST" });
    const data = await res.json();
    if (data.skipped && data.reason === "cooldown") {
      cooldownRemaining = Math.max(0, Number(data.cooldown_remaining) || 0);
    }
    if (data.errors && Object.keys(data.errors).length) {
      alert("部分站点抓取失败：\n" + Object.entries(data.errors).map(([k, v]) => `${k}: ${v}`).join("\n"));
    }
    await loadOverview();
  } catch (e) {
    alert("抓取失败：" + e.message);
  } finally {
    syncRefreshButtons();
  }
}

// 强制刷新（受后端独立强刷冷却约束）
async function forceRefresh() {
  const btn = $("#btnForce");
  btn.disabled = true;
  btn.textContent = "强制抓取中…";
  try {
    const res = await fetch("/api/fetch?force=1", { method: "POST" });
    const data = await res.json();
    if (data.skipped && data.reason === "force_cooldown") {
      forceCooldownRemaining = Math.max(0, Number(data.force_cooldown_remaining) || 0);
    }
    if (data.errors && Object.keys(data.errors).length) {
      alert("部分站点抓取失败：\n" + Object.entries(data.errors).map(([k, v]) => `${k}: ${v}`).join("\n"));
    }
    await loadOverview();
  } catch (e) {
    alert("强制刷新失败：" + e.message);
  } finally {
    syncRefreshButtons();
  }
}

function tickClock() {
  const now = new Date();
  $("#now").textContent = now.toLocaleString("zh-CN", { hour12: false });
}

function setup() {
  loadUI();
  $("#btnRefresh").addEventListener("click", refreshPrices);
  $("#btnForce").addEventListener("click", forceRefresh);
  $("#btnAlpha").addEventListener("click", toggleAlpha);
  $("#btnAlphaReset").addEventListener("click", resetAlpha);
  $("#btnCny").addEventListener("click", toggleCny);
  $("#btnCollapseAll").addEventListener("click", toggleCollapseAll);
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
