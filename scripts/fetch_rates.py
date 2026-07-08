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


def get_mizuho(out, errors):
    last = None
    for url in (
        "https://www.mizuhobank.co.jp/market/csv/quote.csv",
        "https://www.mizuhobank.co.jp/market/quote.csv",
    ):
        try:
            raw = fetch(url, referer="https://www.mizuhobank.co.jp/market/index.html")
            text = decode_jp(raw)
            print("--- mizuho", url, "head ---")
            print("\n".join(text.splitlines()[:6]))
            rates = {}
            for line in text.splitlines():
                cells = [c.strip().strip('"') for c in line.split(",")]
                joined = " ".join(cells[:3])
                ccy, _ = ccy_of(joined)
                if not ccy or ccy in rates:
                    continue
                nums = floats_in(",".join(cells[1:]))
                pair = parse_pair(ccy, nums[:2]) if len(nums) >= 2 else None
                if pair:
                    rates[ccy] = {"tts": pair[0], "ttb": pair[1]}
                    print("mizuho", ccy, pair, "raw:", line[:120])
            if rates:
                out["mizuho"] = rates
                return
            last = f"{url}: parsed 0 rows"
        except Exception as e:
            last = f"{url}: {e!r}"
            print("mizuho fail", last)
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
    candidates = [
        "https://www.smbc.co.jp/kojin/kinri/kawase.html",
        "https://www.smbc.co.jp/kojin/kawase/index.html",
        "https://www.smbc.co.jp/kojin/soukin/kawase.html",
    ]
    # トップからのリンク探索
    for top in ("https://www.smbc.co.jp/kojin/", "https://www.smbc.co.jp/"):
        try:
            text = decode_jp(fetch(top))
            links = re.findall(r'href="([^"]*(?:kawase|souba|soba|rate|kinri)[^"]*)"', text, flags=re.I)
            uniq = []
            for l in links:
                if l.startswith("//"):
                    l = "https:" + l
                elif l.startswith("/"):
                    l = "https://www.smbc.co.jp" + l
                if l.startswith("http") and l not in uniq:
                    uniq.append(l)
            print("smbc discovered links from", top, ":", uniq[:15])
            candidates = uniq[:10] + candidates
            break
        except Exception as e:
            print("smbc top fail", top, repr(e))
    last = None
    for url in candidates:
        try:
            text = decode_jp(fetch(url))
            plain_all = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)).split())
            print("--- smbc try", url, "len", len(text), "---")
            print(plain_all[:250])
            rates = {}
            for row in rows_from_html(text):
                plain = " ".join(row.split())
                ccy, tail = ccy_of(plain)
                if not ccy or ccy in rates:
                    continue
                nums = floats_in(tail)
                pair = parse_pair(ccy, nums[:2]) if len(nums) >= 2 else None
                if pair:
                    rates[ccy] = {"tts": pair[0], "ttb": pair[1]}
                    print("smbc", ccy, pair, "raw:", plain[:110])
            if rates:
                out["smbc"] = rates
                return
            last = f"{url}: parsed 0 rows"
        except Exception as e:
            last = f"{url}: {e!r}"
            print("smbc fail", last)
    errors["smbc"] = last or "no candidate worked"


def get_wise(out, errors):
    rates = {}
    last = None
    for ccy in CCYS:
        got = False
        # 1) 比較API（公開・キー不要のことが多い）
        try:
            url = f"https://api.wise.com/v3/comparisons/?sourceCurrency={ccy}&targetCurrency=JPY&sendAmount=10000"
            data = json.loads(fetch(url, timeout=20).decode("utf-8", errors="replace"))
            for p in data.get("providers", []):
                if p.get("alias") in ("wise", "transferwise") or "Wise" in (p.get("name") or ""):
                    qs = p.get("quotes") or []
                    if qs and qs[0].get("rate"):
                        rates[ccy] = {"mid": float(qs[0]["rate"])}
                        got = True
                        break
        except Exception as e:
            last = f"comparisons {ccy}: {e!r}"
        if got:
            continue
        # 2) 通貨コンバータページから埋め込みレートを抽出
        try:
            url = f"https://wise.com/jp/currency-converter/{ccy.lower()}-to-jpy-rate?amount=1"
            html = fetch(url, timeout=20).decode("utf-8", errors="replace")
            m = re.search(r'"rate"\s*:\s*([\d.]+)', html) or re.search(r'1\s*' + ccy + r'\s*=\s*([\d.]+)\s*JPY', html)
            if m:
                v = float(m.group(1))
                if normalize(ccy, v):
                    rates[ccy] = {"mid": v}
                    got = True
        except Exception as e:
            last = f"converter {ccy}: {e!r}"
        if not got:
            print("wise fail", ccy, last)
    if rates:
        out["wise"] = rates
    else:
        errors["wise"] = last or "all failed"


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    out, errors = {}, {}
    get_mizuho(out, errors)
    get_mufg(out, errors)
    get_smbc(out, errors)
    get_wise(out, errors)

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
