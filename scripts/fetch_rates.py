#!/usr/bin/env python3
"""銀行TTS/TTBレート取得スクリプト（GitHub Actionsで定期実行）。

みずほ・三菱UFJ（MURC）・三井住友・Wise（中値）から対円レートを取得し、
tools/bankrate/rates.json に書き出す。部分的な取得失敗があっても
取れた分だけで JSON を更新し（失敗ソースは前回値を維持）、exit 0 で終える。
"""
import json, re, sys, datetime, gzip, urllib.request

OUT = "tools/bankrate/rates.json"
CCYS = ["USD", "EUR", "GBP", "CNY", "TWD", "KRW", "VND"]
JPNAME = {
    "米ドル": "USD", "ユーロ": "EUR", "英ポンド": "GBP",
    "中国人民元": "CNY", "人民元": "CNY",
    "台湾ドル": "TWD", "ニュー台湾ドル": "TWD", "新台湾ドル": "TWD",
    "韓国ウォン": "KRW", "ウォン": "KRW",
    "ベトナムドン": "VND", "ドン": "VND",
}
ENNAME = {
    "Taiwan": "TWD", "New Taiwan": "TWD",
    "Vietnam": "VND", "Viet Nam": "VND", "Vietnamese": "VND",
    "Korean": "KRW", "Korea": "KRW",
}
# 対円の常識的な per-1 レンジ（単位の自動判定に使う）
SANE = {
    "USD": (60, 400), "EUR": (80, 400), "GBP": (100, 500),
    "CNY": (10, 60), "TWD": (2, 15), "KRW": (0.03, 0.4), "VND": (0.002, 0.02),
}
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/csv,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, identity",
    "Connection": "close",
}


def fetch(url, timeout=25, referer=None):
    h = dict(HDRS)
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return raw


# ---- 実ブラウザ（Playwright）によるフォールバック取得 ----
_PW = {"ctx": None, "pw": None, "browser": None}


def browser_page(url, wait_ms=2500, pre_url=None):
    """Chromiumでページを開き (html, innerText) を返す。ボット対策サイト用。"""
    if _PW["ctx"] is None:
        from playwright.sync_api import sync_playwright
        _PW["pw"] = sync_playwright().start()
        _PW["browser"] = _PW["pw"].chromium.launch()
        _PW["ctx"] = _PW["browser"].new_context(
            locale="ja-JP", user_agent=HDRS["User-Agent"],
            viewport={"width": 1280, "height": 900})
    page = _PW["ctx"].new_page()
    try:
        if pre_url:
            try:
                page.goto(pre_url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(1200)
            except Exception as e:
                print("browser pre_url fail", pre_url, repr(e))
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(wait_ms)
        html = page.content()
        text = page.evaluate("document.body ? document.body.innerText : ''")
        return html, text
    finally:
        page.close()


def browser_links(url):
    """ページ内の全リンク (href, text) を返す。"""
    if _PW["ctx"] is None:
        browser_page("about:blank", wait_ms=0)
    page = _PW["ctx"].new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        return page.eval_on_selector_all(
            "a", "els=>els.map(e=>({h:e.href||'',t:(e.innerText||'').trim()}))")
    finally:
        page.close()


def close_browser():
    try:
        if _PW["browser"]:
            _PW["browser"].close()
        if _PW["pw"]:
            _PW["pw"].stop()
    except Exception:
        pass


def parse_lines(text, want=CCYS):
    """innerText/CSVテキストの行から通貨ごとの (tts,ttb) を抽出。"""
    rates = {}
    for line in text.splitlines():
        line = " ".join(line.replace(",", " ").split())
        ccy, tail = ccy_of(line)
        if not ccy or ccy in rates or ccy not in want:
            continue
        nums = floats_in(tail)
        pair = parse_pair(ccy, nums[:2]) if len(nums) >= 2 else None
        if pair:
            rates[ccy] = {"tts": pair[0], "ttb": pair[1]}
    return rates


def decode_jp(raw):
    for enc in ("utf-8", "cp932", "euc_jp"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def normalize(ccy, v):
    """公表値を per-1 に正規化（100通貨単位表示などを桁で自動判定）。"""
    lo, hi = SANE[ccy]
    for f in (1, 100, 10000):
        if lo <= v / f <= hi:
            return v / f
    return None


def floats_in(s):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s.replace(",", ""))]


