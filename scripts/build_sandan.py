#!/usr/bin/env python3
"""法令三段表データ生成（e-Gov 法令API）

法律・施行令・施行規則の本則を取得し、施行令・施行規則の各条を
条文中の「法第○条」「令第○条」の引用から法律の条に対応付けて
sandan/<id>/data.json に出力する。

対応付けのルール
  - 施行令の条: 最初に引用している「法第○条」の行に置く
  - 施行規則の条: 最初に引用している「法第○条」または「令第○条」の行に置く
    （令の条を引用している場合は、その令の条が置かれた行）
  - 引用のない条: 同じ列の直前の条と同じ行に置く（"n" フラグ）
  - 「法別表」「令別表」の引用は別表の行に置く
内容に変化がなければファイルは書き換えない。
"""
import json, re, sys, os, datetime, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

SETS = [
    {
        "id": "hanshu",
        "short": "犯収法",
        "name": "犯罪による収益の移転防止に関する法律",
        "titles": {
            "law": "犯罪による収益の移転防止に関する法律",
            "ord": "犯罪による収益の移転防止に関する法律施行令",
        },
        "ids": {"law": "419AC0000000022", "ord": "420CO0000000020"},
        "regs": [{"key": "", "short": "施行規則", "title": "犯罪による収益の移転防止に関する法律施行規則"}],
    },
    {
        "id": "shikin",
        "short": "資金決済法",
        "name": "資金決済に関する法律",
        "titles": {
            "law": "資金決済に関する法律",
            "ord": "資金決済に関する法律施行令",
        },
        "ids": {"law": "421AC0000000059"},
        "labels": {"reg": "内閣府令"},
        # 第三段は業態ごとの内閣府令（法の章立ての順）。見つからない府令は飛ばす
        "regs": [
            {"key": "pre", "short": "前払式府令", "title": "前払式支払手段に関する内閣府令"},
            {"key": "idou", "short": "資金移動業府令", "title": "資金移動業者に関する内閣府令"},
            {"key": "denshi", "short": "電子決済手段府令", "title": "電子決済手段等取引業者に関する内閣府令"},
            {"key": "ango", "short": "暗号資産府令", "title": "暗号資産交換業者に関する内閣府令"},
            {"key": "chukai", "short": "仲介業府令", "title": "電子決済手段・暗号資産サービス仲介業者に関する内閣府令"},
            {"key": "bunseki", "short": "為替取引分析業府令", "title": "為替取引分析業者に関する内閣府令"},
            {"key": "seisan", "short": "資金清算機関府令", "title": "資金清算機関に関する内閣府令"},
        ],
    },
]

ROLES = ("law", "ord", "reg")
LABEL = {"law": "法律", "ord": "施行令", "reg": "施行規則"}
API2 = "https://laws.e-gov.go.jp/api/2"
API1 = "https://elaws.e-gov.go.jp/api/1"
UA = {"User-Agent": "Mozilla/5.0 (sandan-builder; personal portal)"}
JST = datetime.timezone(datetime.timedelta(hours=9))


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------- 取得 ----------------

def search_id(title):
    """v2 の法令一覧APIで題名完全一致の law_id を探す"""
    url = API2 + "/laws?" + urllib.parse.urlencode(
        {"law_title": title, "response_format": "json", "limit": 50})
    d = json.loads(get(url))
    for x in d.get("laws", []):
        li = x.get("law_info") or {}
        ri = x.get("current_revision_info") or x.get("revision_info") or {}
        if (ri.get("law_title") or "").strip() == title:
            return li.get("law_id")
    print("  search: no exact match for", title,
          [((x.get("revision_info") or {}).get("law_title")) for x in d.get("laws", [])][:10])
    return None


def jt2et(n):
    """v2 の JSON 形式の法令本文（tag/attr/children）を ElementTree に変換"""
    el = ET.Element(n["tag"], {k: str(v) for k, v in (n.get("attr") or {}).items()})
    last = None
    for c in n.get("children") or []:
        if isinstance(c, str):
            if last is None:
                el.text = (el.text or "") + c
            else:
                last.tail = (last.tail or "") + c
        else:
            last = jt2et(c)
            el.append(last)
    return el


