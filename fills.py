"""Verify how much input the v3 pool would consume, via the amounts in the Quoter callback."""

import time
import argparse
from pathlib import Path
from protocol import RAW, Q, ENDPOINTS, fetch, read, dump
from grid import dates
from concurrent.futures import ThreadPoolExecutor

POOL = "0xbb6642dda99c7fb1ecf310baa3477fa7ba3e7c82"


def delta(resp):
    tr = resp["result"]["trace"]
    fl = [
        x["action"]
        for x in tr
        if x["action"].get("input", "").startswith("0xfa461e33")
        and x["action"].get("from", "").lower() == POOL
        and x["action"].get("to", "").lower() == Q
    ]
    assert len(fl) == 1
    data = fl[0]["input"][10:]
    debit = int(data[:64], 16)
    credit = 2**256 - int(data[64:128], 16)
    assert (
        0 < debit < 2**255
        and 0 < credit < 2**255
        and int(resp["result"]["output"], 16) == credit
    )
    return debit, credit


def batch(day, params, tag, root):
    p = root / ("fills_" + str(day) + "_" + tag + ".json.gz")
    if p.exists():
        return
    records = []
    for item in params:
        cp, address = item["params"]
        request = [cp, ["trace"], address]
        response = None
        for attempt in range(6):
            try:
                response = fetch(ENDPOINTS[tag], "trace_call", request)
                delta(response)
                break
            except (OSError, KeyError, ValueError):
                if attempt == 5:
                    raise
                time.sleep(2 + 2 * attempt)
        records.append(dict(params=request, response=response))
    dump(p, records)


def source_requests(raw):
    for day in dates:
        yield (
            str(day),
            [
                r
                for r in read(raw / ("quotes_" + str(day) + "_t.json.gz"))
                if r["venue"] == "v3"
            ],
        )
    for l in ("pre", "A", "B"):
        yield (
            l,
            [
                read(raw / (l + "_v3_" + k + "_t.json.gz"))
                for k in ("small", "half", "full", "double", "ten")
            ],
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW)
    args = ap.parse_args()
    with ThreadPoolExecutor(3) as ex:
        list(
            ex.map(
                lambda p: batch(*p, args.raw),
                [(d, r, t) for d, r in source_requests(args.raw) for t in ("a", "d")],
            )
        )
