#!/usr/bin/env python3
"""金融庁公表データの取得（GitHub Actionsで定期実行）。

1. 資金移動業者登録一覧: 一覧ファイル（Excel/PDF）を取得し
   fund-transfer/registry/operators.json に保存。前回との差分
   （新規登録・登録抹消）を fund-transfer/registry/changes.json に追記。
2. 行政処分情報: 金融庁の行政処分ページから資金決済関連の項目を抽出し
   fund-transfer/shobun/items.json にマージ。

部分的な失敗があっても取れた分だけ更新し exit 0。
"""
import json, re, sys, io, datetime, urllib.request

BASE = "https://www.fsa.go.jp"
REG_OUT = "fund-transfer/registry/operators.json"
CHG_OUT = "fund-transfer/registry/changes.json"
SHB_OUT = "fund-transfer/shobun/items.json"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}
SHOBUN_KEYWORDS = ("資金移動", "資金決済", "前払式", "暗号資産", "仮想通貨", "為替取引")


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def decode_jp(raw):
    for enc in ("utf-8", "cp932", "euc_jp"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def absolutize(href, base_url):
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return base_url.rsplit("/", 1)[0] + "/" + href


def links_of(html, base_url):
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, flags=re.S | re.I):
        text = re.sub(r"<[^>]+>", "", m.group(2))
        text = " ".join(text.split())
        out.append((absolutize(m.group(1), base_url), text))
    return out


# ---------------- 資金移動業者登録一覧 ----------------

def parse_reg_xlsx(raw):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
    columns, ops = [], []
    for ws in wb.worksheets:
        rows = [[("" if c is None else str(c).strip()) for c in row]
                for row in ws.iter_rows(values_only=True)]
        hi = None
        for i, row in enumerate(rows[:15]):
            if any("登録番号" in c for c in row):
                hi = i
                break
        if hi is None:
            continue
        hdr = rows[hi]
        # 空でない列だけ残す
        keep = [j for j, h in enumerate(hdr) if h]
        cols = [hdr[j] for j in keep]
        print("registry sheet:", ws.title, "columns:", cols[:8])
        if not columns:
            columns = cols
        for row in rows[hi + 1:]:
            vals = [row[j] if j < len(row) else "" for j in keep]
            if not any(vals):
                continue
            ops.append(dict(zip(cols, vals)))
    return columns, ops


def rec_key(rec):
    no = name = ""
    for k, v in rec.items():
        if "登録番号" in k and not no:
            no = v
        elif "番号" in k and not no:
            no = v
        if not name and ("名称" in k or "商号" in k or "業者名" in k or "氏名" in k):
            name = v
    return no, name


def get_registry(stamp, errors):
    try:
        html = decode_jp(fetch(BASE + "/menkyo/menkyo.html"))
    except Exception as e:
        errors["registry"] = f"menkyo.html: {e!r}"
        print("registry index fail", repr(e))
        return
    cand = [(u, t) for u, t in links_of(html, BASE + "/menkyo/menkyo.html")
            if "資金移動" in t or "shikin" in u.lower()]
    print("registry candidate links:", cand[:8])
    columns, ops, src = [], [], None
    for url, t in cand:
        try:
            raw = fetch(url)
        except Exception as e:
            print("registry dl fail", url, repr(e))
            continue
        if raw[:2] == b"PK" or url.endswith((".xlsx", ".xls")):
            try:
                columns, ops = parse_reg_xlsx(raw)
            except Exception as e:
                print("registry xlsx parse fail", url, repr(e))
                continue
        elif raw[:4] == b"%PDF":
            print("registry: PDF found at", url, "- xlsx優先のため一旦スキップ")
            continue
        elif b"<html" in raw[:500].lower() or b"<!doctype" in raw[:500].lower():
            # 中間ページ: さらにファイルリンクを探す
            for u2, t2 in links_of(decode_jp(raw), url):
                if u2.endswith((".xlsx", ".xls")):
                    try:
                        columns, ops = parse_reg_xlsx(fetch(u2))
                        url = u2
                    except Exception as e:
                        print("registry nested xlsx fail", u2, repr(e))
                    if ops:
                        break
        if ops:
            src = url
            break
    if not ops:
        errors["registry"] = "no parsable list found"
        return

    print("registry parsed:", len(ops), "operators from", src)

    # 前回との差分
    prev_ops, prev_exists = [], False
    try:
        with open(REG_OUT, encoding="utf-8") as f:
            prev = json.load(f)
            prev_ops = prev.get("operators", [])
            prev_exists = bool(prev_ops)
    except Exception:
        pass

    new_keys = {rec_key(r): r for r in ops}
    old_keys = {rec_key(r): r for r in prev_ops}
    added = [new_keys[k] for k in new_keys if k not in old_keys]
    removed = [old_keys[k] for k in old_keys if k not in new_keys]
    if prev_exists and (added or removed):
        try:
            with open(CHG_OUT, encoding="utf-8") as f:
                changes = json.load(f)
        except Exception:
            changes = []
        changes.insert(0, {"date": stamp, "added": added, "removed": removed})
        with open(CHG_OUT, "w", encoding="utf-8") as f:
            json.dump(changes[:200], f, ensure_ascii=False, indent=1)
        print("registry diff: +", len(added), "-", len(removed))
    elif not prev_exists:
        print("registry: baseline saved (no diff on first run)")

    with open(REG_OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": stamp, "source": src, "columns": columns,
                   "count": len(ops), "operators": ops}, f, ensure_ascii=False, indent=1)