def find_law_el(root):
    if root.tag == "Law":
        return root
    el = root.find(".//Law")
    if el is None:
        raise ValueError("no <Law> element")
    return el


REV_KEYS = ("law_revision_id", "amendment_enforcement_date", "amendment_law_title",
            "amendment_law_num", "amendment_promulgate_date", "current_revision_status",
            "amendment_scheduled_enforcement_date", "amendment_enforcement_comment", "updated")


def flat_rev(x):
    """改正履歴の1件を平らな dict にする（revision_info 入れ子にも対応）"""
    r = dict(x.get("revision_info") or {})
    for k, v in x.items():
        if not isinstance(v, (dict, list)):
            r.setdefault(k, v)
    return r


def revisions(law_id, today):
    """(現在施行中の版, [未施行の版...]) を返す"""
    d = json.loads(get(f"{API2}/law_revisions/{urllib.parse.quote(law_id)}?response_format=json"))
    items = d.get("revisions") or d.get("law_revisions") or []
    revs = [flat_rev(x) for x in items]
    print("  law_revisions:", len(revs), "revisions; top keys", sorted(d.keys()))
    if revs:
        print("   sample:", {k: revs[0].get(k) for k in REV_KEYS})
    cur, pending = None, []
    for r in revs:
        st = (r.get("current_revision_status") or "")
        ed = (r.get("amendment_enforcement_date") or "")[:10]
        if st == "CurrentEnforced":
            cur = r
        elif st == "UnEnforced" or (ed and ed > today and st not in ("PreviousEnforced", "Repeal")):
            pending.append(r)
    if cur is None:  # ステータスが無い場合は施行日が今日以前で最新のもの
        past = [r for r in revs if (r.get("amendment_enforcement_date") or "")[:10] <= today]
        past.sort(key=lambda r: r.get("amendment_enforcement_date") or "")
        cur = past[-1] if past else None
    pending.sort(key=lambda r: r.get("amendment_enforcement_date") or "")
    return cur, pending


def fetch_law(law_id):
    """(Law要素, メタ情報dict) を返す。
    改正履歴から「現在施行中の版」を特定し、その版の本文を取得する。"""
    errs = []
    today = datetime.datetime.now(JST).strftime("%Y-%m-%d")
    cur, pending = None, []
    try:
        cur, pending = revisions(law_id, today)
        print("  current:", {k: (cur or {}).get(k) for k in REV_KEYS})
        print("  pending:", [(r.get("amendment_enforcement_date"), r.get("amendment_law_title")) for r in pending])
    except Exception as e:
        print("  law_revisions failed:", repr(e))
    meta = {"revision_info": cur or {}, "pending": pending}
    target = (cur or {}).get("law_revision_id") or law_id
    try:
        raw = get(f"{API2}/law_file/xml/{urllib.parse.quote(target)}")
        print("  v2 law_file ok:", target)
        return find_law_el(ET.fromstring(raw)), meta
    except Exception as e:
        errs.append(f"v2 law_file {target}: {e!r}")
    try:
        url = f"{API2}/law_data/{urllib.parse.quote(law_id)}?" + urllib.parse.urlencode(
            {"response_format": "json", "law_full_text_format": "xml", "asof": today})
        d = json.loads(get(url))
        lft = d.get("law_full_text")
        root = ET.fromstring(lft) if isinstance(lft, str) else jt2et(lft)
        print("  v2 law_data ok")
        return find_law_el(root), {"revision_info": d.get("revision_info") or cur or {}, "pending": pending}
    except Exception as e:
        errs.append(f"v2 law_data: {e!r}")
    try:
        raw = get(f"{API1}/lawdata/{urllib.parse.quote(law_id)}")
        print("  v1 lawdata ok")
        return find_law_el(ET.fromstring(raw)), {}
    except Exception as e:
        errs.append(f"v1 lawdata: {e!r}")
    raise RuntimeError("; ".join(errs))


