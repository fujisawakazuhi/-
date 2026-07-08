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

SCHEMA = 2


def clean_cell(v):
    v = " ".join(str(v).split())
    # "2022-01-31 00:00:00" → "2022-01-31"
    m = re.match(r"^(\d{4}-\d{2}-\d{2}) 00:00:00$", v)
    return m.group(1) if m else v


def parse_reg_xlsx(raw):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
    columns, ops = [], []
    for ws in wb.worksheets:
        rows = [[("" if c is None else clean_cell(c)) for c in row]
                for row in ws.iter_rows(values_only=True)]
        hi = None
        for i, row in enumerate(rows[:15]):
            if any("登録番号" in c for c in row):
                hi = i
                break
        if hi is None:
            continue
        hdr = rows[hi]
        keep = [j for j, h in enumerate(hdr) if h]
        cols = [hdr[j] for j in keep]
        print("registry sheet:", ws.title, "columns:", cols)
        if not columns:
            columns = cols
        cur = {}  # 所管・業務の種別のセクション値を引き継ぐ
        for row in rows[hi + 1:]:
            vals = [row[j] if j < len(row) else "" for j in keep]
            if not any(vals):
                continue
            rec = dict(zip(cols, vals))
            no = rec.get("登録番号", "")
            name = next((rec[k] for k in rec if ("名" in k and "法人" not in k) and rec[k]), "")
            for k in ("所管", "業務の種別"):
                if rec.get(k):
                    rec[k] = re.sub(r"【[^】]*】", "", rec[k]).strip()
                    cur[k] = rec[k]
            if not no and not name:
                continue  # 種別見出し行など
            for k in ("所管", "業務の種別"):
                if k in cols and not rec.get(k):
                    rec[k] = cur.get(k, "")
            ops.append(rec)
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

    # 前回との差分（スキーマ変更時はベースラインを取り直す）
    prev_ops, prev_exists = [], False
    try:
        with open(REG_OUT, encoding="utf-8") as f:
            prev = json.load(f)
            if prev.get("schema") == SCHEMA:
                prev_ops = prev.get("operators", [])
                prev_exists = bool(prev_ops)
            else:
                print("registry: schema changed -> new baseline")
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
        json.dump({"updated": stamp, "schema": SCHEMA, "source": src, "columns": columns,
                   "count": len(ops), "operators": ops}, f, ensure_ascii=False, indent=1)


# ---------------- 行政処分情報 ----------------

def get_shobun(stamp, errors):
    """報道発表の年度別一覧から「行政処分」×資金決済関連キーワードの発表を抽出。"""
    # 年度別の報道発表一覧ページを発見
    list_pages = []
    for top in (BASE + "/news/index.html", BASE + "/news/"):
        try:
            html = decode_jp(fetch(top))
            list_pages.append((top, html))
            # 年度別アーカイブへのリンクがあれば辿る（現状の金融庁サイトには無いが将来用）
            for u, t in links_of(html, top):
                if re.search(r"(令和|平成)\s*\d+年度", t) and u.endswith(".html"):
                    if u not in [p for p, _ in list_pages]:
                        list_pages.append((u, None))
            break
        except Exception as e:
            print("shobun news index fail", top, repr(e))
    print("shobun list pages:", [u for u, _ in list_pages][:6])

    items = []
    seen_pages = set()
    for url, html in list_pages[:5]:
        if url in seen_pages:
            continue
        seen_pages.add(url)
        if html is None:
            try:
                html = decode_jp(fetch(url))
            except Exception as e:
                print("shobun list fail", url, repr(e))
                continue
        print("--- shobun list", url, "len", len(html))
        # RSS/RDF形式
        if "<item" in html:
            for im in re.finditer(r"<item[^>]*>(.*?)</item>", html, flags=re.S):
                blk = im.group(1)
                tm = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", blk, flags=re.S)
                lk = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", blk, flags=re.S)
                dt = re.search(r"<(?:dc:date|pubDate)>(.*?)</", blk, flags=re.S)
                if not tm or not lk:
                    continue
                title = " ".join(tm.group(1).split())
                if not re.search(r"行政処分|業務停止|業務改善|登録の取消|登録取消", title):
                    continue
                if not any(k in title for k in SHOBUN_KEYWORDS):
                    print("shobun near-miss(rss):", title[:80])
                    continue
                items.append({"date": (dt.group(1).strip()[:10] if dt else ""),
                              "title": title[:140], "url": lk.group(1).strip()})
            continue
        # 行単位（tr / li / dd）で日付・リンク・タイトルを抽出
        blocks = re.split(r"<(?:tr|li|dt)[^>]*>", html)
        near_miss = 0
        for blk in blocks:
            plain = " ".join(re.sub(r"<[^>]+>", " ", blk).split())
            lm = re.search(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', blk, flags=re.S)
            if not lm:
                continue
            title = " ".join(re.sub(r"<[^>]+>", "", lm.group(2)).split()) or plain[:80]
            is_action = re.search(r"行政処分|業務停止|業務改善|登録の取消|登録取消", title)
            if not is_action:
                continue
            if not any(k in title for k in SHOBUN_KEYWORDS):
                near_miss += 1
                if near_miss <= 5:
                    print("shobun near-miss:", title[:80])
                continue
            dm = (re.search(r"(令和|平成)\s*\d+\s*年\s*\d+\s*月\s*\d+\s*日", plain)
                  or re.search(r"\d{4}\s*年\s*\d+\s*月\s*\d+\s*日", plain))
            items.append({
                "date": dm.group(0).replace(" ", "") if dm else "",
                "title": title[:140],
                "url": absolutize(lm.group(1), url),
            })
        print("shobun page done, near-miss(actions w/o keyword):", near_miss)
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
    # 0件でも正常（該当する新着発表が無い週は普通にある）— 更新時刻だけ進める
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