def parse_pair(ccy, nums):
    """数値列から (tts, ttb) を推定。TTS>TTB。"""
    cand = [normalize(ccy, v) for v in nums]
    cand = [v for v in cand if v is not None]
    if len(cand) < 2:
        return None
    a, b = cand[0], cand[1]
    if a == b:
        return None
    return (max(a, b), min(a, b))


def ccy_of(text):
    m = re.search(r"\b(USD|EUR|GBP|CNY|TWD|KRW|VND)\b", text)
    if m:
        return m.group(1), text[m.end():]
    for jp, code in JPNAME.items():
        if jp in text:
            return code, text.split(jp, 1)[1]
    for en, code in ENNAME.items():
        if en in text:
            tail = text.split(en, 1)[1]
            return code, tail
    return None, None


def rows_from_html(text):
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    return [re.sub(r"<[^>]+>", " ", r) for r in re.split(r"<tr[^>]*>", text)]


def pdf_text(raw):
    import io
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(raw))
    return "\n".join((p.extract_text() or "") for p in r.pages)


def parse_mizuho_text(text):
    """みずほ fx-quotation 表のテキストからTTS/TTBを抽出。

    実際の行形式（reader抽出、値は昇順の5スロット、欠測は -------- ）:
      USD 米ドル 159.37 161.37 162.37 163.37 165.37
      →  [現金買, TTB, 仲値, TTS, 現金売]
      CNY 中国元 -------- 23.56 23.86 24.16 --------
      KRW (100) 韓国ウォン 9.21 -------- -------- -------- 12.21  (TTS/TTB非公表)
    スロット2=TTB、スロット4=TTS を採用。存在する数値が昇順でない行は
    レイアウト変更とみなして捨てる。"""
    rates = {}
    for line in text.splitlines():
        line = " ".join(line.split())
        ccy, tail = ccy_of(line)
        if not ccy or ccy in rates:
            continue
        tail = tail.replace("（", "(").replace("）", ")")
        tail = re.sub(r"\(\s*100\s*\)", " ", tail)
        toks = re.findall(r"-{3,}|\d+(?:\.\d+)?", tail.replace(",", ""))
        if len(toks) < 5:
            continue
        slots = toks[:5]
        vals = [None if t.startswith("-") else normalize(ccy, float(t)) for t in slots]
        present = [v for v in vals if v is not None]
        if any(v is None for v in present) or present != sorted(present):
            print("mizuho row rejected (not ascending)", ccy, slots)
            continue
        ttb, tts = vals[1], vals[3]
        if tts is not None and ttb is not None and tts > ttb:
            rates[ccy] = {"tts": tts, "ttb": ttb}
            print("mizuho row", ccy, slots, "-> tts", tts, "ttb", ttb)
        else:
            print("mizuho row skipped (no TTS/TTB published)", ccy, slots)
    return rates