# ---------------- 本文の整形 ----------------

def text_of(el):
    """ルビ（Rt）を除いた要素内テキスト"""
    if el is None:
        return ""
    parts = []

    def rec(e):
        if e.tag == "Rt":
            return
        if e.text:
            parts.append(e.text)
        for c in e:
            rec(c)
            if c.tail:
                parts.append(c.tail)
    rec(el)
    return "".join(parts).strip()


def sent_text(container):
    """ParagraphSentence / ItemSentence 等の本文（Column は全角空白で連結）"""
    if container is None:
        return ""
    cols = container.findall("Column")
    if cols:
        return "　".join(sent_text(c) for c in cols)
    ss = container.findall("Sentence")
    if ss:
        return "".join(text_of(s) for s in ss)
    return text_of(container)


def block_text(e):
    """表のセル等、構造をもつ要素を改行区切りのテキストにする"""
    parts, title = [], ""
    for c in e:
        t = c.tag
        if t == "Rt":
            continue
        if t.endswith("Title") or t == "ParagraphNum":
            title = text_of(c)
        elif t.endswith("Sentence") and t != "Sentence":
            s = sent_text(c)
            parts.append((title + "　" if title else "") + s)
            title = ""
        elif t == "Sentence":
            parts.append(text_of(c))
        elif t == "Column":
            parts.append(sent_text(c))
        else:
            sub = block_text(c)
            if sub:
                parts.append(sub)
    if not parts and e.text and e.text.strip():
        parts.append(text_of(e))
    return "\n".join(p for p in parts if p)


def table_line(ts):
    rows, head = [], 0
    for tr in ts.iter():
        if tr.tag == "TableHeaderRow":
            rows.append([text_of(c) for c in tr.findall("TableHeaderColumn")])
            head += 1
        elif tr.tag == "TableRow":
            rows.append([block_text(c) for c in tr.findall("TableColumn")])
    return ["tbl", head, rows]


def item_lines(el, depth, lines):
    tag = el.tag
    t = el.find(tag + "Title")
    s = el.find(tag + "Sentence")
    lines.append([f"i{min(depth, 6)}", text_of(t), sent_text(s)])
    for c in el:
        if re.fullmatch(r"Subitem\d+", c.tag):
            item_lines(c, depth + 1, lines)
        elif c.tag == "TableStruct":
            lines.append(table_line(c))
        elif c.tag == "List":
            list_lines(c, depth + 1, lines)


def list_lines(el, depth, lines):
    for c in el:
        if c.tag == "ListSentence":
            lines.append([f"i{min(depth, 6)}", "", sent_text(c)])
        elif re.fullmatch(r"Sublist\d+", c.tag):
            list_lines(c, depth + 1, lines)


def para_lines(p, lines):
    cap = p.find("ParagraphCaption")
    if cap is not None:
        lines.append(["cap", "", text_of(cap)])
    lines.append(["p", text_of(p.find("ParagraphNum")), sent_text(p.find("ParagraphSentence"))])
    for c in p:
        if c.tag == "Item":
            item_lines(c, 1, lines)
        elif c.tag == "TableStruct":
            lines.append(table_line(c))
        elif c.tag == "List":
            list_lines(c, 1, lines)
        elif c.tag in ("StyleStruct", "FigStruct", "FormatStruct"):
            lines.append(["note", "", "（様式・図は省略。e-Govで確認）"])


HEAD_TAGS = {"Part": "PartTitle", "Chapter": "ChapterTitle", "Section": "SectionTitle",
             "Subsection": "SubsectionTitle", "Division": "DivisionTitle"}


