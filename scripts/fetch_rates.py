#!/usr/bin/env python3
"""銀行TTS/TTBレート取得スクリプト（GitHub Actionsで定期実行）。

みずほ・三菱UFJ（MURC）・三井住友・Wise（中値）から対円レートを取得し、
tools/bankrate/rates.json に書き出す。部分的な取得失敗があっても
取れた分だけで JSON を更新し、exit 0 で終える（errors に記録）。
"""
import json, re, sys, datetime, urllib.request

OUT = "tools/bankrate/rates.json"
CCYS = ["USD", "EUR", "GBP", "CNY", "TWD", "KRW", "VND"]
JPNAME = {
    "米ドル": "USD", "ユーロ": "EUR", "英ポンド": "GBP",
    "中国人民元": "CNY", "人民元": "CNY",
    "台湾ドル": "TWD", "ニュー台湾ドル": "TWD", "新台湾ドル": "TWD",
    "韓国ウォン": "KRW", "ウォン": "KRW",
    "ベトナムドン": "VND", "ドン": "VND",
}
# 対円の常識的な per-1 レンジ（単位の自動判定に使う）
SANE = {
    "USD": (60, 400), "EUR": (80, 400), "GBP": (100, 500),
    "CNY": (10, 60), "TWD": (2, 15), "KRW": (0.03, 0.4), "VND": (0.002, 0.02),
}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "ja,en;q=0.8"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


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
    return (max(a, b), min(a, b))


def get_mizuho(out, errors):
    try:
        raw = fetch("https://www.mizuhobank.co.jp/market/quote.csv")
        text = raw.decode("shift_jis", errors="replace")
        print("--- mizuho head ---")
        print("\n".join(text.splitlines()[:8]))
        rates = {}
        for line in text.splitlines():
            cells = [c.strip().strip('"') for c in line.split(",")]
            if not cells:
                continue
            ccy = None
            for cell in cells[:3]:
                for jp, code in JPNAME.items():
                    if jp == cell or (jp in cell and len(cell) <= len(jp) + 4):
                        ccy = code
                        break
                if ccy:
                    break
            if not ccy or ccy in rates:
                continue
            nums = floats_in(",".join(cells[1:]))
            pair = parse_pair(ccy, nums[:2]) if len(nums) >= 2 else None
            if pair:
                rates[ccy] = {"tts": pair[0], "ttb": pair[1]}
                print("mizuho", ccy, pair, "raw:", line[:120])
        if rates:
            out["mizuho"] = rates
        else:
            errors["mizuho"] = "parse: no rows matched"
    except Exception as e:
        errors["mizuho"] = repr(e)


def get_mufg(out, errors):
    try:
        raw = fetch("https://www.murc-kawasesouba.jp/fx/index.php")
        text = raw.decode("utf-8", errors="replace")
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S)
        print("--- murc length", len(text), "---")
        rows = re.split(r"<tr[^>]*>", text)
        rates = {}
        for row in rows:
            plain = re.sub(r"<[^>]+>", " ", row)
            m = re.search(r"\b(USD|EUR|GBP|CNY|TWD|KRW|VND)\b", plain)
            if not m:
                continue
            ccy = m.group(1)
            if ccy in rates:
                continue
            nums = floats_in(plain[m.end():])
            pair = parse_pair(ccy, nums[:2]) if len(nums) >= 2 else None
            if pair:
                rates[ccy] = {"tts": pair[0], "ttb": pair[1]}
                print("murc", ccy, pair, "raw:", " ".join(plain.split())[:120])
        if rates:
            out["mufg"] = rates
        else:
            errors["mufg"] = "parse: no rows matched; head=" + " ".join(re.sub(r"<[^>]+>", " ", text).split())[:300]
    except Exception as e:
        errors["mufg"] = repr(e)


def get_smbc(out, errors):
    candidates = [
        "https://www.smbc.co.jp/kojin/kawase/",
        "https://www.smbc.co.jp/kojin/soukin/gaika/soba/",
        "https://www.smbc.co.jp/kojin/gaika/soba/",
    ]
    last = None
    for url in candidates:
        try:
            raw = fetch(url)
            text = raw.decode("utf-8", errors="replace")
            plain_all = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S))
            print("--- smbc", url, "len", len(text), "---")
            print(" ".join(plain_all.split())[:400])
            rates = {}
            for row in re.split(r"<tr[^>]*>", text):
                plain = re.sub(r"<[^>]+>", " ", row)
                ccy = None
                m = re.search(r"\b(USD|EUR|GBP|CNY|TWD|KRW|VND)\b", plain)
                if m:
                    ccy = m.group(1)
                    tail = plain[m.end():]
                else:
                    for jp, code in JPNAME.items():
                        if jp in plain:
                            ccy = code
                            tail = plain.split(jp, 1)[1]
                            break
                if not ccy or ccy in rates:
                    continue
                nums = floats_in(tail)
                pair = parse_pair(ccy, nums[:2]) if len(nums) >= 2 else None
                if pair:
                    rates[ccy] = {"tts": pair[0], "ttb": pair[1]}
                    print("smbc", ccy, pair, "raw:", " ".join(plain.split())[:120])
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
        for url in (
            f"https://wise.com/rates/live?source={ccy}&target=JPY",
            f"https://api.wise.com/v1/rates?source={ccy}&target=JPY",
        ):
            try:
                raw = fetch(url, timeout=15)
                data = json.loads(raw.decode("utf-8", errors="replace"))
                if isinstance(data, list) and data:
                    data = data[0]
                v = data.get("value") or data.get("rate")
                if v:
                    rates[ccy] = {"mid": float(v)}
                    got = True
                    break
            except Exception as e:
                last = f"{url}: {e!r}"
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