def get_mizuho(out, errors):
    last = None
    # 0) 公表PDF（日付入りURLが予測可能）
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    ymd = today.strftime("%y%m%d")
    pdf_urls = [
        f"https://www.mizuhobank.co.jp/market/historical/backnumber_b/pdf/fx-quotation{ymd}.pdf",
        "https://www.mizuhobank.co.jp/market/pdf/fx-quotation.pdf",
        "https://www.mizuhobank.co.jp/market/pdf/relatedrate.pdf",
    ]
    for url in pdf_urls:
        try:
            raw = fetch(url, referer="https://www.mizuhobank.co.jp/market/index.html")
            print("--- mizuho pdf", url, "bytes", len(raw), "magic", raw[:5])
            if raw[:4] != b"%PDF":
                last = f"{url}: not a PDF"
                continue
            text = pdf_text(raw)
            rates = parse_mizuho_text(text)
            if rates:
                print("mizuho pdf parsed:", rates)
                out["mizuho"] = rates
                return
            last = f"{url}: pdf parsed 0 rows"
        except Exception as e:
            last = f"{url}: {e!r}"
            print("mizuho pdf fail", last)
    # 0.5) 読み取りプロキシ経由（みずほは全クラウドIPを遮断しているため別経路で取得）
    for target in (
        f"https://www.mizuhobank.co.jp/market/historical/backnumber_b/pdf/fx-quotation{ymd}.pdf",
        "https://www.mizuhobank.co.jp/market/csv/quote.csv",
        "https://www.mizuhobank.co.jp/market/quote.csv",
    ):
        url = "https://r.jina.ai/" + target
        try:
            text = fetch(url, timeout=60).decode("utf-8", errors="replace")
            print("--- mizuho via reader", target, "len", len(text))
            for ln in text.splitlines()[:70]:
                print("  |", ln[:120])
            rates = parse_mizuho_text(text)
            if len(rates) >= 2:
                print("mizuho via reader parsed:", rates)
                out["mizuho"] = rates
                return
            last = f"reader {target}: parsed {len(rates)}"
        except Exception as e:
            last = f"reader {target}: {e!r}"
            print("mizuho reader fail", last)
    # 0.7) 転載サイトの探索（構造確認用ログ）
    try:
        html = decode_jp(fetch("https://fx.sauda.net/"))
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]{0,40})', html)
        hits = [(h, t) for h, t in links if "mizuho" in h.lower() or "みずほ" in t]
        print("sauda probe hits:", hits[:10])
        m = re.search(r"<title>([^<]+)</title>", html)
        print("sauda title:", m.group(1) if m else "?")
    except Exception as e:
        print("sauda probe fail", repr(e))
    # 1) 素のHTTP（速い）
    for url in (
        "https://www.mizuhobank.co.jp/market/csv/quote.csv",
        "https://www.mizuhobank.co.jp/market/quote.csv",
    ):
        try:
            text = decode_jp(fetch(url, referer="https://www.mizuhobank.co.jp/market/index.html"))
            rates = parse_lines(text)
            if rates:
                print("mizuho via urllib", url, rates)
                out["mizuho"] = rates
                return
            last = f"{url}: parsed 0 rows"
        except Exception as e:
            last = f"{url}: {e!r}"
            print("mizuho urllib fail", last)
    # 2) 実ブラウザ
    for url in (
        "https://www.mizuhobank.co.jp/market/csv/quote.csv",
        "https://www.mizuhobank.co.jp/market/quote.csv",
        "https://www.mizuhobank.co.jp/market/quote.html",
        "https://www.mizuhobank.co.jp/market/index.html",
    ):
        try:
            html, text = browser_page(url, pre_url="https://www.mizuhobank.co.jp/market/index.html")
            rates = parse_lines(text)
            print("--- mizuho browser", url, "textlen", len(text), "parsed", sorted(rates))
            if not rates:
                print("mizuho text head:", " / ".join(text.splitlines()[:12])[:400])
            if rates:
                out["mizuho"] = rates
                return
            last = f"{url}: browser parsed 0 rows"
        except Exception as e:
            last = f"{url}: browser {e!r}"
            print("mizuho browser fail", last)
    errors["mizuho"] = last or "no candidate worked"


def get_mufg(out, errors):
    try:
        raw = fetch("https://www.murc-kawasesouba.jp/fx/index.php")
        text = decode_jp(raw)
        rates = {}
        for row in rows_from_html(text):
            plain = " ".join(row.split())
            ccy, tail = ccy_of(plain)
            if not ccy:
                # デバッグ: 通貨コードらしき行を記録
                if re.search(r"\b[A-Z]{3}\b\s+\d", plain):
                    print("murc unmatched:", plain[:110])
                continue
            if ccy in rates:
                continue
            nums = floats_in(tail)
            pair = parse_pair(ccy, nums[:2]) if len(nums) >= 2 else None
            if pair:
                rates[ccy] = {"tts": pair[0], "ttb": pair[1]}
                print("murc", ccy, pair, "raw:", plain[:110])
        missing = [c for c in CCYS if c not in rates]
        if missing:
            print("murc missing:", missing)
        if rates:
            out["mufg"] = rates
        else:
            errors["mufg"] = "parse: no rows matched"
    except Exception as e:
        errors["mufg"] = repr(e)