def parse_law(law_el):
    body = law_el.find("LawBody")
    main = body.find("MainProvision")
    arts = []

    def walk(el, path):
        for c in el:
            if c.tag in HEAD_TAGS:
                walk(c, path + [text_of(c.find(HEAD_TAGS[c.tag]))])
            elif c.tag == "Article":
                lines = []
                for p in c.findall("Paragraph"):
                    para_lines(p, lines)
                arts.append({
                    "k": c.get("Num"),
                    "t": text_of(c.find("ArticleTitle")),
                    "c": text_of(c.find("ArticleCaption")),
                    "L": lines,
                    "path": path,
                })
    walk(main, [])

    appdx = []
    for i, a in enumerate(body.findall("AppdxTable")):
        lines = []
        rel = text_of(a.find("RelatedArticleNum"))
        for c in a:
            if c.tag == "TableStruct":
                lines.append(table_line(c))
            elif c.tag == "Item":
                item_lines(c, 1, lines)
            elif c.tag in ("Remarks",):
                for s in c:
                    if s.tag == "RemarksLabel":
                        lines.append(["cap", "", text_of(s)])
                    elif s.tag == "Sentence":
                        lines.append(["p", "", text_of(s)])
                    elif s.tag == "Item":
                        item_lines(s, 1, lines)
        appdx.append({"k": f"appdx{i + 1}", "t": text_of(a.find("AppdxTableTitle")) or "別表",
                      "c": rel, "L": lines, "path": []})
    title = text_of(body.find("LawTitle"))
    num = text_of(law_el.find("LawNum"))
    return title, num, arts, appdx


# ---------------- 対応付け ----------------

KNUM = "〇一二三四五六七八九十百千"
NOT_KANJI = r"(?<![㐀-鿿々〆])"
RE_REF = re.compile(NOT_KANJI + r"(法|令)(?:(別表)|第([%s]+)条((?:の[%s]+)*))" % (KNUM, KNUM))
DELEG = re.compile(r"(政令|主務省令|内閣府令|命令)で定め")


def k2i(s):
    dg = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    un = {"十": 10, "百": 100, "千": 1000}
    total = cur = 0
    for ch in s:
        if ch in dg:
            cur = dg[ch]
        elif ch in un:
            total += (cur or 1) * un[ch]
            cur = 0
    return total + cur


def ref_key(m):
    if m.group(2):
        return "appdx"
    key = str(k2i(m.group(3)))
    if m.group(4):
        key += "".join("_" + str(k2i(x)) for x in m.group(4).split("の") if x)
    return key


def art_text(a):
    out = [a.get("c", "")]
    for ln in a["L"]:
        if ln[0] == "tbl":
            out += ["　".join(r) for r in ln[2]]
        else:
            out.append(ln[2])
    return "\n".join(out)


def refs_in(a):
    """[(種類'法'/'令', key), ...] 出現順・重複なし。
    括弧書き（定義・例外の言及が多い）の外にある引用を先に並べる。
    配置先はこの先頭の引用で決まる。"""
    txt = art_text(a)
    depth, d = [], 0
    for ch in txt:
        if ch == "（":
            d += 1
        depth.append(d)
        if ch == "）":
            d = max(0, d - 1)
    top, inner = [], []
    for m in RE_REF.finditer(txt):
        r = (m.group(1), ref_key(m))
        (top if depth[m.start()] == 0 else inner).append(r)
    out = []
    for r in top + inner:
        if r not in out:
            out.append(r)
    return out


