"""Freeze public price data, trustee documents and verification attempts."""

import argparse, gzip, json, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent


def request(url):
    with urlopen(
        Request(url, headers={"User-Agent": "ReplicableResearch/1.1"}), timeout=26
    ) as f:
        return f.read()


def collect(out):
    out.mkdir(parents=True, exist_ok=True)
    last = (
        json.loads((out / "web_index.json").read_text())
        if (out / "web_index.json").exists()
        else {}
    )
    index = request("https://www.mtgox.com/").decode()
    urls = {
        "plan_en.pdf": "https://www.mtgox.com/d/04y7ivbnz5gw.pdf",
        "trustee_20240705.pdf": "https://www.mtgox.com/img/pdf/20240705_01_announcement_en.pdf",
        "trustee_20221004.pdf": "https://www.mtgox.com/img/pdf/20221004_announcement_en.pdf",
        "trustee_20221028.pdf": "https://www.mtgox.com/img/pdf/20221028_announcement_en.pdf",
        "forum_topic.json": "https://gov.uniswap.org/t/13586.json",
        "fx_usd_eur.csv": "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?startPeriod=2014-01-01&endPeriod=2014-02-25&format=csvdata",
        "wayback_0636.html": "https://web.archive.org/web/20210724063600id_/https://app.uniswap.org/",
        "wayback_scripts.json": "https://web.archive.org/cdx/search/cdx?url=app.uniswap.org%2Fstatic%2Fjs%2F*&from=20210723&to=20210727&output=json&filter=statuscode%3A200",
        "cc2021.json": "https://index.commoncrawl.org/CC-MAIN-2021-31-index?url=app.uniswap.org&output=json",
        "archive_today.json": "https://archive.org/wayback/available?url=app.uniswap.org&timestamp=20210724063600",
    }
    for d in ("20211116", "20240716", "20240724", "20240731", "20240821", "20250327"):
        paths = re.findall(r'href="([^"]*' + d + r'[^"]*?_en\.pdf)"', index)
        if paths:
            urls["trustee_" + d + ".pdf"] = "https://www.mtgox.com" + paths[0]
    btc = "https://data.bitcoinity.org/export_data.csv?"
    for v, cur, typ in [
        ("mtgox", "USD", "volume"),
        ("bitstamp", "USD", "volume"),
        ("bitfinex", "USD", "volume"),
        ("mtgox", "EUR", "price"),
        ("btce", "USD", "price"),
        ("kraken", "USD", "price"),
    ]:
        urls[f"{v}_{cur}_{typ}.csv.gz"] = btc + urlencode(
            dict(
                c="e",
                data_type=typ,
                r="day",
                t="l",
                timespan="all",
                currency=cur,
                exchange=v,
            )
        )
    for a, w in [
        ("A", "0x2ead300eab9e407aa5e96766b2bc69d871d7f790"),
        ("B", "0x269ea4cd75a8ecabff55e47a34453801e412b991"),
    ]:
        urls["account_" + a + ".json"] = "https://eth.blockscout.com/api?" + urlencode(
            dict(
                module="account",
                action="txlist",
                address=w,
                startblock=12789855,
                endblock=12974517,
                page=1,
                offset=1000,
                sort="asc",
            )
        )

    def get(kv):
        k, u = kv
        if (out / k).exists() and last.get(k, {}).get("status") == 200:
            return k, last[k]
        try:
            b = request(u)
            (out / k).write_bytes(gzip.compress(b, mtime=0) if k.endswith(".gz") else b)
            return k, dict(url=u, status=200, bytes=len(b))
        except (OSError, ValueError) as e:
            return k, dict(url=u, status=getattr(e, "code", None), error=str(e))

    with ThreadPoolExecutor(10) as ex:
        info = dict(ex.map(get, urls.items()))
    (out / "web_index.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
    for k, v in info.items():
        print(k, v.get("status"), v.get("bytes", ""), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "raw")
    collect(p.parse_args().out)