# ---------------- 行政処分情報 ----------------

def get_shobun(stamp, errors):
    idx_candidates = [
        BASE + "/status/syobun/index.html",
        BASE + "/status/gyouseishobun/index.html",
        BASE + "/status/s_gyousei/index.html",
    ]
    pages = []
    # 金融庁トップ等から「行政処分」リンクを探索
    for top in (BASE + "/index.html", BASE + "/policy/index.html", BASE + "/status/index.html"):
        try:
            html = decode_jp(fetch(top))
            for u, t in links_of(html, top):
                if "行政処分" in t and u not in [p for p, _ in pages]:
                    pages.append((u, t))
        except Exception as e:
            print("shobun discover fail", top, repr(e))
    print("shobun discovered links:", pages[:8])
    for u in idx_candidates:
        pages.append((u, "candidate"))

    items = []
    seen_pages = set()
    for url, t in pages[:6]:
        if url in seen_pages:
            continue
        seen_pages.add(url)
        try:
            html = decode_jp(fetch(url))
        except Exception as e:
            print("shobun page fail", url, repr(e))
            continue
        print("--- shobun page", url, "len", len(html))
        # 年度別ページへのリンクも1階層だけ辿る
        sub = [(u2, t2) for u2, t2 in links_of(html, url)
               if re.search(r"(令和|平成)\S*年度|nendo|\d{4}", u2 + t2) and "行政処分" in (t2 + url)]
        targets = [(url, html)]
        for u2, t2 in sub[:4]:
            if u2 in seen_pages:
                continue
            seen_pages.add(u2)
            try:
                targets.append((u2, decode_jp(fetch(u2))))
                print("shobun sub page", u2, t2[:40])
            except Exception as e:
                print("shobun sub fail", u2, repr(e))
        for purl, phtml in targets:
            # 表の行ごとに: 日付・リンク・テキスト
            for row in re.split(r"<tr[^>]*>", phtml):
                plain = " ".join(re.sub(r"<[^>]+>", " ", row).split())
                if not any(k in plain for k in SHOBUN_KEYWORDS):
                    continue
                lm = re.search(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', row, flags=re.S)
                if not lm:
                    continue
                title = " ".join(re.sub(r"<[^>]+>", "", lm.group(2)).split())
                if not title:
                    title = plain[:80]
                dm = re.search(r"(令和\s*\d+|平成\s*\d+|\d{4})\s*年\s*\d+\s*月\s*\d+\s*日", plain)
                items.append({
                    "date": dm.group(0).replace(" ", "") if dm else "",
                    "title": title[:120],
                    "url": absolutize(lm.group(1), purl),
                })
    # 重複除去
    uniq, seen = [], set()
    for it in items:
        k = it["url"]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    print("shobun extracted:", len(uniq))
    for it in uniq[:10]:
        print("  shobun item:", it["date"], it["title"][:60], it["url"])
    if not uniq:
        errors["shobun"] = "no items extracted"
        return
    # 既存とマージ（既存を残しつつ新規を追加）
    try:
        with open(SHB_OUT, encoding="utf-8") as f:
            old = json.load(f).get("items", [])
    except Exception:
        old = []
    old_urls = {o["url"] for o in old}
    merged = old + [it for it in uniq if it["url"] not in old_urls]
    with open(SHB_OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": stamp, "items": merged}, f, ensure_ascii=False, indent=1)


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    stamp = now.strftime("%Y-%m-%d %H:%M")
    errors = {}
    get_registry(stamp, errors)
    get_shobun(stamp, errors)
    print("=== summary ===", "errors:", errors or "-")
    return 0


if __name__ == "__main__":
    sys.exit(main())