def build_rows(L, O, R):
    law_keys = [a["k"] for a in L["arts"]]
    law_set = set(law_keys) | {"appdx"}
    ord_keys = {a["k"] for a in O["arts"]}

    # 令の各条 → 行
    ord_row, ord_by_row = {}, {}
    prev = law_keys[0] if law_keys else "appdx"
    for a in O["arts"] + O["appdx"]:
        rs = [k for kind, k in refs_in(a) if kind == "法" and k in law_set]
        a["r"] = rs
        if rs:
            row = rs[0]
        else:
            row = "appdx" if a["k"].startswith("appdx") else prev
            a["n"] = 1
        prev = row
        ord_row[a["k"]] = row
        ord_by_row.setdefault(row, []).append(a)

    # 規則の各条 → 行
    reg_by_row, prev_by_s = {}, {}
    for a in R["arts"] + R["appdx"]:
        prev = prev_by_s.get(a.get("s", ""), law_keys[0] if law_keys else "appdx")
        rs = refs_in(a)
        a["r"] = [k for kind, k in rs if kind == "法" and k in law_set]
        a["o"] = [k for kind, k in rs if kind == "令" and (k in ord_keys or k == "appdx")]
        row = None
        for kind, k in rs:
            if kind == "法" and k in law_set:
                row = k
                break
            if kind == "令" and k in ord_row:
                row = ord_row[k]
                break
            if kind == "令" and k == "appdx":
                row = "appdx"
                break
        if row is None:
            row = "appdx" if "appdx" in a["k"] else prev
            a["n"] = 1
        a["row"] = row
        prev_by_s[a.get("s", "")] = row
        reg_by_row.setdefault(row, []).append(a)

    # 他の行に置いた条のうち、この行の法の条を引用しているもの（関連）
    rel_ord, rel_reg = {}, {}
    for a in O["arts"] + O["appdx"]:
        for k in a["r"][1:]:
            if k != ord_row[a["k"]]:
                rel_ord.setdefault(k, []).append(a["k"])
    for a in R["arts"] + R["appdx"]:
        targets = list(a["r"]) + [ord_row[k] for k in a["o"] if k in ord_row]
        for k in dict.fromkeys(targets):
            if k != a["row"]:
                rel_reg.setdefault(k, []).append(a["k"])
    for a in R["arts"] + R["appdx"]:
        a.pop("row", None)

    rows, last_path = [], None
    law_rows = L["arts"] + ([{"k": "appdx", "t": "別表", "c": "",
                              "L": [], "sub": L["appdx"], "path": ["別表"]}] if (L["appdx"] or "appdx" in ord_by_row or "appdx" in reg_by_row) else [])
    for la in law_rows:
        path = la.get("path") or []
        if path != last_path and path:
            rows.append({"type": "head", "path": path})
            last_path = path
        k = la["k"]
        deleg = bool(DELEG.search(art_text(la)))
        rows.append({
            "type": "row", "k": k, "law": la, "deleg": deleg,
            "ord": ord_by_row.get(k, []), "reg": reg_by_row.get(k, []),
            "rel_ord": rel_ord.get(k, []), "rel_reg": rel_reg.get(k, []),
        })
    for a in L["arts"]:
        a.pop("path", None)
    for a in O["arts"] + O["appdx"] + R["arts"] + R["appdx"] + L["appdx"]:
        a.pop("path", None)
    return rows


def meta_summary(meta, law_id, title, num):
    ri = meta.get("revision_info") or {}
    out = {"title": title, "num": num, "id": law_id,
           "url": f"https://laws.e-gov.go.jp/law/{law_id}"}
    for src, dst in (("amendment_law_num", "amend_num"), ("amendment_law_title", "amend_title"),
                     ("amendment_enforcement_date", "enforced"),
                     ("amendment_promulgate_date", "promulgated"),
                     ("law_revision_id", "rev")):
        if ri.get(src):
            out[dst] = str(ri[src])[:10] if src.endswith("_date") else ri[src]
    out["pending"] = [{"enforced": (r.get("amendment_enforcement_date") or "")[:10],
                       "title": r.get("amendment_law_title") or "",
                       "num": r.get("amendment_law_num") or ""}
                      for r in meta.get("pending") or []]
    return out


def load_part(title, law_id):
    if not law_id:
        law_id = search_id(title)
    if not law_id:
        raise RuntimeError(f"law id not found: {title}")
    print(f" {title} -> {law_id}")
    law_el, meta = fetch_law(law_id)
    t, num, arts, appdx = parse_law(law_el)
    print(f"  parsed: {t} / {num} / articles {len(arts)} / appdx {len(appdx)}")
    if t != title:
        print("  WARNING: title mismatch:", t)
    return {"arts": arts, "appdx": appdx, "meta": meta_summary(meta, law_id, t, num)}


