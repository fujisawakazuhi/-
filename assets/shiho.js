/* ============================================================
   shiho.js — 暗記シートの共通挙動
   - .k をクリック／タップで答えの表示・非表示を切り替える
   - 節ごとの一括表示ボタンを自動で差し込む
   - 目次を h2.chap / section.sec>h3 から自動生成する
   - 画面下部に「全部表示 / 全部かくす」コントロールを出す
   ============================================================ */
(function () {
  "use strict";

  var keys = Array.prototype.slice.call(document.querySelectorAll(".k"));
  if (!keys.length) return;

  var cntEl = null;

  function refresh() {
    if (!cntEl) return;
    var on = 0;
    for (var i = 0; i < keys.length; i++) if (keys[i].classList.contains("on")) on++;
    cntEl.textContent = on + " / " + keys.length;
  }

  /* ---- 個々の暗記ポイント ---- */
  keys.forEach(function (el) {
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.setAttribute("aria-label", "暗記ポイント（押すと答えを表示）");
    el.addEventListener("click", function () {
      el.classList.toggle("on");
      refresh();
    });
    el.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        el.classList.toggle("on");
        refresh();
      }
    });
  });

  function setAll(on) {
    keys.forEach(function (el) { el.classList.toggle("on", on); });
    refresh();
  }

  /* ---- 節ごとの一括ボタン ---- */
  Array.prototype.forEach.call(document.querySelectorAll("section.sec"), function (sec) {
    var h = sec.querySelector("h3");
    var mine = sec.querySelectorAll(".k");
    if (!h || !mine.length) return;
    var b = document.createElement("button");
    b.type = "button";
    b.className = "secbtn";
    b.textContent = "この節を表示";
    b.addEventListener("click", function () {
      var show = b.textContent === "この節を表示";
      Array.prototype.forEach.call(mine, function (el) { el.classList.toggle("on", show); });
      b.textContent = show ? "この節をかくす" : "この節を表示";
      refresh();
    });
    h.appendChild(b);
  });

  /* ---- 目次 ---- */
  var tocBox = document.getElementById("toc");
  if (tocBox) {
    var root = document.createElement("ol");
    var sub = null;
    var nodes = document.querySelectorAll("h2.chap, section.sec > h3");
    var n = 0;
    Array.prototype.forEach.call(nodes, function (node) {
      if (!node.id) node.id = "h" + (++n);
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + node.id;
      a.textContent = (node.firstChild && node.firstChild.nodeValue ? node.firstChild.nodeValue : node.textContent).trim();
      li.appendChild(a);
      if (node.tagName === "H2") {
        root.appendChild(li);
        sub = document.createElement("ol");
        li.appendChild(sub);
      } else if (sub) {
        sub.appendChild(li);
      } else {
        root.appendChild(li);
      }
    });
    tocBox.appendChild(root);
  }

  /* ---- 下部コントロール ---- */
  var fab = document.createElement("div");
  fab.className = "fab";

  var bShow = document.createElement("button");
  bShow.type = "button";
  bShow.textContent = "全部表示";
  bShow.addEventListener("click", function () { setAll(true); });

  var bHide = document.createElement("button");
  bHide.type = "button";
  bHide.textContent = "全部かくす";
  bHide.addEventListener("click", function () { setAll(false); });

  cntEl = document.createElement("span");
  cntEl.className = "cnt";

  fab.appendChild(bShow);
  fab.appendChild(bHide);
  fab.appendChild(cntEl);
  document.body.appendChild(fab);
  refresh();
})();
