/* ==========================================================================
   小米穿戴固件档案馆 · app.js
   纯原生 JS 单页应用：加载 data.json → 渲染网格 → 搜索/筛选 → 详情抽屉
   Author: hrk_
   ========================================================================== */
"use strict";

(function () {
  /* ---------- 状态 ---------- */
  const state = {
    data: null,
    devices: [],
    cat: "all",
    query: "",
    activeCode: null,
  };

  /* ---------- DOM ---------- */
  const $ = (id) => document.getElementById(id);
  const grid = $("grid");
  const empty = $("empty");
  const loading = $("loading");
  const drawer = $("drawer");
  const drawerBody = $("drawerBody");
  const scrim = $("scrim");
  const toastEl = $("toast");
  const searchInput = $("searchInput");
  const themeToggle = $("themeToggle");

  const CAT_LABEL = { all: "全部", band: "手环", watch: "手表", other: "待确认" };

  /* ---------- 工具 ---------- */
  function fmtSize(bytes) {
    if (!bytes && bytes !== 0) return "–";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB";
    return (bytes / 1073741824).toFixed(2) + " GB";
  }

  function fmtTime(iso) {
    if (!iso) return "–";
    const d = new Date(iso);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  const IMG_EXTS = ["webp", "png", "jpg"];
  function imgSrc(code, ext) {
    return `assets/devices/${code}.${ext}`;
  }
  function imgPath(code) {
    return imgSrc(code, IMG_EXTS[0]);
  }
  // 全局回退：webp → png → jpg → 占位符（供内联 onerror 调用）
  window.imgFallback = function (el) {
    const code = el && el.dataset && el.dataset.code;
    if (!code) { el.outerHTML = '<span class="no-img">⌚</span>'; return; }
    const cur = (el.src.split(".").pop() || "").toLowerCase();
    const idx = IMG_EXTS.indexOf(cur);
    if (idx >= 0 && idx < IMG_EXTS.length - 1) {
      el.src = imgSrc(code, IMG_EXTS[idx + 1]);
    } else {
      el.outerHTML = '<span class="no-img">⌚</span>';
    }
  };

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  let toastTimer = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    requestAnimationFrame(() => toastEl.classList.add("show"));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("show");
      setTimeout(() => { toastEl.hidden = true; }, 300);
    }, 2200);
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(() => true, () => false);
    }
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return Promise.resolve(ok);
    } catch (e) {
      return Promise.resolve(false);
    }
  }

  /* ---------- 渲染：统计 ---------- */
  function renderStats() {
    const d = state.data;
    $("statDevices").textContent = d.device_count;
    $("statReleases").textContent = d.release_count;
    $("statAssets").textContent = d.asset_count;
    let total = 0;
    for (const dev of d.devices) {
      for (const rel of dev.releases) {
        for (const f of rel.full) total += f.size;
        for (const f of rel.incrementals) total += f.size;
      }
    }
    $("statSize").textContent = fmtSize(total).replace(" ", "");
    $("updateTime").textContent = "更新于 " + fmtTime(d.generated_at);
    $("footerTime").textContent = fmtTime(d.generated_at);
  }

  /* ---------- 渲染：卡片网格 ---------- */
  function renderGrid() {
    const q = state.query.trim().toLowerCase();
    const list = state.devices.filter((dev) => {
      if (state.cat !== "all" && dev.category !== state.cat) return false;
      if (!q) return true;
      const hay = (dev.name + " " + dev.code + " " + (dev.note || "")).toLowerCase();
      // 支持空格分隔的多关键词（AND）
      return q.split(/\s+/).every((kw) => hay.includes(kw));
    });

    $("cntAll").textContent = state.devices.length;
    $("cntBand").textContent = state.devices.filter((d) => d.category === "band").length;
    $("cntWatch").textContent = state.devices.filter((d) => d.category === "watch").length;
    $("cntOther").textContent = state.devices.filter((d) => d.category === "other").length;

    empty.hidden = list.length !== 0;
    grid.innerHTML = "";

    list.forEach((dev, i) => {
      const fullCount = dev.releases.reduce((n, r) => n + r.full.length, 0);
      const incrCount = dev.releases.reduce((n, r) => n + r.incrementals.length, 0);
      const latest = dev.releases.length ? dev.releases[0].version : "–";

      const card = document.createElement("div");
      card.className = "card";
      card.style.animationDelay = Math.min(i * 28, 420) + "ms";
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", "查看 " + dev.name + " 详情");
      card.innerHTML = `
        ${dev.confirmed ? "" : '<span class="await-badge">待确认</span>'}
        <div class="card-img">
          <img src="${imgPath(dev.code)}" data-code="${escapeHtml(dev.code)}" alt="${escapeHtml(dev.name)}" loading="lazy"
               onerror="imgFallback(this)">
        </div>
        <div class="card-name">${escapeHtml(dev.name)}</div>
        <div class="card-code">${escapeHtml(dev.code)}</div>
        <div class="card-meta">
          <span class="tag">${CAT_LABEL[dev.category] || dev.category}</span>
          <span class="tag ghost">${latest}</span>
          ${fullCount ? `<span class="tag ok">${fullCount} 全量</span>` : ""}
          ${incrCount ? `<span class="tag">${incrCount} 增量</span>` : ""}
        </div>`;
      card.addEventListener("click", () => openDrawer(dev.code));
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDrawer(dev.code); }
      });
      grid.appendChild(card);
    });
  }

  /* ---------- 渲染：详情抽屉 ---------- */
  function openDrawer(code) {
    const dev = state.devices.find((d) => d.code === code);
    if (!dev) return;
    state.activeCode = code;

    const rels = dev.releases.map((r) => {
      const files = [];
      for (const f of r.full) files.push({ ...f, kind: "full", label: "全量包" });
      for (const f of r.incrementals) files.push({ ...f, kind: "incr", label: "增量包 · from " + f.from });
      return { ...r, files };
    });

    drawerBody.innerHTML = `
      <div class="dw-hero">
        <div class="img">
          <img src="${imgPath(dev.code)}" data-code="${escapeHtml(dev.code)}" alt="${escapeHtml(dev.name)}" loading="lazy"
               onerror="imgFallback(this)">
        </div>
        <div>
          <div class="dw-title">${escapeHtml(dev.name)}</div>
          <div class="dw-code">${escapeHtml(dev.code)}</div>
        </div>
      </div>
      ${dev.note ? `<div class="dw-note">ℹ️ ${escapeHtml(dev.note)}</div>` : ""}
      <div class="dw-section-title">固件版本（${rels.length}）</div>
      ${
        rels.length === 0
          ? '<p style="color:var(--text-3);font-size:13px">暂无固件记录</p>'
          : rels.map((r, ri) => `
        <div class="rel ${ri === 0 ? "open" : ""}" data-ri="${ri}">
          <div class="rel-head" data-ri="${ri}">
            <span class="rel-ver">${escapeHtml(r.version)}</span>
            <span class="rel-count">${r.files.length} 个文件 ▾</span>
          </div>
          <div class="rel-files">
            ${r.files.map((f) => `
              <div class="file-row ${f.kind}">
                <div class="file-meta">
                  <span class="file-type">${f.kind === "full" ? "FULL" : "DELTA"}</span>
                  <span class="file-name">${escapeHtml(f.file)}</span>
                </div>
                <div class="file-actions">
                  <a class="mini-btn primary" href="${escapeHtml(f.url)}" target="_blank" rel="noopener">⬇ 下载 ${fmtSize(f.size)}</a>
                  <button class="mini-btn" data-cmd="gh">gh</button>
                  <button class="mini-btn" data-cmd="curl">curl</button>
                </div>
              </div>`).join("")}
          </div>
        </div>`).join("")
      }`;

    drawerBody.querySelectorAll(".rel-head").forEach((h) => {
      h.addEventListener("click", () => {
        const rel = h.closest(".rel");
        rel.classList.toggle("open");
      });
    });

    drawerBody.querySelectorAll(".mini-btn[data-cmd]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const row = btn.closest(".file-row");
        const file = row.querySelector(".file-name").textContent;
        const url = row.querySelector("a").href;
        const cmd = btn.dataset.cmd === "gh"
          ? `gh release download ${url.split("/releases/download/")[1].split("/")[0]} --repo hrk666666/firmware-archives-public --pattern "${file}"`
          : `curl -LO "${url}"`;
        const ok = await copyText(cmd);
        toast(ok ? "命令已复制到剪贴板 📋" : "复制失败，请手动选择复制");
      });
    });

    scrim.hidden = false;
    drawer.hidden = false;
    requestAnimationFrame(() => {
      scrim.classList.add("show");
      drawer.classList.add("open");
    });
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    scrim.classList.remove("show");
    drawer.classList.remove("open");
    setTimeout(() => {
      scrim.hidden = true;
      drawer.hidden = true;
      document.body.style.overflow = "";
    }, 300);
  }

  /* ---------- 主题 ---------- */
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("fw-theme", theme); } catch (e) {}
  }

  function initTheme() {
    let saved = null;
    try { saved = localStorage.getItem("fw-theme"); } catch (e) {}
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(saved || (prefersDark ? "dark" : "light"));
    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
        if (!localStorage.getItem("fw-theme")) applyTheme(e.matches ? "dark" : "light");
      });
    }
  }

  /* ---------- 事件绑定 ---------- */
  function bindEvents() {
    // 搜索（防抖）
    let t = null;
    searchInput.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => { state.query = searchInput.value; renderGrid(); }, 160);
    });

    // 全局 / 快捷键聚焦搜索
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement !== searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
      if (e.key === "Escape") {
        if (!drawer.hidden) closeDrawer();
        else searchInput.blur();
      }
    });

    // 筛选 chips
    document.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        state.cat = chip.dataset.cat;
        renderGrid();
      });
    });

    // 主题切换
    themeToggle.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(next);
      toast(next === "dark" ? "🌙 已切换深色模式" : "☀️ 已切换浅色模式");
    });

    // 抽屉关闭
    $("drawerClose").addEventListener("click", closeDrawer);
    scrim.addEventListener("click", closeDrawer);
    $("emptyReset").addEventListener("click", () => {
      state.query = "";
      state.cat = "all";
      searchInput.value = "";
      document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c.dataset.cat === "all"));
      renderGrid();
    });
  }

  /* ---------- 启动 ---------- */
  async function init() {
    initTheme();
    bindEvents();
    try {
      const resp = await fetch("data.json", { cache: "no-store" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      state.data = await resp.json();
      state.devices = state.data.devices;
      renderStats();
      renderGrid();
      loading.hidden = true;
      document.title = `小米穿戴固件档案馆 · ${state.data.device_count} 款设备`;
    } catch (e) {
      loading.innerHTML = `<p style="color:var(--danger)">数据加载失败（${escapeHtml(e.message)}）</p>
        <p style="font-size:12px;margin-top:6px">请确认 data.json 存在且格式正确</p>`;
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