def build_set(cfg):
    print("==", cfg["id"])
    parts = {}
    for role in ("law", "ord"):
        parts[role] = load_part(cfg["titles"][role], cfg.get("ids", {}).get(role))

    # 第三段（施行規則・府令）。複数ある場合は条のキーに府令の記号を付ける
    regs_cfg = cfg["regs"]
    multi = len(regs_cfg) > 1
    R = {"arts": [], "appdx": []}
    reg_metas = []
    for rc in regs_cfg:
        try:
            part = load_part(rc["title"], rc.get("id"))
        except Exception as e:
            if not multi:
                raise
            print("  SKIP reg:", rc["title"], repr(e))
            continue
        if multi:
            for a in part["arts"] + part["appdx"]:
                a["k"] = rc["key"] + "-" + a["k"]
                a["s"] = rc["key"]
        R["arts"] += part["arts"]
        R["appdx"] += part["appdx"]
        m = part["meta"]
        m.update({"key": rc["key"], "short": rc["short"], "count": len(part["arts"])})
        reg_metas.append(m)
    if not reg_metas:
        raise RuntimeError("no regulation loaded")
    parts["reg"] = R

    rows = build_rows(parts["law"], parts["ord"], parts["reg"])

    # 統計・診断
    for role in ("ord", "reg"):
        arts = parts[role]["arts"]
        nref = [a["k"] for a in arts if a.get("n")]
        print(f"  {role}: {len(arts)} arts, no-ref {len(nref)}: {nref[:30]}")
    placed = sum(len(r["ord"]) for r in rows if r["type"] == "row")
    print("  ord placed:", placed, "/", len(parts["ord"]["arts"]) + len(parts["ord"]["appdx"]))
    placed = sum(len(r["reg"]) for r in rows if r["type"] == "row")
    print("  reg placed:", placed, "/", len(R["arts"]) + len(R["appdx"]))
    for r in rows:
        if r["type"] == "row" and (r["ord"] or r["reg"]):
            print("   ", r["law"]["t"], "令", [a["k"] for a in r["ord"]][:12], "規", [a["k"] for a in r["reg"]][:14])

    labels = dict(LABEL)
    labels.update(cfg.get("labels") or {})
    out = {
        "id": cfg["id"], "short": cfg["short"], "name": cfg["name"],
        "laws": {"law": parts["law"]["meta"], "ord": parts["ord"]["meta"]},
        "labels": labels,
        "counts": {"law": len(parts["law"]["arts"]), "ord": len(parts["ord"]["arts"]), "reg": len(R["arts"])},
        "rows": rows,
    }
    if multi:
        out["regs"] = reg_metas
        out["laws"]["reg"] = {"title": labels["reg"] + "（" + str(len(reg_metas)) + "本）",
                              "num": "、".join(m["short"] for m in reg_metas),
                              "id": "", "url": reg_metas[0]["url"], "pending": []}
    else:
        m = reg_metas[0]
        for k in ("key", "short", "count"):
            m.pop(k, None)
        out["laws"]["reg"] = m
    # 既存データとキーの並びをそろえる（変更検知のため）
    out["laws"] = {k: out["laws"][k] for k in ROLES}
    return out


def main():
    only = sys.argv[1:]
    stamp = datetime.datetime.now(JST).strftime("%Y-%m-%d")
    failed = []
    for cfg in SETS:
        if only and cfg["id"] not in only:
            continue
        try:
            data = build_set(cfg)
        except Exception as e:
            print("FAILED", cfg["id"], repr(e))
            failed.append(cfg["id"])
            continue
        out = f"sandan/{cfg['id']}/data.json"
        try:
            with open(out, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            old = None
        if old and {k: v for k, v in old.items() if k != "updated"} == data:
            print("  unchanged:", out)
            continue
        data["updated"] = stamp
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print("  wrote:", out, os.path.getsize(out), "bytes")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
