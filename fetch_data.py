"""업종별 종목 데이터 수집 -> data.js

- 현재가·등락률·시가총액: 키움 REST API(ka10001, kwcli). 사용 불가 시 네이버 증권으로 대체.
- EPS·추정EPS·BPS·ROE: 네이버 증권 (분기/연간 실적 기준, 가격과 무관하게 천천히 변함)
- PER = 현재가/EPS, Forward P/E = 현재가/추정EPS, PBR = 현재가/BPS  -> 매일 주가에 맞춰 재계산
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests

from sectors import SECTORS

H = {"User-Agent": "Mozilla/5.0"}
NAVER = "https://m.stock.naver.com/api/stock"
OUT = Path(__file__).parent / "data.js"


def num(s):
    """'1,234.5배' -> 1234.5, 해석 불가면 None"""
    if s is None:
        return None
    m = re.search(r"-?[\d,]+(?:\.\d+)?", str(s))
    return float(m.group().replace(",", "")) if m else None


def won(s):
    """'1,248조 1,805억' -> 억원 float"""
    if not s:
        return None
    jo = re.search(r"([\d,]+)조", s)
    rest = s.replace(jo.group(0), "") if jo else s
    eok = re.search(r"([\d,]+)억", rest)
    v = (float(jo.group(1).replace(",", "")) * 10000 if jo else 0) + (float(eok.group(1).replace(",", "")) if eok else 0)
    return v or None


def get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(1 + i)


def roe_rows(code):
    f = get(f"{NAVER}/{code}/finance/annual")["financeInfo"]
    row = next((r for r in f["rowList"] if r["title"] == "ROE"), None)
    actual = cons = ay = cy = None
    if row:
        for t in f["trTitleList"]:
            v = num(row["columns"].get(t["key"], {}).get("value"))
            if v is None:
                continue
            if t["isConsensus"] == "Y":
                if cons is None:
                    cons, cy = v, t["title"].rstrip(".")
            else:
                actual, ay = v, t["title"].rstrip(".")
    return actual, ay, cons, cy


def naver_fetch(code):
    integ = get(f"{NAVER}/{code}/integration")
    basic = get(f"{NAVER}/{code}/basic")
    info = {t["code"]: t["value"] for t in integ["totalInfos"]}
    roe, roe_y, roe_f, roe_fy = roe_rows(code)
    return {
        "name": integ["stockName"],
        "market": basic.get("stockExchangeName") or basic.get("stockExchangeType", {}).get("name", ""),
        "price": num(basic["closePrice"]),
        "change": num(basic["compareToPreviousClosePrice"]),
        "changePct": num(basic["fluctuationsRatio"]),
        "marketCap": won(info.get("marketValue")),
        "eps": num(info.get("eps")), "cnsEps": num(info.get("cnsEps")), "bps": num(info.get("bps")),
        "per": num(info.get("per")), "fper": num(info.get("cnsPer")), "pbr": num(info.get("pbr")),
        "roe": roe, "roeYear": roe_y, "roeF": roe_f, "roeFYear": roe_fy,
    }


def kiwoom_client():
    try:
        from kiwoom import get_client
        return get_client()
    except Exception as e:  # noqa: BLE001
        print(f"[키움 사용 불가 -> 네이버 가격 사용] {e}", file=sys.stderr)
        return None


def kiwoom_quote(client, code):
    """키움 ka10001. 부호 포함 문자열을 정리해 반환."""
    body = client.fetch_page(api_id="ka10001", path="/api/dostk/stkinfo", body={"stk_cd": code}).body
    if body.get("return_code") not in (None, 0):
        raise RuntimeError(body.get("return_msg"))
    price = abs(num(body["cur_prc"]) or 0) or None
    return {"price": price, "change": num(body["pred_pre"]), "changePct": num(body["flu_rt"]),
            "marketCap": num(body["mac"])}


def derive(s):
    """가격 기준으로 밸류에이션 재계산 (적자·결측은 None)"""
    p = s["price"]
    pos = lambda v: v if v and v > 0 else None
    s["per"] = round(p / s["eps"], 2) if p and pos(s["eps"]) else pos(s["per"])
    s["fper"] = round(p / s["cnsEps"], 2) if p and pos(s["cnsEps"]) else pos(s["fper"])
    s["pbr"] = round(p / s["bps"], 2) if p and pos(s["bps"]) else s["pbr"]
    return s


def main():
    jobs = [(k, g, c) for k, sec in SECTORS.items() for g, cs in sec["groups"].items() for c in cs]
    seen, uniq = set(), []
    for j in jobs:  # 중복 코드 방지
        if j[2] not in seen:
            seen.add(j[2]); uniq.append(j)

    def safe(j):
        try:
            return j, naver_fetch(j[2])
        except Exception as e:  # noqa: BLE001
            print(f"FAIL naver {j[2]}: {e}", file=sys.stderr)
            return j, None

    with ThreadPoolExecutor(8) as ex:
        fetched = list(ex.map(safe, uniq))

    client = kiwoom_client()
    k_ok = k_fail = 0
    out = {k: {"name": sec["name"], "stocks": []} for k, sec in SECTORS.items()}
    for (sec, grp, code), d in fetched:
        if d is None:
            continue
        if client:
            try:
                d.update(kiwoom_quote(client, code))
                k_ok += 1
                time.sleep(0.2)
            except Exception as e:  # noqa: BLE001
                k_fail += 1
                print(f"WARN kiwoom {code}: {e} -> 네이버 가격 사용", file=sys.stderr)
        d = derive(d)
        out[sec]["stocks"].append({"code": code, "sub": grp, **d})

    payload = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "priceSource": f"키움증권 OpenAPI ({k_ok}종목)" if k_ok else "네이버 증권",
        "fundamentalSource": "네이버 증권(EPS·BPS·ROE·컨센서스)",
        "sectors": out,
    }
    n = sum(len(v["stocks"]) for v in out.values())
    if n < len(uniq) * 0.8:  # 실패 시 기존 data.js 보존
        sys.exit(f"수집 실패율이 높아 중단 ({n}/{len(uniq)}), data.js 유지")
    OUT.write_text("window.ALL_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"{n}/{len(uniq)} 종목 저장 (키움 성공 {k_ok}, 실패 {k_fail}) -> {OUT}")


if __name__ == "__main__":
    main()
