/* 法令三段表ビューア: #sdApp[data-src] の JSON（scripts/build_sandan.py が生成）を描画 */
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

  var data, rows = [], has = { law: {}, ord: {}, reg: {} }, titles = { ord: {}, reg: {} };
  var qEl, onlyEl, cntEl, jumpEl, stickyEl, bodyEl;

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

  // 条文テキスト → HTML（委任文言の色分け、法・令の引用をリンク化）
  function deco(s, col) {
    return esc(s).replace(RE, function (m, pre, kind, ap, num, nos, dg, pre2, selfAp) {
      if (dg) {
        return '<mark class="dg ' + (dg.indexOf("政令") === 0 ? "dg-o" : "dg-r") + '">' + dg + "</mark>";
      }
      if (selfAp) { // 法の本文中の「別表」→ 別表の行
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
      if (has.law[k]) out.push('<a class="chip cl" href="#h-' + (k.indexOf("appdx") === 0 ? "appdx" : k) + '">法' + kLabel(k) + "</a>");
    });
    (a.o || []).forEach(function (k) {
      if (has.ord[k]) out.push('<a class="chip co" href="#o-' + k + '">令' + kLabel(k) + "</a>");
    });
    if (a.n) out.push('<span class="chip cn" title="条文中に法・令の条の引用がないため、直前の条と同じ行に置いています">引用なし</span>');
    return out.length ? '<span class="chips">' + out.join(" ") + "</span>" : "";
  }
  function artHTML(a, col) {
    var id = PFX[col] + "-" + a.k;
    var h = '<article class="art" id="' + id + '"><header class="ah"><a class="at" href="#' + id + '">' + esc(a.t) + "</a>" +
      (a.c ? '<span class="ac">' + esc(a.c) + "</span>" : "") + (col === "law" ? "" : chips(a)) + "</header>";
    h += '<div class="ab">' + linesHTML(a.L, col);
    (a.sub || []).forEach(function (s) {
      h += '<div class="sub-appdx"><div class="st">' + esc(s.t) + (s.c ? " " + esc(s.c) : "") + "</div>" + linesHTML(s.L, col) + "</div>";
    });
    return h + "</div></article>";
  }
  function relHTML(keys, col) {
    if (!keys || !keys.length) return "";
    return '<div class="rel">このほか関連する条（他の行に掲載）：' + keys.map(function (k) {
      return '<a href="#' + PFX[col] + "-" + k + '">' + esc(titles[col][k] || kLabel(k)) + "</a>";
    }).join("、") + "</div>";
  }
  function plain(a) {
    var out = [a.t, a.c || ""];
    (a.L || []).concat([].concat.apply([], (a.sub || []).map(function (s) { return [[0, 0, s.t]].concat(s.L); })))
      .forEach(function (ln) { out.push(ln[0] === "tbl" ? ln[2].map(function (r) { return r.join(" "); }).join(" ") : ln[2]); });
    return out.join(" ");
  }

  function render() {
    var L = data.laws;
    document.title = data.short + " 三段表 · マイポータル";
    // 列見出し・操作バー
    var head = '<div class="sd-tools">' +
      '<select id="sdJump" aria-label="条文へジャンプ"><option value="">📍 条文へジャンプ…</option></select>' +
      '<input type="search" id="sdQ" placeholder="🔍 3つの法令を横断検索（例：本人確認書類）">' +
      '<span class="cnt" id="sdCnt"></span>' +
      '<label class="chk"><input type="checkbox" id="sdOnly">政令・省令の対応がある条だけ</label>' +
      '<span class="colsw">表示：' + COLS.map(function (c) {
        return '<button type="button" data-col="' + c + '" aria-pressed="true">' + data.labels[c] + "</button>";
      }).join("") + "</span></div>" +
      '<div class="sd-colhead grid3">' + COLS.map(function (c) {
        return '<div class="' + c + '">' + data.labels[c] + "<small>" + esc(L[c].num) + "</small></div>";
      }).join("") + "</div>";

    var body = "";
    data.rows.forEach(function (r) {
      if (r.type === "head") { body += '<div class="sd-chap">' + esc(r.path.join("　")) + "</div>"; return; }
      body += '<section class="sd-row grid3" data-k="' + r.k + '">' +
        '<div class="cell law"><div class="cin">' + artHTML(r.law, "law") + "</div></div>" +
        '<div class="cell ord"><div class="cin">' + (r.ord.length ? r.ord.map(function (a) { return artHTML(a, "ord"); }).join("") : '<span class="empty">—</span>') + relHTML(r.rel_ord, "ord") + "</div></div>" +
        '<div class="cell reg">' + (r.reg.length ? r.reg.map(function (a) { return artHTML(a, "reg"); }).join("") : '<span class="empty">—</span>') + relHTML(r.rel_reg, "reg") + "</div>" +
        "</section>";
    });
    app.innerHTML = '<div class="sd-sticky" id="sdSticky">' + head + '</div><div class="sd-body" id="sdBody">' + body + "</div>";

    stickyEl = document.getElementById("sdSticky");
    bodyEl = document.getElementById("sdBody");
    qEl = document.getElementById("sdQ");
    onlyEl = document.getElementById("sdOnly");
    cntEl = document.getElementById("sdCnt");
    jumpEl = document.getElementById("sdJump");

    // 行の検索インデックス
    var els = bodyEl.children, ri = 0;
    data.rows.forEach(function (r) {
      var el = els[ri++];
      if (r.type === "head") { rows.push({ head: true, el: el }); return; }
      var txt = [plain(r.law)].concat(r.ord.map(plain), r.reg.map(plain)).join(" ");
      rows.push({ el: el, idx: norm(txt), has: !!(r.ord.length || r.reg.length || r.deleg) });
    });

    // ジャンプ用リスト
    var opt = "";
    COLS.forEach(function (c) {
      opt += '<optgroup label="' + data.labels[c] + '">';
      data.rows.forEach(function (r) {
        if (r.type !== "row") return;
        (c === "law" ? [r.law] : r[c]).forEach(function (a) {
          opt += '<option value="' + PFX[c] + "-" + a.k + '">' + esc((c === "law" ? "法 " : c === "ord" ? "令 " : "規則 ") + a.t + (a.c || "")) + "</option>";
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
    stickyEl.querySelectorAll(".colsw button").forEach(function (b) {
      b.addEventListener("click", function () {
        var on = b.getAttribute("aria-pressed") !== "true";
        var vis = stickyEl.querySelectorAll('.colsw button[aria-pressed="true"]').length;
        if (!on && vis <= 1) return; // 最低1列は表示
        b.setAttribute("aria-pressed", on ? "true" : "false");
        layoutCols();
      });
    });
    app.addEventListener("click", function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      e.preventDefault();
      goTo(a.getAttribute("href").slice(1), true);
    });
    window.addEventListener("resize", measure);
    measure();
    applyFilter();
    if (location.hash.length > 1) setTimeout(function () { goTo(decodeURIComponent(location.hash.slice(1)), false); }, 60);
  }

  function layoutCols() {
    var w = { law: "minmax(0,1fr)", ord: "minmax(0,1fr)", reg: "minmax(0,1.25fr)" }, tpl = [];
    COLS.forEach(function (c) {
      var on = stickyEl.querySelector('.colsw button[data-col="' + c + '"]').getAttribute("aria-pressed") === "true";
      app.classList.toggle("hide-" + c, !on);
      if (on) tpl.push(w[c]);
    });
    app.style.setProperty("--cols", tpl.join(" "));
    measure();
  }

  // 固定ヘッダーの高さを測り、条文の固定表示（短い条だけ）を切り替える
  function measure() {
    var bar = document.querySelector(".bar");
    var barH = bar ? bar.offsetHeight : 0;
    var narrow = window.matchMedia("(max-width:900px)").matches;
    document.documentElement.style.setProperty("--barh", barH + "px");
    var st = barH + (narrow ? 0 : stickyEl.offsetHeight) + 8;
    document.documentElement.style.setProperty("--st", st + "px");
    var avail = window.innerHeight - st - 16;
    var cins = bodyEl.querySelectorAll(".sd-row:not([hidden]) .cell.law .cin, .sd-row:not([hidden]) .cell.ord .cin");
    cins.forEach(function (c) { c.classList.remove("stick", "stickscroll"); });
    if (narrow) return;
    // 先に全部の高さを読んでからクラスを付ける（レイアウトの再計算を1回で済ませる）
    var m = [];
    cins.forEach(function (c) { m.push([c, c.offsetHeight, c.closest(".sd-row").offsetHeight]); });
    m.forEach(function (x) {
      var c = x[0], h = x[1], rowH = x[2];
      if (rowH <= h + 40) return;            // この列がいちばん長い → そのまま
      c.classList.add(h < avail ? "stick" : "stickscroll");
    });
  }

  function clearMarks() {
    bodyEl.querySelectorAll("mark.hit").forEach(function (m) {
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
    var raw = qEl.value.trim(), q = norm(raw), only = onlyEl.checked, shown = 0, total = 0;
    clearMarks();
    rows.forEach(function (r) {
      if (r.head) return;
      total++;
      var ok = (!only || r.has) && (!q || r.idx.indexOf(q) >= 0);
      r.el.hidden = !ok;
      if (ok) { shown++; if (raw) markIn(r.el, raw); }
    });
    // 章見出し：配下の行がすべて非表示なら隠す
    for (var i = 0; i < rows.length; i++) {
      if (!rows[i].head) continue;
      var any = false;
      for (var j = i + 1; j < rows.length && !rows[j].head; j++) if (!rows[j].el.hidden) { any = true; break; }
      rows[i].el.hidden = !any;
    }
    cntEl.textContent = (q || only) ? shown + " / " + total + " 条" : "法律 " + data.counts.law + "条・施行令 " + data.counts.ord + "条・施行規則 " + data.counts.reg + "条";
    measure();
  }

  function goTo(id, push) {
    var el = document.getElementById(id);
    if (!el) return;
    var row = el.closest(".sd-row");
    if (row && row.hidden) { qEl.value = ""; onlyEl.checked = false; applyFilter(); }
    var col = id.charAt(0) === "h" ? "law" : id.charAt(0) === "o" ? "ord" : "reg";
    var btn = stickyEl.querySelector('.colsw button[data-col="' + col + '"]');
    if (btn && btn.getAttribute("aria-pressed") !== "true") { btn.setAttribute("aria-pressed", "true"); layoutCols(); }
    el.scrollIntoView({ block: "start" });
    el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
    if (push) history.replaceState(null, "", "#" + id);
  }

  fetch(app.getAttribute("data-src") + "?ts=" + Date.now(), { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      data = d;
      d.rows.forEach(function (r) {
        if (r.type !== "row") return;
        has.law[r.k] = 1;
        r.ord.forEach(function (a) { has.ord[a.k] = 1; titles.ord[a.k] = a.t; });
        r.reg.forEach(function (a) { has.reg[a.k] = 1; titles.reg[a.k] = a.t; });
      });
      var meta = document.getElementById("sdMeta");
      if (meta) {
        meta.innerHTML = COLS.map(function (c) {
          var m = d.laws[c];
          var am = m.amend_num ? "　最終改正：" + esc(m.amend_num) + (m.enforced ? "（" + esc(m.enforced) + " 施行）" : "") : "";
          return '<div class="lw"><span class="tag ' + c + '">' + d.labels[c] + '</span><a href="' + esc(m.url) + '" target="_blank" rel="noopener">' +
            esc(m.title) + "</a><span>（" + esc(m.num) + "）" + am + "</span></div>";
        }).join("") +
          '<div class="legend">色分け：<mark class="dg dg-o">政令で定め</mark>る → 施行令の列　' +
          '<mark class="dg dg-r">主務省令で定め</mark>る → 施行規則の列　／　' +
          '<a class="ref rl">法第○条</a>・<a class="ref ro">令第○条</a> は該当条へのリンク　／　データ更新日 ' + esc(d.updated || "") + "（e-Gov法令API）</div>";
      }
      render();
    })
    .catch(function (e) {
      app.innerHTML = '<div class="sd-loading">データを読み込めませんでした。</div>';
      if (window.console) console.error(e);
    });
})();
