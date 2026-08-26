/**
 * app.js — 小米穿戴固件档案馆（MD3 + 玻璃拟态）
 * 数据源: data.json（GitHub Actions 每日自动同步）
 * 新登记/未确认设备自动置顶展示。
 *
 * v2 修复（2026-08-26）：
 *  - 移除地理位置检测：无论用户在哪个地区，均展示下载引导弹窗与首次访问欢迎弹窗
 *  - 发布说明改为构建期注入 data.json（release.notes），不再依赖运行时 GitHub API（避免限流）
 *  - 复制按钮真实反馈：剪贴板写入失败时提示「复制失败」而非假成功
 *  - Escape 监听不泄漏：关闭弹窗时统一移除 keydown 监听
 *  - 增量包显示真实文件名 + 版本摘要标签
 *  - 夸克按钮提示「打开后搜索文件名」定位具体固件
 *  - 弹窗样式与站点 MD3 橙色主题统一（无渐变、无玻璃，使用设计令牌）
 */
(function () {
  'use strict';

  var THEME_KEY = 'fw-archive-theme';
  var QUARK_SHARE_URL = 'https://pan.quark.cn/s/71ba679b86c3';

  /* ---------- 下载引导弹窗 ---------- */
  function showDownloadModal(filename, githubUrl) {
    // 移除已有弹窗
    var old = document.getElementById('fwModal');
    if (old) old.remove();

    var overlay = document.createElement('div');
    overlay.id = 'fwModal';
    overlay.className = 'modal-overlay';
    overlay.innerHTML =
      '<div class="modal" role="dialog" aria-modal="true" aria-label="下载提示">' +
        '<div class="modal__head">' +
          '<span class="modal__icon">' + icon('cloud') + '</span>' +
          '<h3 class="modal__title">推荐使用夸克网盘下载</h3>' +
        '</div>' +
        '<p class="modal__reason">国内下载速度更快、更稳定。打开夸克网盘后，搜索下方文件名即可定位对应固件。</p>' +
        '<div class="modal__filename">' +
          '<span class="modal__fname-label">文件名</span>' +
          '<div class="modal__fname-row">' +
            '<code class="modal__fname" id="fwModalFname">' + esc(filename) + '</code>' +
            '<button class="modal__copy-btn" id="fwModalCopy" type="button">' + icon('content_copy') + '<span>复制</span></button>' +
          '</div>' +
        '</div>' +
        '<div class="modal__actions">' +
          '<a class="btn btn--primary" href="' + esc(QUARK_SHARE_URL) + '" target="_blank" rel="noopener">' +
            icon('cloud') + ' 打开夸克网盘' +
          '</a>' +
          '<a class="btn btn--outline" href="' + esc(githubUrl) + '" target="_blank" rel="noopener" id="fwModalGithub">' +
            icon('download') + ' 继续使用 GitHub 下载' +
          '</a>' +
        '</div>' +
        '<button class="modal__close" id="fwModalClose" type="button" aria-label="关闭">' + icon('close') + '</button>' +
      '</div>';

    document.body.appendChild(overlay);
    requestAnimationFrame(function () { overlay.classList.add('show'); });

    function closeModal() {
      overlay.classList.remove('show');
      document.removeEventListener('keydown', onKeydown);
      setTimeout(function () { overlay.remove(); }, 300);
    }
    function onKeydown(e) {
      if (e.key === 'Escape') closeModal();
    }
    document.addEventListener('keydown', onKeydown);

    // 自动复制文件名：成功才显示「已复制」，失败提示「复制失败」
    copyToClipboard(filename).then(function (ok) {
      updateCopyBtn('fwModalCopy', ok ? '已复制' : '复制失败');
    });

    // 复制按钮
    document.getElementById('fwModalCopy').addEventListener('click', function () {
      copyToClipboard(filename).then(function (ok) {
        updateCopyBtn('fwModalCopy', ok ? '已复制' : '复制失败');
      });
    });

    // 关闭
    document.getElementById('fwModalClose').addEventListener('click', closeModal);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeModal();
    });
    // GitHub 下载链接也关闭弹窗
    document.getElementById('fwModalGithub').addEventListener('click', function () {
      setTimeout(closeModal, 200);
    });
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text)
        .then(function () { return true; })
        .catch(function () { return fallbackCopy(text); });
    }
    return Promise.resolve(fallbackCopy(text));
  }

  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    ta.remove();
    return ok;
  }

  function updateCopyBtn(id, text) {
    var btn = document.getElementById(id);
    if (!btn) return;
    var span = btn.querySelector('span');
    if (!span) return;
    var orig = span.textContent;
    span.textContent = text;
    btn.classList.add('is-busy');
    setTimeout(function () {
      span.textContent = orig;
      btn.classList.remove('is-busy');
    }, 2000);
  }

  /* ---------- 增量包版本摘要 ---------- */
  function parseIncrSummary(filename, fromVersion, toVersion) {
    // 从文件名或参数解析 from → to
    if (fromVersion && toVersion) return fromVersion + ' → ' + toVersion;
    var m = filename.match(/_from_(v[\d.]+)_/);
    if (m) return m[1] + ' → ' + (toVersion || '?');
    return '';
  }

  /* ---------- 发布说明（构建期注入 data.json，无需运行时 API） ---------- */
  function mdToHtml(body) {
    if (!body) return '';
    return body
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
      .replace(/\n/g, '<br>');
  }

  /* ---------- 首次访问检测 ---------- */
  function isFirstVisit() {
    return !localStorage.getItem('fw-archive-visited');
  }
  function markVisited() {
    localStorage.setItem('fw-archive-visited', '1');
  }

  var CAT_LABEL = { band: '手环', watch: '手表', other: '其他' };
  var filters = { status: 'all', category: 'all', query: '' };
  var state = { data: null, status: 'loading', errorMsg: '' };

  function $(id) { return document.getElementById(id); }

  /* ---------- 工具 ---------- */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function icon(name) {
    return '<svg class="icon" aria-hidden="true"><use href="assets/icons.svg#i-' + esc(name) + '"/></svg>';
  }

  function fmtSize(bytes) {
    if (bytes == null) return '';
    if (bytes >= 1e9) return (bytes / 1e9).toFixed(2) + ' GB';
    if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + ' MB';
    if (bytes >= 1e3) return (bytes / 1e3).toFixed(0) + ' KB';
    return bytes + ' B';
  }

  function fmtTime(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  /* ---------- 主题 ---------- */

  function currentTheme() {
    var s = localStorage.getItem(THEME_KEY);
    if (s === 'light' || s === 'dark') return s;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    var btn = $('themeToggle');
    var next = t === 'dark' ? 'light' : 'dark';
    btn.setAttribute('aria-label', next === 'dark' ? '切换到深色模式' : '切换到浅色模式');
    btn.title = next === 'dark' ? '切换到深色模式' : '切换到浅色模式';
    btn.innerHTML = icon(next === 'dark' ? 'dark_mode' : 'light_mode');
  }

  /* ---------- 数据 ---------- */

  function load() {
    state.status = 'loading';
    return fetch('data.json', { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        state.data = d;
        state.status = 'ready';
      })
      .catch(function (e) {
        state.status = 'error';
        state.errorMsg = String(e && e.message ? e.message : e);
      });
  }

  function imgPath(code, ext) {
    return 'assets/devices/' + encodeURIComponent(code) + '.' + ext;
  }

  function imgMarkup(code, alt) {
    // 回退链: webp -> png -> jpg -> 隐藏（露出占位图标）
    // onload 加 loaded（CSS 不透明背景遮住底层 SVG）；onerror 链走完隐藏 img
    return (
      '<img src="' + imgPath(code, 'webp') + '" alt="' + esc(alt) + '" loading="lazy"' +
      ' data-exts="webp,png,jpg" data-fb="0"' +
      ' onload="this.classList.add(\'loaded\')"' +
      ' onerror="var fb=+this.dataset.fb+1;this.dataset.fb=fb;' +
      'var ext=this.dataset.exts.split(\',\')[fb];' +
      'if(ext){this.src=this.src.replace(/\\.[a-z]+$/,\'.\'+ext)}else{this.style.display=\'none\';this.classList.add(\'no-img\')}">'
    );
  }

  function totalSizeBytes(data) {
    var sum = 0;
    data.devices.forEach(function (d) {
      d.releases.forEach(function (r) {
        (r.full || []).forEach(function (f) { sum += f.size || 0; });
        (r.incrementals || []).forEach(function (f) { sum += f.size || 0; });
      });
    });
    return sum;
  }

  function latestVersion(dev) {
    return dev.releases && dev.releases.length ? dev.releases[0].version : '';
  }

  /* ---------- 渲染：统计 ---------- */

  function renderStats() {
    var d = state.data;
    var tiles = [
      { icon: 'devices', value: String(d.device_count), label: '设备' },
      { icon: 'update', value: String(d.release_count), label: '固件版本' },
      { icon: 'download', value: String(d.asset_count), label: '安装包' },
      { icon: 'storage', value: fmtSize(totalSizeBytes(d)), label: '归档体积', small: true }
    ];
    $('stats').innerHTML = tiles.map(function (t, i) {
      return (
        '<div class="stat glass reveal">' +
        '<span class="stat__icon' + (i === 0 ? ' stat__icon--new' : '') + '">' + icon(t.icon) + '</span>' +
        '<span class="stat__value' + (t.small ? ' stat__value--small' : '') + '">' + esc(t.value) + '</span>' +
        '<span class="stat__label">' + esc(t.label) + '</span>' +
        '</div>'
      );
    }).join('');
  }

  /* ---------- 渲染：筛选芯片 ---------- */

  function renderChips() {
    var d = state.data;
    var unconfirmed = d.devices.filter(function (x) { return !x.confirmed; }).length;
    var statusItems = [
      { id: 'all', label: '全部', count: d.devices.length },
      { id: 'new', label: '新设备', count: unconfirmed }
    ];
    $('statusChips').innerHTML = statusItems.map(function (it) {
      return chipHtml(it.id, it.label, it.count, filters.status === it.id);
    }).join('');

    var cats = ['all'];
    d.devices.forEach(function (x) {
      if (cats.indexOf(x.category) === -1) cats.push(x.category);
    });
    $('categoryChips').innerHTML = cats.map(function (c) {
      var label = c === 'all' ? '全部类型' : (CAT_LABEL[c] || c);
      var count = c === 'all' ? null : d.devices.filter(function (x) { return x.category === c; }).length;
      return chipHtml('cat-' + c, label, count, filters.category === c);
    }).join('');
  }

  function chipHtml(id, label, count, pressed) {
    return (
      '<button class="chip' + (pressed ? ' is-selected' : '') + '" data-chip="' + esc(id) + '" aria-pressed="' + (pressed ? 'true' : 'false') + '">' +
      '<span class="chip__check">' + icon('check') + '</span>' +
      '<span>' + esc(label) + '</span>' +
      (count != null ? '<span class="chip__count">' + count + '</span>' : '') +
      '</button>'
    );
  }

  /* ---------- 渲染：设备卡 ---------- */

  function deviceCard(dev, delay) {
    var latest = latestVersion(dev);
    var fullCount = 0, incrCount = 0;
    dev.releases.forEach(function (r) {
      fullCount += (r.full || []).length;
      incrCount += (r.incrementals || []).length;
    });
    var catLabel = CAT_LABEL[dev.category] || dev.category;
    var tags =
      '<span class="cat-tag">' + esc(catLabel) + '</span>' +
      (latest ? '<span class="badge badge--ok">' + esc(latest) + '</span>' : '') +
      (fullCount ? '<span class="badge badge--info">' + fullCount + ' 全量</span>' : '') +
      (incrCount ? '<span class="badge">' + incrCount + ' 增量</span>' : '');

    return (
      '<article class="device-card glass reveal' + (dev.confirmed ? '' : ' is-new') + '" style="transition-delay:' + delay + 'ms" tabindex="0" role="button" data-code="' + esc(dev.code) + '">' +
      '<div class="device-card__head">' +
      '<span class="device-card__img">' + icon('devices') + imgMarkup(dev.code, dev.name) + '</span>' +
      '<div style="min-width:0">' +
      '<div class="device-card__name">' + esc(dev.name) +
      (dev.confirmed ? '' : '<span class="badge badge--new">新设备</span>') +
      '</div>' +
      '<div class="device-card__full">' + esc(dev.code) + '</div>' +
      '</div>' +
      '</div>' +
      '<div class="device-card__fw">' +
      '<span class="fw-label">最新固件</span>' +
      '<span class="fw-version">' + esc(latest || '—') + '</span>' +
      '<span class="fw-date">' + icon('schedule') + (dev.releases.length ? dev.releases.length + ' 个版本' : '暂无版本') + '</span>' +
      '</div>' +
      '<div class="device-card__foot">' + tags + '</div>' +
      '</article>'
    );
  }

  function renderGrid(devices, container, startDelay) {
    container.innerHTML = devices
      .map(function (d, i) { return deviceCard(d, Math.min((startDelay || 0) + i * 30, 260)); })
      .join('');
  }

  /* ---------- 渲染：其他设备折叠区（待确认，默认收起，懒渲染） ---------- */

  function renderCollapseHtml(devices) {
    return (
      '<section class="collapse" id="otherCollapse">' +
      '<button class="collapse__head" id="collapseHead" type="button" aria-expanded="false" aria-controls="collapseBody">' +
      '<span class="collapse__title">' + icon('fiber_new') + '<span>其他设备 · 待确认</span></span>' +
      '<span class="collapse__sub">新登记、尚未确认的未知设备</span>' +
      '<span class="collapse__count">' + devices.length + '</span>' +
      '<span class="collapse__chevron">' + icon('keyboard_arrow_down') + '</span>' +
      '</button>' +
      '<div class="collapse__body" id="collapseBody"></div>' +
      '</section>'
    );
  }

  function wireCollapse() {
    var head = $('collapseHead');
    var box = $('otherCollapse');
    var body = $('collapseBody');
    if (!head || !box) return;
    head.addEventListener('click', function () {
      var open = head.getAttribute('aria-expanded') === 'true';
      head.setAttribute('aria-expanded', String(!open));
      box.classList.toggle('open', !open);
      if (!open && !body.dataset.rendered) {
        var devices = state.data.devices.filter(function (x) { return !x.confirmed; });
        body.innerHTML = '<div class="device-grid">' +
          devices.map(function (d, i) { return deviceCard(d, Math.min(i * 25, 200)); }).join('') +
          '</div>';
        body.dataset.rendered = '1';
        initReveal(body);
      }
    });
  }

  /* ---------- 渲染：主列表 ---------- */

  function filterDevices() {
    var all = state.data.devices;
    return all.filter(function (d) {
      if (filters.status === 'new' && d.confirmed) return false;
      if (filters.category !== 'all' && d.category !== filters.category) return false;
      if (filters.query) {
        var q = filters.query.toLowerCase();
        var hay = (d.name + ' ' + d.code + ' ' + (d.note || '')).toLowerCase();
        var ver = (d.releases[0] && d.releases[0].version || '').toLowerCase();
        if (hay.indexOf(q) === -1 && ver.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  function renderAll() {
    var content = $('content');

    if (state.status === 'error') {
      content.innerHTML =
        '<div class="state glass" role="alert">' +
        '<span class="state__icon">' + icon('error') + '</span>' +
        '<h3 class="state__title">数据加载失败</h3>' +
        '<p class="state__desc">无法读取 data.json（' + esc(state.errorMsg) + '）。请确认数据文件存在，或稍后重试。</p>' +
        '<button class="filled-button" id="retryBtn" type="button">' + icon('refresh') + ' 重试</button>' +
        '</div>';
      $('retryBtn').addEventListener('click', reload);
      return;
    }
    if (state.status === 'loading') {
      content.innerHTML = skeleton(6);
      return;
    }

    var d = state.data;
    renderStats();
    renderChips();
    renderFooter(d);
    renderSyncChip(d);

    // 默认视图：已确认设备网格 + 底部「其他设备」折叠区（待确认设备不置顶）
    var isDefault = filters.status === 'all' && filters.category === 'all' && !filters.query;
    var unconfirmed = d.devices.filter(function (x) { return !x.confirmed; });
    var list = isDefault ? d.devices.filter(function (x) { return x.confirmed; }) : filterDevices();

    var html =
      '<section class="section" id="listSection">' +
      '<div class="section__head">' +
      '<div>' +
      '<h2 class="section__title">' + (isDefault ? '全部设备' : '筛选结果') + '</h2>' +
      '<p class="section__sub">' + (isDefault
        ? (unconfirmed.length ? '已确认设备在此展示；待确认的未知设备在下方折叠区。' : '按数据登记顺序展示。')
        : '已按当前条件筛选。') + '</p>' +
      '</div>' +
      '<span class="section__count">' + list.length + ' 台</span>' +
      '</div>' +
      '<div class="device-grid" id="deviceGrid"></div>' +
      '</section>';
    content.innerHTML = html;

    var grid = $('deviceGrid');
    if (list.length) {
      renderGrid(list, grid, 0);
    } else {
      grid.innerHTML = emptyState(isDefault ? false : true);
      var clearBtn = $('clearFilterBtn');
      if (clearBtn) clearBtn.addEventListener('click', function () {
        filters.status = 'all';
        filters.category = 'all';
        filters.query = '';
        $('searchInput').value = '';
        syncChips();
        renderAll();
      });
    }

    // 底部折叠区（仅默认视图显示）
    if (isDefault && unconfirmed.length) {
      $('listSection').insertAdjacentHTML('afterend', renderCollapseHtml(unconfirmed));
      wireCollapse();
    }
    initReveal(content);
  }

  function skeleton(count) {
    var html = '<div class="device-grid" role="status" aria-label="加载中">';
    for (var i = 0; i < count; i++) {
      html +=
        '<div class="skeleton">' +
        '<div class="skeleton__row">' +
        '<div class="skeleton__box"></div>' +
        '<div style="flex:1;display:flex;flex-direction:column;gap:8px">' +
        '<div class="skeleton__line skeleton__line--w60 skeleton__line--h24"></div>' +
        '<div class="skeleton__line skeleton__line--w40"></div>' +
        '</div>' +
        '</div>' +
        '<div class="skeleton__line skeleton__line--w80"></div>' +
        '<div class="skeleton__line"></div>' +
        '</div>';
    }
    return html + '</div>';
  }

  function emptyState(hasFilter) {
    return (
      '<div class="state glass">' +
      '<span class="state__icon">' + icon('search') + '</span>' +
      '<h3 class="state__title">没有匹配的设备</h3>' +
      '<p class="state__desc">' + (hasFilter ? '换个筛选条件或关键字试试。' : '暂无可展示的设备。') + '</p>' +
      (hasFilter ? '<button class="filled-button" id="clearFilterBtn" type="button">清除筛选</button>' : '') +
      '</div>'
    );
  }

  /* ---------- 页脚 / 同步时间 ---------- */

  function renderFooter(d) {
    var el = $('footerLine');
    var parts = [];
    if (d.generated_at) parts.push('数据更新于 ' + fmtTime(d.generated_at));
    if (d.source_repo) parts.push('来源 ' + esc(d.source_repo));
    el.textContent = parts.join(' · ');
  }

  function renderSyncChip(d) {
    var chip = $('syncChip');
    var text = $('syncChipText');
    if (!chip || !text) return;
    if (d.generated_at) {
      text.textContent = '同步于 ' + fmtTime(d.generated_at);
      chip.hidden = false;
    } else {
      chip.hidden = true;
    }
  }

  /* ---------- 详情抽屉 ---------- */

  function openDrawer(code) {
    var dev = state.data.devices.find(function (x) { return x.code === code; });
    if (!dev) return;

    var rels = dev.releases.map(function (r) {
      var files = [];
      (r.full || []).forEach(function (f) { files.push({ file: f.file, size: f.size, url: f.url, kind: 'full', label: '全量包', summary: '' }); });
      (r.incrementals || []).forEach(function (f) {
        var summary = parseIncrSummary(f.file, f.from, r.version);
        files.push({ file: f.file, size: f.size, url: f.url, kind: 'delta', label: '增量包 · ' + summary, summary: summary });
      });
      return { version: r.version, notes: r.notes || '', files: files };
    });

    // 渲染基础内容
    $('drawerBody').innerHTML =
      '<div class="dw-hero">' +
      '<div class="dw-img">' + icon('devices') + imgMarkup(dev.code, dev.name) + '</div>' +
      '<div>' +
      '<div class="dw-title">' + esc(dev.name) + (dev.confirmed ? '' : ' <span class="badge badge--new">新设备</span>') + '</div>' +
      '<div class="dw-code">' + esc(dev.code) + ' · ' + esc(CAT_LABEL[dev.category] || dev.category) + '</div>' +
      '</div>' +
      '</div>' +
      (dev.note ? '<div class="dw-note">' + icon('info') + '<span>' + esc(dev.note) + '</span></div>' : '') +
      '<div class="dw-section-title">' + icon('history') + ' 固件版本（' + rels.length + '）</div>' +
      (rels.length === 0
        ? '<p style="color:var(--md-on-surface-variant);font-size:13px">暂无固件记录</p>'
        : rels.map(function (r) {
          // 增量包摘要行
          var deltaFiles = r.files.filter(function (f) { return f.kind === 'delta'; });
          var deltaSummaryHtml = '';
          if (deltaFiles.length > 0) {
            deltaSummaryHtml = '<div class="rel-deltas">' +
              deltaFiles.map(function (f) {
                return '<span class="rel-delta-tag">' + esc(f.summary) + '</span>';
              }).join('') +
              '</div>';
          }
          // 发布说明：构建期注入，直接展示
          var notesHtml = r.notes
            ? '<div class="rel-notes"><div class="rel-notes-body">' + mdToHtml(r.notes) + '</div></div>'
            : '';
          return (
            '<div class="rel" data-ver="' + esc(r.version) + '">' +
            '<div class="rel-head">' +
            '<span class="rel-ver">' + esc(r.version) + '</span>' +
            '<span class="rel-count">' + r.files.length + ' 个文件 ' + icon('keyboard_arrow_down') + '</span>' +
            '</div>' +
            notesHtml +
            deltaSummaryHtml +
            '<div class="rel-files">' +
            r.files.map(function (f) {
              // 显示真实文件名 + 版本摘要标签
              var summaryTag = f.kind === 'delta' && f.summary
                ? '<span class="file-summary">' + esc(f.summary) + '</span>'
                : '';
              return (
                '<div class="file-row">' +
                '<div class="file-meta">' +
                '<span class="file-type ' + f.kind + '">' + (f.kind === 'full' ? 'FULL' : 'DELTA') + '</span>' +
                '<span class="file-name" title="' + esc(f.file) + '">' + esc(f.file) + summaryTag + '</span>' +
                '<span class="file-size">' + fmtSize(f.size) + '</span>' +
                '</div>' +
                '<div class="file-actions">' +
                '<a class="mini-btn quark-btn" href="' + esc(QUARK_SHARE_URL) + '" target="_blank" rel="noopener" title="打开夸克网盘后搜索：' + esc(f.file) + '">' + icon('cloud') + ' 夸克</a>' +
                '<button class="mini-btn primary dl-intercept" data-file="' + esc(f.file) + '" data-url="' + esc(f.url) + '" type="button">' + icon('download') + ' 下载</button>' +
                '</div>' +
                '</div>'
              );
            }).join('') +
            '</div>' +
            '</div>'
          );
        }).join(''));

    // 展开/收起版本
    $('drawerBody').querySelectorAll('.rel-head').forEach(function (h) {
      h.addEventListener('click', function () {
        var rel = h.closest('.rel');
        rel.classList.toggle('open');
      });
    });

    // 下载按钮：无论地理位置，一律弹出下载引导
    $('drawerBody').querySelectorAll('.dl-intercept').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        showDownloadModal(btn.getAttribute('data-file'), btn.getAttribute('data-url'));
      });
    });

    $('scrim').hidden = false;
    $('drawer').hidden = false;
    requestAnimationFrame(function () {
      $('scrim').classList.add('show');
      $('drawer').classList.add('open');
    });
    document.body.style.overflow = 'hidden';
    $('drawerClose').focus();
  }

  function closeDrawer() {
    $('scrim').classList.remove('show');
    $('drawer').classList.remove('open');
    setTimeout(function () {
      $('scrim').hidden = true;
      $('drawer').hidden = true;
      document.body.style.overflow = '';
    }, 300);
  }

  /* ---------- 交互 ---------- */

  function syncChips() {
    document.querySelectorAll('[data-chip]').forEach(function (btn) {
      var id = btn.getAttribute('data-chip');
      var pressed;
      if (id.indexOf('cat-') === 0) pressed = filters.category === id.slice(4);
      else pressed = filters.status === id;
      btn.setAttribute('aria-pressed', pressed ? 'true' : 'false');
      btn.classList.toggle('is-selected', pressed);
    });
  }

  function wireEvents() {
    $('statusChips').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-chip]');
      if (!btn) return;
      filters.status = btn.getAttribute('data-chip');
      syncChips();
      renderAll();
    });

    $('categoryChips').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-chip]');
      if (!btn) return;
      filters.category = btn.getAttribute('data-chip').slice(4);
      syncChips();
      renderAll();
    });

    var search = $('searchInput');
    var debounce = null;
    search.addEventListener('input', function () {
      clearTimeout(debounce);
      var q = search.value.trim();
      debounce = setTimeout(function () {
        filters.query = q;
        renderAll();
      }, 200);
    });

    $('content').addEventListener('click', function (e) {
      var card = e.target.closest('.device-card');
      if (card) openDrawer(card.getAttribute('data-code'));
    });
    $('content').addEventListener('keydown', function (e) {
      if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('device-card')) {
        e.preventDefault();
        openDrawer(e.target.getAttribute('data-code'));
      }
    });

    $('refreshBtn').addEventListener('click', reload);
    $('scrim').addEventListener('click', closeDrawer);
    $('drawerClose').addEventListener('click', closeDrawer);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !$('drawer').hidden) closeDrawer();
    });
  }

  function initReveal(root) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var els = (root || document).querySelectorAll('.reveal:not(.is-in)');
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add('is-in');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -24px 0px' }
    );
    els.forEach(function (el) { io.observe(el); });
  }

  function reload() {
    var btn = $('refreshBtn');
    btn.classList.add('is-spinning');
    load().then(function () {
      renderAll();
      btn.classList.remove('is-spinning');
    });
  }

  /* ---------- 启动 ---------- */

  function boot() {
    applyTheme(currentTheme());
    $('themeToggle').addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
    wireEvents();
    renderAll();
    load().then(function () {
      renderAll();
      initReveal(document.body);
      // 首次访问欢迎弹窗：无论地理位置，首次访问一律展示
      if (isFirstVisit()) {
        markVisited();
        setTimeout(function () {
          showWelcomeModal();
        }, 800);
      }
    });
  }

  /* ---------- 首次访问欢迎弹窗 ---------- */
  function showWelcomeModal() {
    var old = document.getElementById('fwModal');
    if (old) old.remove();

    var overlay = document.createElement('div');
    overlay.id = 'fwModal';
    overlay.className = 'modal-overlay';
    overlay.innerHTML =
      '<div class="modal" role="dialog" aria-modal="true" aria-label="欢迎">' +
        '<div class="modal__head">' +
          '<span class="modal__icon">' + icon('cloud') + '</span>' +
          '<h3 class="modal__title">推荐使用夸克网盘下载固件</h3>' +
        '</div>' +
        '<p class="modal__reason">国内下载速度更快、更稳定，支持夸克 APP 直接搜索和下载固件文件。打开夸克网盘后，搜索文件名即可定位对应固件。</p>' +
        '<div class="modal__actions">' +
          '<a class="btn btn--primary" href="' + esc(QUARK_SHARE_URL) + '" target="_blank" rel="noopener">' +
            icon('cloud') + ' 打开夸克网盘' +
          '</a>' +
          '<button class="btn btn--outline" id="welcomeClose" type="button">' +
            icon('check') + ' 我知道了，继续浏览' +
          '</button>' +
        '</div>' +
        '<button class="modal__close" id="fwModalClose" type="button" aria-label="关闭">' + icon('close') + '</button>' +
      '</div>';

    document.body.appendChild(overlay);
    requestAnimationFrame(function () { overlay.classList.add('show'); });

    function closeModal() {
      overlay.classList.remove('show');
      document.removeEventListener('keydown', onKeydown);
      setTimeout(function () { overlay.remove(); }, 300);
    }
    function onKeydown(e) {
      if (e.key === 'Escape') closeModal();
    }
    document.addEventListener('keydown', onKeydown);

    document.getElementById('fwModalClose').addEventListener('click', closeModal);
    document.getElementById('welcomeClose').addEventListener('click', closeModal);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeModal();
    });
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
