"""Compare the same token, direction and sizes at equally spaced UTC dates, using two archive providers."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from protocol import RAW, T, W, Q, C, ENDPOINTS, calldata, fetch, dump, read
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

dates = [date(2021, 7, 23) + timedelta(days=i) for i in range(-14, 15) if i]
sizes = [10**17, 5 * 10**17, 10**18, 5 * 10**18]


def boundary(day, root):
    key = str(day)
    target = int(datetime.combine(day, datetime.min.time(), timezone.utc).timestamp())
    targetfile = root / ("utc_" + key + ".json.gz")
    if targetfile.exists():
        return read(targetfile)["height"]
    url = "https://coins.llama.fi/block/ethereum/" + str(target)
    try:
        with urlopen(url, timeout=12) as f:
            n = int(json.load(f)["height"])
    except (OSError, KeyError, ValueError):
        n = 12879309 + (day - date(2021, 7, 23)).days * 6400

    def head(n):
        return fetch(ENDPOINTS["t"], "eth_getBlockByNumber", [hex(n), False])["result"]

    lo = n - 1
    hi = n
    while int(head(lo)["timestamp"], 16) >= target:
        hi = lo
        lo -= 64
    while int(head(hi)["timestamp"], 16) < target:
        lo = hi
        hi += 64
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if int(head(mid)["timestamp"], 16) < target:
            lo = mid
        else:
            hi = mid
    h1 = head(lo)
    h2 = head(hi)
    assert h2["parentHash"] == h1["hash"] and int(h1["timestamp"], 16) < target <= int(
        h2["timestamp"], 16
    )
    fields = ("hash", "parentHash", "timestamp", "number")
    dump(
        targetfile,
        {
            "height": hi,
            "seed_source": url,
            "headers": [{k: h[k] for k in fields} for h in (h1, h2)],
        },
    )
    return hi


def batch(tag, day, n, root):
    p = root / ("quotes_" + str(day) + "_" + tag + ".json.gz")
    if p.exists():
        return
    jobs = []
    for q in sizes:
        for who, to, data in [
            ("v3", Q, calldata("f7729d43", T, W, 500, q, 0)),
            ("curve", C, calldata("5e0d443f", 1, 0, q)),
        ]:
            params = [{"to": to, "data": data}, hex(n)]
            v = fetch(ENDPOINTS[tag], "eth_call", params)
            if "result" not in v:
                raise ValueError((tag, day, who, v))
            jobs.append(dict(venue=who, input_wei=q, params=params, response=v))
    dump(p, jobs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW)
    args = ap.parse_args()
    args.raw.mkdir(exist_ok=True, parents=True)
    with ThreadPoolExecutor(7) as e:
        heights = list(e.map(lambda d: boundary(d, args.raw), dates))
        list(
            e.map(
                lambda x: batch(*x, args.raw),
                [(tag, d, n) for d, n in zip(dates, heights) for tag in ("t", "d")],
            )
        )


if __name__ == "__main__":
    main()
