/* 法令三段表ビューア
   #sdApp[data-src] の JSON（scripts/build_sandan.py が生成）を3列で描画する。
   各列は独立してスクロールでき、操作中の列の「いま読んでいる法の条」に
   他の列が自動で追従する（連動スクロール）。 */
(function () {
  "use strict";
  var app = document.getElementById("sdApp");
  if (!app) return;
  var COLS = ["law", "ord", "reg"];
  var PFX = { law: "h", ord: "o", reg: "r" };
  var KN = "〇一二三四五六七八九十百千";
  // 先頭グループ = 直前の文字（漢字なら他法令の引用なので対象外）
  var RE = new RegExp("(^|[^\\u3400-\\u9fff々〆])(法|令)(?:(別表)|第([" + KN + "]+)条((?:の[" + KN + "]+)*))" +
    "|((?:政令|主務省令|内閣府令|命令)で定め)" +
    "|(^|[^\\u3400-\\u9fff々〆同])(別表)", "g");

  var data, rowsInfo = [], has = { law: {}, ord: {}, reg: {} }, titles = { ord: {}, reg: {} };
  var panes = {}, activeKey = null, syncOn = true, narrow = false, narrowCol = "law";
  // 第三段に複数の府令がある場合（資金決済法など）
  var multi = false, regInfo = {}, regOn = {};
  var SRC_BG = ["#fde2ec", "#dff3e2", "#e1ebfb", "#fbeed3", "#ece3f8", "#d9f1f2", "#f4e4d6", "#e9ecef"];
  var SRC_FG = ["#a8325f", "#2c7a3c", "#2a4ea6", "#8a5a00", "#6a3fa0", "#1d6f73", "#8a4a1d", "#4a4f57"];
  function srcBadge(key) {
    var r = regInfo[key];
    if (!r) return "";
    return '<span class="src" style="background:' + SRC_BG[r.i % 8] + ";color:" + SRC_FG[r.i % 8] + ";border-color:" + SRC_FG[r.i % 8] + '">' + esc(r.short) + "</span>";
  }
  var qEl, onlyEl, cntEl, jumpEl, syncEl, panesEl;

  /* ---------- 文字列ユーティリティ ---------- */
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function norm(s) {
    try { return String(s).normalize("NFKC"); } catch (e) { return String(s); }
  }
  function k2i(s) {
    var dg = { "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9 };
    var un = { "十": 10, "百": 100, "千": 1000 }, total = 0, cur = 0;
    for (var i = 0; i < s.length; i++) {
      var ch = s.charAt(i);
      if (ch in dg) cur = dg[ch];
      else if (ch in un) { total += (cur || 1) * un[ch]; cur = 0; }
    }
    return total + cur;
  }
  function refKey(ap, num, nos) {
    if (ap) return "appdx";
    var k = String(k2i(num));
    if (nos) nos.split("の").forEach(function (x) { if (x) k += "_" + k2i(x); });
    return k;
  }
  function kLabel(k) {
    if (k.indexOf("appdx") === 0) return "別表";
    var p = k.split("_");
    return p[0] + "条" + p.slice(1).map(function (x) { return "の" + x; }).join("");
  }
  // "2025-06-01" → "令和7年6月1日"
  function wareki(ymd) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ymd || "");
    if (!m) return ymd || "";
    var y = +m[1], md = +(m[2] + m[3]), era, ey;
    if (y > 2019 || (y === 2019 && md >= 501)) { era = "令和"; ey = y - 2018; }
    else if (y > 1989 || (y === 1989 && md >= 108)) { era = "平成"; ey = y - 1988; }
    else { era = "昭和"; ey = y - 1925; }
    return era + (ey === 1 ? "元" : ey) + "年" + (+m[2]) + "月" + (+m[3]) + "日";
  }

  /* ---------- 条文の描画 ---------- */
  function deco(s, col) {
    return esc(s).replace(RE, function (m, pre, kind, ap, num, nos, dg, pre2, selfAp) {
      if (dg) {
        var o = dg.indexOf("政令") === 0;
        return '<mark class="dg ' + (o ? "dg-o" : "dg-r") + '" title="クリックで' + (o ? "施行令" : "施行規則") + 'の該当箇所へ">' + dg + "</mark>";
      }
      if (selfAp) { // 法の本文中の「別表」→ 法の別表
        return col === "law" && has.law.appdx ? (pre2 || "") + '<a class="ref rl" href="#h-appdx">別表</a>' : m;
      }
      pre = pre || "";
      var body = m.slice(pre.length), key = refKey(ap, num, nos);
      if (col === "law") return m;
      if (kind === "法" && has.law[key]) return pre + '<a class="ref rl" href="#h-' + key + '">' + body + "</a>";
      if (kind === "令" && col === "reg" && has.ord[key]) return pre + '<a class="ref ro" href="#o-' + key + '">' + body + "</a>";
      return m;
    });
  }
  function tableHTML(head, rws, col) {
    return '<div class="tblw"><table class="ltbl">' + rws.map(function (r, i) {
      var tag = i < head ? "th" : "td";
      return "<tr>" + r.map(function (c) { return "<" + tag + ">" + deco(c, col) + "</" + tag + ">"; }).join("") + "</tr>";
    }).join("") + "</table></div>";
  }
  function linesHTML(L, col) {
    return (L || []).map(function (ln) {
      var k = ln[0];
      if (k === "tbl") return tableHTML(ln[1], ln[2], col);
      if (k === "cap") return '<p class="ln cap">' + deco(ln[2], col) + "</p>";
      if (k === "note") return '<p class="ln note">' + esc(ln[2]) + "</p>";
      return '<p class="ln ' + k + '">' + (ln[1] ? '<span class="lb">' + esc(ln[1]) + "</span>" : "") + deco(ln[2], col) + "</p>";
    }).join("");
  }
  function chips(a) {
    var out = [];
    (a.r || []).forEach(function (k) {
      if (has.law[k]) out.push('<a class="chip cl" href="#h-' + k + '">法' + kLabel(k) + "</a>");
    });
    (a.o || []).forEach(function (k) {
      if (has.ord[k]) out.push('<a class="chip co" href="#o-' + k + '">令' + kLabel(k) + "</a>");
    });
    if (a.n) out.push('<span class="chip cn" title="条文中に法・令の条の引用がないため、直前の条と同じまとまりに置いています">引用なし</span>');
    return out.join(" ");
  }
  function artHTML(a, col, rowK) {
    var id = PFX[col] + "-" + a.k;
    var h = '<article class="art" id="' + id + '" data-k="' + rowK + '"' + (a.s ? ' data-s="' + a.s + '"' : "") + '><header class="ah">' +
      (a.s ? srcBadge(a.s) : "") + '<a class="at" href="#' + id + '">' + esc(a.t) + "</a>" +
      (a.c ? '<span class="ac">' + esc(a.c) + "</span>" : "") + (col === "law" ? "" : chips(a)) + "</header>";
    h += '<div class="ab">' + linesHTML(a.L, col);
    (a.sub || []).forEach(function (s) {
      h += '<div class="sub-appdx"><div class="st">' + esc(s.t) + (s.c ? " " + esc(s.c) : "") + "</div>" + linesHTML(s.L, col) + "</div>";
    });
    return h + "</div></article>";
  }
  function relHTML(keys, col) {
    if (!keys || !keys.length) return "";
    return '<div class="rel">このほか関連する条（別のまとまりに掲載）：' + keys.map(function (k) {
      var src = col === "reg" && multi ? ' data-s="' + k.split("-")[0] + '"' : "";
      return '<a href="#' + PFX[col] + "-" + k + '"' + src + ">" + esc(titles[col][k] || kLabel(k)) + "</a>";
    }).join("<i>、</i>") + "</div>";
  }
  function plain(a) {
    var out = [a.t, a.c || ""];
    var L = (a.L || []).slice();
    (a.sub || []).forEach(function (s) { L.push([0, 0, s.t]); L = L.concat(s.L); });
    L.forEach(function (ln) { out.push(ln[0] === "tbl" ? ln[2].map(function (r) { return r.join(" "); }).join(" ") : ln[2]); });
    return out.join(" ");
  }
  function verText(m) {
    return m.enforced ? wareki(m.enforced) + " 施行の内容" + (m.amend_num ? "（最終改正：" + m.amend_num + "）" : "") : "現行";
  }
  // カーソルを置く（スマホはタップ）と出る小窓
  function hint(icon, html, cls) {
    return '<span class="hint ' + (cls || "") + '" tabindex="0"><span class="ic">' + icon + '</span><span class="pop">' + html + "</span></span>";
  }
  function pendHTML(ps) {
    return "<b>⏳ 未施行の改正（この表には未反映）</b><ul>" + ps.map(function (p) {
      return "<li>" + esc(wareki(p.enforced)) + " 施行予定<br><small>" + esc((p.num || "") + " " + (p.title || "")) + "</small></li>";
    }).join("") + "</ul>";
  }
  function multiHead() {
    var lst = data.regs.map(function (m) {
      var ps = m.pending || [];
      return '<label class="ri"><input type="checkbox" data-s="' + m.key + '"' + (regOn[m.key] ? " checked" : "") + ">" +
        '<span class="rt">' + srcBadge(m.key) + ' <a href="' + esc(m.url) + '" target="_blank" rel="noopener">' + esc(m.title) + "</a>" +
        "<small>" + esc(m.num) + "</small>" +
        '<small class="rv">📅 ' + esc(verText(m)) + "</small>" +
        (ps.length ? '<small class="rp">⏳ 未施行の改正 ' + ps.length + "件（" + esc(wareki(ps[0].enforced)) + (ps.length > 1 ? "〜" : "") + "施行予定）※表には未反映</small>" : "") +
        "</span></label>";
    }).join("");
    var pend = [];
    data.regs.forEach(function (m) { (m.pending || []).forEach(function (p) { pend.push({ enforced: p.enforced, num: m.short, title: p.num }); }); });
    pend.sort(function (a, b) { return a.enforced < b.enforced ? -1 : 1; });
    return '<div class="ph reg"><span class="tag">' + data.labels.reg + "</span>" +
      '<details class="regsel"><summary><span id="sdRegShow"></span> ▾</summary>' +
      '<div class="rlist"><div class="rhint">表示する府令を選べます（選択はこの端末に保存）。各府令の施行日もここで確認できます。</div>' + lst + "</div></details>" +
      (pend.length ? hint("⏳", pendHTML(pend), "r") : "") + "</div>";
  }
  function regShowText() {
    var on = data.regs.filter(function (m) { return regOn[m.key]; });
    var el = document.getElementById("sdRegShow");
    if (el) el.textContent = on.length === data.regs.length ? data.regs.length + "本すべて" :
      on.length === 1 ? on[0].short : on.length + "/" + data.regs.length + "本";
  }
  function applyRegs() {
    if (!multi) return;
    panes.reg.pb.querySelectorAll(".art[data-s], .rel a[data-s]").forEach(function (el) { el.hidden = !regOn[el.getAttribute("data-s")]; });
    panes.reg.pb.querySelectorAll(".rel").forEach(function (r) { r.hidden = !r.querySelector("a:not([hidden])"); });
    panes.reg.items.forEach(function (it) {
      it.el.classList.toggle("empty", !it.el.querySelector(".art:not([hidden])") && !it.el.querySelector(".rel:not([hidden])"));
    });
    regShowText();
    try { localStorage.setItem("sandan-regs-" + data.id, JSON.stringify(regOn)); } catch (e) {}
  }
  function paneHead(c) {
    if (c === "reg" && multi) return multiHead();
    var m = data.laws[c], ps = m.pending || [], r = c === "reg" ? "r" : "";
    var info = "<b>" + esc(m.title) + "</b><br><small>" + esc(m.num) + "</small>" +
      '<div class="ln2">📅 ' + esc(m.enforced ? wareki(m.enforced) + " 施行の内容を表示しています" : "現行の内容（e-Gov " + (data.updated || "") + " 取得）") + "</div>" +
      (m.amend_num ? '<div class="ln2">最終改正：' + esc(m.amend_num) + (m.amend_title ? "<br><small>" + esc(m.amend_title) + "</small>" : "") + "</div>" : "") +
      '<div class="ln2"><a href="' + esc(m.url) + '" target="_blank" rel="noopener">e-Gov法令検索で原文を開く ↗</a></div>';
    return '<div class="ph ' + c + '"><span class="tag">' + data.labels[c] + "</span>" +
      '<span class="dt">' + esc(m.enforced ? wareki(m.enforced) + "施行" : "現行") + "</span>" +
      (ps.length ? hint("⏳", pendHTML(ps), r) : "") + hint("ⓘ", info, r) + "</div>";
  }
  function helpHTML() {
    var dr = data.labels.reg === "内閣府令" ? "内閣府令で定め" : "主務省令で定め";
    return "<b>三段表の使い方</b><ul>" +
      "<li>" + COLS.map(function (c) { return data.labels[c]; }).join("・") + "を左右に並べています。各列は個別にスクロールでき、「🔗 連動」がONなら他の列が対応する箇所へ付いてきます。</li>" +
      '<li><mark class="dg dg-o">政令で定め</mark>る → ' + data.labels.ord + 'の列、<mark class="dg dg-r">' + dr + "</mark>る → " + data.labels.reg + "の列に中身があります（クリックで移動）。</li>" +
      '<li><a class="ref rl">法第○条</a>・<a class="ref ro">令第○条</a> は該当する条へのリンクです。</li>' +
      "<li>各列の見出しの ⓘ に正式名称・最終改正、⏳ に未施行の改正があります。</li>" +
      (multi ? "<li>" + data.labels.reg + "の列は見出しの ▾ から表示する府令を選べます。</li>" : "") +
      "</ul><small>収録：" + COLS.map(function (c) { return data.labels[c] + " " + data.counts[c] + "条"; }).join("・") +
      "／データ更新日 " + esc(data.updated || "") + "（e-Gov法令API・毎週自動更新）</small>";
  }

  function render() {
    document.title = data.short + " 三段表 · マイポータル";
    var tools = '<div class="sd-tools">' +
      '<span class="sw search" data-tip="3つの法令をまとめて検索（例：本人確認書類）"><input type="search" id="sdQ" placeholder="🔍 検索" aria-label="3つの法令を横断検索"><span class="cnt" id="sdCnt"></span></span>' +
      '<span class="sw" data-tip="条を選んでその位置へ移動"><select id="sdJump" aria-label="条文へジャンプ"><option value="">📍 条へ移動</option></select></span>' +
      '<span class="sp"></span>' +
      '<label class="pill on" data-tip="どれかの列をスクロールすると、他の列が対応する箇所へ付いてくる"><input type="checkbox" id="sdSync" checked>🔗 連動</label>' +
      '<label class="pill" data-tip="政令・省令への委任や対応する条がある条だけを表示"><input type="checkbox" id="sdOnly">委任のある条だけ</label>' +
      '<span class="colsw" data-tip="クリックで列の表示／非表示">' + COLS.map(function (c) {
        return '<button type="button" data-col="' + c + '" aria-pressed="true">' + data.labels[c] + "</button>";
      }).join("") + "</span></div>";

    var body = { law: "", ord: "", reg: "" };
    data.rows.forEach(function (r) {
      if (r.type === "head") {
        COLS.forEach(function (c) { body[c] += '<div class="sd-chap">' + esc(r.path.join("　")) + "</div>"; });
        return;
      }
      body.law += artHTML(r.law, "law", r.k);
      ["ord", "reg"].forEach(function (c) {
        var arts = r[c], rel = relHTML(r["rel_" + c], c);
        body[c] += '<section class="grp' + (arts.length || rel ? "" : " empty") + '" id="g-' + PFX[c] + "-" + r.k + '" data-k="' + r.k + '">' +
          '<a class="gh" href="#h-' + r.k + '">法 ' + esc(r.law.t) + esc(r.law.c || "") + " 関係</a>" +
          arts.map(function (a) { return artHTML(a, c, r.k); }).join("") + rel + "</section>";
      });
    });
    app.innerHTML = tools + '<div class="sd-panes" id="sdPanes">' + COLS.map(function (c) {
      return '<div class="pane ' + c + '" data-col="' + c + '">' + paneHead(c) + '<div class="pb" tabindex="0">' + body[c] + "</div></div>";
    }).join("") + "</div>";

    qEl = document.getElementById("sdQ");
    onlyEl = document.getElementById("sdOnly");
    cntEl = document.getElementById("sdCnt");
    jumpEl = document.getElementById("sdJump");
    syncEl = document.getElementById("sdSync");
    panesEl = document.getElementById("sdPanes");

    COLS.forEach(function (c) {
      var pane = panesEl.querySelector('.pane[data-col="' + c + '"]'), pb = pane.querySelector(".pb");
      var items = c === "law"
        ? [].slice.call(pb.querySelectorAll(":scope > .art")).map(function (el) { return { k: el.getAttribute("data-k"), el: el }; })
        : [].slice.call(pb.querySelectorAll(":scope > .grp")).map(function (el) { return { k: el.getAttribute("data-k"), el: el }; });
      panes[c] = { pane: pane, pb: pb, items: items, map: {}, last: null, lock: 0, user: 0, raf: 0 };
      items.forEach(function (it) { panes[c].map[it.k] = it.el; });
      bindPane(c);
    });

    // 行ごとの検索インデックス
    data.rows.forEach(function (r) {
      if (r.type !== "row") return;
      var txt = [plain(r.law)].concat(r.ord.map(plain), r.reg.map(plain)).join(" ");
      rowsInfo.push({ k: r.k, idx: norm(txt), has: !!(r.ord.length || r.reg.length || r.deleg) });
    });

    // ジャンプ用リスト
    var opt = "";
    COLS.forEach(function (c) {
      opt += '<optgroup label="' + data.labels[c] + '">';
      data.rows.forEach(function (r) {
        if (r.type !== "row") return;
        (c === "law" ? [r.law] : r[c]).forEach(function (a) {
          var pre = c === "law" ? "法 " : c === "ord" ? "令 " : (a.s && regInfo[a.s] ? regInfo[a.s].short + " " : "規則 ");
          opt += '<option value="' + PFX[c] + "-" + a.k + '">' + esc(pre + a.t + (a.c || "")) + "</option>";
        });
      });
      opt += "</optgroup>";
    });
    jumpEl.insertAdjacentHTML("beforeend", opt);
    jumpEl.addEventListener("change", function () {
      if (this.value) { goTo(this.value, true); this.value = ""; }
    });

    var t;
    qEl.addEventListener("input", function () { clearTimeout(t); t = setTimeout(applyFilter, 220); });
    onlyEl.addEventListener("change", applyFilter);
    [syncEl, onlyEl].forEach(function (cb) {
      cb.addEventListener("change", function () { cb.parentNode.classList.toggle("on", cb.checked); });
    });
    syncEl.addEventListener("change", function () {
      syncOn = syncEl.checked;
      if (syncOn && activeKey) syncAll(activeKey, null);
    });
    app.querySelectorAll(".colsw button").forEach(function (b) {
      b.addEventListener("click", function () { toggleCol(b.getAttribute("data-col")); });
    });
    app.addEventListener("click", onClick);
    window.addEventListener("resize", layout);

    if (multi) {
      app.querySelectorAll(".regsel input[data-s]").forEach(function (cb) {
        cb.addEventListener("change", function () {
          var on = 0;
          app.querySelectorAll(".regsel input[data-s]").forEach(function (x) { if (x.checked) on++; });
          if (!on) { cb.checked = true; return; } // 最低1本は表示
          regOn[cb.getAttribute("data-s")] = cb.checked;
          applyRegs();
          if (activeKey) scrollPaneTo("reg", activeKey);
        });
      });
      applyRegs();
    }
    layout();
    applyFilter();
    activeKey = panes.law.items.length ? panes.law.items[0].k : null;
    markCur();
    if (location.hash.length > 1) setTimeout(function () { goTo(decodeURIComponent(location.hash.slice(1)), false); }, 80);
  }

  /* ---------- 列のスクロールと連動 ---------- */
  function visibleCols() {
    return COLS.filter(function (c) { return !panes[c].pane.hidden; });
  }
  // 列 c の上端付近にある「法の条」（施行令・規則の列ではまとまり）のキー
  function currentKey(c) {
    var p = panes[c], y = p.pb.scrollTop + 44, cur = null, first = null;
    for (var i = 0; i < p.items.length; i++) {
      var el = p.items[i].el;
      if (el.hidden) continue;
      if (first === null) first = p.items[i].k;
      if (el.offsetTop <= y) cur = p.items[i].k; else break;
    }
    return cur || first;
  }
  function scrollPaneTo(c, k, el) {
    var p = panes[c];
    el = el || p.map[k];
    if (!el || el.hidden || p.pane.hidden) return;
    p.last = k;
    // 画面外の条文は後からレイアウトされて高さが確定するので、数フレーム位置を補正する
    var fix = function (n) {
      var want = Math.max(0, el.offsetTop - 6);
      if (Math.abs(p.pb.scrollTop - want) > 2) { p.lock = Date.now() + 250; p.pb.scrollTop = want; }
      if (n > 0) requestAnimationFrame(function () { fix(n - 1); });
    };
    p.lock = Date.now() + 250;
    fix(4);
  }
  function syncAll(k, from) {
    visibleCols().forEach(function (c) {
      if (c !== from && currentKey(c) !== k) scrollPaneTo(c, k);
    });
  }
  function markCur() {
    COLS.forEach(function (c) {
      panes[c].items.forEach(function (it) { it.el.classList.toggle("cur", it.k === activeKey); });
    });
  }
  function bindPane(c) {
    var p = panes[c];
    var touch = function (ms) { return function () { p.user = Date.now() + ms; }; };
    p.pb.addEventListener("wheel", touch(700), { passive: true });
    p.pb.addEventListener("touchstart", touch(1500), { passive: true });
    p.pb.addEventListener("touchmove", touch(1500), { passive: true });
    p.pb.addEventListener("touchend", touch(1500), { passive: true });
    p.pb.addEventListener("pointerdown", touch(4000));
    p.pb.addEventListener("pointerup", touch(400));
    p.pb.addEventListener("pointermove", function (e) { if (e.buttons) p.user = Date.now() + 800; }, { passive: true });
    p.pb.addEventListener("keydown", touch(800));
    p.pb.addEventListener("scroll", function () {
      if (p.raf) return;
      p.raf = requestAnimationFrame(function () {
        p.raf = 0;
        var now = Date.now(), k = currentKey(c);
        // 他の列から動かされたスクロール、またはユーザー操作でないスクロールは連動の起点にしない
        if (now < p.lock || now > p.user) { p.last = k; return; }
        if (k === p.last) return;
        p.last = k;
        activeKey = k;
        markCur();
        if (syncOn) syncAll(k, c);
      });
    }, { passive: true });
  }

  /* ---------- 列の表示・レイアウト ---------- */
  function layout() {
    var was = narrow;
    narrow = window.matchMedia("(max-width:900px)").matches;
    if (was && !narrow) app.querySelectorAll(".colsw button").forEach(function (b) { b.setAttribute("aria-pressed", "true"); });
    var bar = document.querySelector(".bar");
    var barH = bar ? bar.offsetHeight : 0;
    // 3列を、ページを開いたときの画面の残りの高さにぴったり収める
    var top = panesEl.getBoundingClientRect().top + window.scrollY;
    var h = Math.max(420, window.innerHeight - Math.max(top, barH) - 14);
    if (window.scrollY > 0) h = Math.max(420, window.innerHeight - barH - 18);
    app.style.setProperty("--paneh", h + "px");
    applyCols();
    // 3列の見出しの高さをそろえる（本文の開始位置を合わせる）
    var heads = app.querySelectorAll(".ph"), mx = 0;
    heads.forEach(function (x) { x.style.minHeight = ""; });
    if (!narrow) {
      heads.forEach(function (x) { if (x.offsetParent) mx = Math.max(mx, x.offsetHeight); });
      heads.forEach(function (x) { x.style.minHeight = mx + "px"; });
    }
  }
  function isOn(c) {
    return app.querySelector('.colsw button[data-col="' + c + '"]').getAttribute("aria-pressed") === "true";
  }
  function applyCols() {
    var w = { law: "minmax(0,1fr)", ord: "minmax(0,1fr)", reg: "minmax(0,1.25fr)" }, tpl = [];
    COLS.forEach(function (c) {
      var show = narrow ? c === narrowCol : isOn(c);
      var wasHidden = panes[c].pane.hidden;
      panes[c].pane.hidden = !show;
      if (show) tpl.push(narrow ? "minmax(0,1fr)" : w[c]);
      if (narrow) app.querySelector('.colsw button[data-col="' + c + '"]').setAttribute("aria-pressed", show ? "true" : "false");
      if (show && wasHidden && activeKey) scrollPaneTo(c, activeKey);
    });
    panesEl.style.setProperty("--cols", tpl.join(" "));
  }
  function toggleCol(c) {
    if (narrow) { narrowCol = c; applyCols(); return; }
    var b = app.querySelector('.colsw button[data-col="' + c + '"]');
    var on = b.getAttribute("aria-pressed") !== "true";
    if (!on && visibleCols().length <= 1) return; // 最低1列は表示
    b.setAttribute("aria-pressed", on ? "true" : "false");
    applyCols();
  }
  function showCol(c) {
    if (narrow) { narrowCol = c; applyCols(); return; }
    var b = app.querySelector('.colsw button[data-col="' + c + '"]');
    if (b.getAttribute("aria-pressed") !== "true") { b.setAttribute("aria-pressed", "true"); applyCols(); }
  }

  /* ---------- 絞り込み・検索 ---------- */
  function clearMarks() {
    app.querySelectorAll("mark.hit").forEach(function (m) {
      var p = m.parentNode;
      p.replaceChild(document.createTextNode(m.textContent), m);
      p.normalize();
    });
  }
  function markIn(root, q) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), nodes = [], n;
    while ((n = w.nextNode())) if (n.nodeValue.indexOf(q) >= 0) nodes.push(n);
    nodes.forEach(function (node) {
      var parts = node.nodeValue.split(q), frag = document.createDocumentFragment();
      parts.forEach(function (p, i) {
        if (p) frag.appendChild(document.createTextNode(p));
        if (i < parts.length - 1) { var m = document.createElement("mark"); m.className = "hit"; m.textContent = q; frag.appendChild(m); }
      });
      node.parentNode.replaceChild(frag, node);
    });
  }
  function applyFilter() {
    var raw = qEl.value.trim(), q = norm(raw), only = onlyEl.checked, shown = 0;
    clearMarks();
    rowsInfo.forEach(function (r) {
      var ok = (!only || r.has) && (!q || r.idx.indexOf(q) >= 0);
      if (ok) shown++;
      COLS.forEach(function (c) {
        var el = panes[c].map[r.k];
        if (!el) return;
        el.hidden = !ok;
        if (ok && raw) markIn(el, raw);
      });
    });
    // 章見出し：配下がすべて非表示なら隠す
    COLS.forEach(function (c) {
      var kids = panes[c].pb.children;
      for (var i = 0; i < kids.length; i++) {
        if (!kids[i].classList.contains("sd-chap")) continue;
        var any = false;
        for (var j = i + 1; j < kids.length && !kids[j].classList.contains("sd-chap"); j++) if (!kids[j].hidden) { any = true; break; }
        kids[i].hidden = !any;
      }
    });
    cntEl.textContent = (q || only) ? shown + "/" + rowsInfo.length : "";
    if (q || only) {
      COLS.forEach(function (c) { panes[c].pb.scrollTop = 0; panes[c].last = null; });
      var first = rowsInfo.filter(function (r) { return !panes.law.map[r.k].hidden; })[0];
      if (first) { activeKey = first.k; markCur(); }
    } else if (activeKey) {
      syncAll(activeKey, null);
    }
  }

  /* ---------- ジャンプ・リンク ---------- */
  function flash(el) {
    el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
  }
  function goTo(id, push) {
    var el = document.getElementById(id);
    if (!el) return;
    var c = id.charAt(0) === "h" ? "law" : id.charAt(0) === "o" ? "ord" : id.charAt(0) === "r" ? "reg" : null;
    if (id.indexOf("g-o-") === 0) c = "ord";
    if (id.indexOf("g-r-") === 0) c = "reg";
    if (!c) return;
    var k = el.getAttribute("data-k");
    if (multi && el.getAttribute("data-s") && el.hidden) {
      regOn[el.getAttribute("data-s")] = true;
      var cb = app.querySelector('.regsel input[data-s="' + el.getAttribute("data-s") + '"]');
      if (cb) cb.checked = true;
      applyRegs();
    }
    if (el.hidden || (el.closest(".grp") && el.closest(".grp").hidden)) { qEl.value = ""; onlyEl.checked = false; onlyEl.parentNode.classList.remove("on"); applyFilter(); }
    showCol(c);
    scrollPaneTo(c, k, el);
    activeKey = k;
    markCur();
    if (syncOn) syncAll(k, c);
    flash(el.classList.contains("grp") ? el.querySelector(".gh") : el);
    if (push) history.replaceState(null, "", "#" + id);
  }
  function onClick(e) {
    var mk = e.target.closest("mark.dg");
    if (mk) {
      var holder = mk.closest("[data-k]");
      if (holder) goTo((mk.classList.contains("dg-o") ? "g-o-" : "g-r-") + holder.getAttribute("data-k"), true);
      return;
    }
    var a = e.target.closest('a[href^="#"]');
    if (!a) return;
    e.preventDefault();
    goTo(a.getAttribute("href").slice(1), true);
  }

  fetch(app.getAttribute("data-src") + "?ts=" + Date.now(), { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      data = d;
      multi = !!(d.regs && d.regs.length > 1);
      if (multi) {
        var saved = null;
        try { saved = JSON.parse(localStorage.getItem("sandan-regs-" + d.id) || "null"); } catch (e) {}
        d.regs.forEach(function (m, i) {
          regInfo[m.key] = { short: m.short, i: i };
          regOn[m.key] = saved && (m.key in saved) ? !!saved[m.key] : true;
        });
        if (!d.regs.some(function (m) { return regOn[m.key]; })) d.regs.forEach(function (m) { regOn[m.key] = true; });
      }
      d.rows.forEach(function (r) {
        if (r.type !== "row") return;
        has.law[r.k] = 1;
        r.ord.forEach(function (a) { has.ord[a.k] = 1; titles.ord[a.k] = a.t; });
        r.reg.forEach(function (a) { has.reg[a.k] = 1; titles.reg[a.k] = (a.s && regInfo[a.s] ? regInfo[a.s].short + " " : "") + a.t; });
      });
      render();
      var hp = document.getElementById("sdHelp");
      if (hp) hp.innerHTML = hint("？ 使い方", helpHTML(), "help");
    })
    .catch(function (e) {
      app.innerHTML = '<div class="sd-loading">データを読み込めませんでした。</div>';
      if (window.console) console.error(e);
    });
})();