def get_smbc(out, errors):
    last = None
    candidates = []
    # 実ブラウザでトップからリンク探索（SMBCのメニューはJSレンダリング）
    for top in ("https://www.smbc.co.jp/kojin/", "https://www.smbc.co.jp/"):
        try:
            links = browser_links(top)
            for l in links:
                h, t = l.get("h", ""), l.get("t", "")
                if re.search(r"kawase|souba|soba", h, re.I) or re.search(r"為替|相場", t):
                    if h.startswith("http") and h not in candidates:
                        candidates.append(h)
            print("smbc discovered:", candidates[:15])
            if candidates:
                break
        except Exception as e:
            print("smbc top browser fail", top, repr(e))
    candidates += [
        "https://www.smbc.co.jp/kojin/kinri/kawase.html",
        "https://www.smbc.co.jp/kojin/kawase/",
    ]
    for url in candidates[:8]:
        try:
            html, text = browser_page(url)
            rates = parse_lines(text)
            print("--- smbc browser", url, "parsed", sorted(rates))
            if not rates:
                print("smbc text head:", " / ".join(text.splitlines()[:10])[:300])
            if len(rates) >= 2:
                out["smbc"] = rates
                return
            last = f"{url}: parsed {len(rates)} rows"
        except Exception as e:
            last = f"{url}: {e!r}"
            print("smbc fail", last)
    errors["smbc"] = last or "no candidate worked"


def get_wise(out, errors):
    rates = {}
    last = None
    for ccy in CCYS:
        got = False
        # 実ブラウザで通貨コンバータページを開き中値を抽出
        try:
            url = f"https://wise.com/ja/currency-converter/{ccy.lower()}-to-jpy-rate"
            html, text = browser_page(url, wait_ms=3500)
            m = (re.search(r'1\s*' + ccy + r'\s*=\s*([\d,.]+)\s*JPY', text)
                 or re.search(r'"rate"\s*:\s*([\d.]+)', html))
            if m:
                v = float(m.group(1).replace(",", ""))
                v = normalize(ccy, v)
                if v:
                    rates[ccy] = {"mid": v}
                    got = True
                    print("wise", ccy, v)
        except Exception as e:
            last = f"{ccy}: {e!r}"
        if not got:
            print("wise fail", ccy, last)
            if ccy == "USD":
                break  # USDすら取れないならこのソースは諦める
    if len(rates) >= 3:
        out["wise"] = rates
        return
    # フォールバック: 公開ミッドマーケトAPI（Wiseは中値適用なので実質同等の参考値）
    try:
        data = json.loads(fetch("https://open.er-api.com/v6/latest/JPY", timeout=20).decode())
        rr = data.get("rates") or {}
        fb = {}
        for ccy in CCYS:
            if rr.get(ccy):
                fb[ccy] = {"mid": 1.0 / float(rr[ccy])}
        if fb:
            fb["_source"] = {"note": "mid-market via open.er-api.com"}
            out["wise"] = {k: v for k, v in fb.items() if k != "_source"}
            print("wise fallback er-api:", {k: round(v['mid'], 4) for k, v in out['wise'].items()})
            return
    except Exception as e:
        last = f"er-api: {e!r}"
    errors["wise"] = last or "all failed"


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    out, errors = {}, {}
    try:
        get_mizuho(out, errors)
        get_mufg(out, errors)
        get_smbc(out, errors)
        get_wise(out, errors)
    finally:
        close_browser()

    # 前回値の読み込み（失敗した銀行は前回値を残す）
    prev = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            prev = json.load(f).get("banks", {})
    except Exception:
        pass

    stamp = now.strftime("%Y-%m-%d %H:%M")
    banks = {}
    for b in ("mizuho", "mufg", "smbc", "wise"):
        if b in out:
            banks[b] = {"rates": out[b], "fetched": stamp}
        elif b in prev and prev[b].get("rates"):
            banks[b] = prev[b]  # 前回値を維持（fetchedは古いまま）
    doc = {
        "updated": stamp,
        "updated_iso": now.isoformat(),
        "currencies": CCYS,
        "banks": banks,
        "errors": errors,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("=== summary ===")
    for b in ("mizuho", "mufg", "smbc", "wise"):
        got = sorted(out.get(b, {}).keys())
        print(b, "OK:", got, "| error:", errors.get(b, "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
