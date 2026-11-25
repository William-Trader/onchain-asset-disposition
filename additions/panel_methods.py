#!/usr/bin/env python3
"""Historical multi-venue AMM cohort, with two hosted log providers."""

import argparse
import gzip
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "raw"
RPCS = {
    "a": "https://gateway.tenderly.co/public/mainnet",
    "b": "https://eth-mainnet.g.alchemy.com/v2/demo/",
    "t": "https://eth.drpc.org",
    "x": "https://eth-mainnet.public.blastapi.io",
    "c": "https://cloudflare-eth.com",
    "m": "https://rpc.mevblocker.io",
}
P2 = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"
P3 = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
S2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
S3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
FACTORIES = {
    "v2": ("0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f", P2, S2),
    "v3": ("0x1f98431c8ad98523631ae4a59f267346ea31f984", P3, S3),
    "sushi": ("0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2ac", P2, S2),
}
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
UST = "0xa47c8bf37f92abed4a126bda807a7b7498661acd"
STABLES = {
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("USDC", 6),
    "0xdac17f958d2ee523a2206206994597c13d831ec7": ("USDT", 6),
    "0x6b175474e89094c44da98b954eedeac495271d0f": ("DAI", 18),
    UST: ("UST", 18),
    WETH: ("WETH", 18),
}
EVENT = datetime(2021, 7, 23, tzinfo=timezone.utc)
DAYS = [
    "2021-06-23",
    "2021-07-09",
    "2021-07-16",
    "2021-07-23",
    "2021-07-24",
    "2021-07-31",
    "2021-08-07",
    "2021-08-23",
]
SEGMENTS = (
    ("pre_outer", 0, 1),
    ("pre_mid", 1, 2),
    ("pre_inner", 2, 3),
    ("event", 3, 4),
    ("post_inner", 4, 5),
    ("post_mid", 5, 6),
    ("post_outer", 6, 7),
)
ROUTES = {
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x",
    "0x11111112542d85b3ef69ae05771c2dccff4faa26": "1inch",
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch",
    "0x111111125434b319222cdbf8c261674adb56f3ae": "1inch",
    "0xdef171fe48cf0115b1d80b88dc8eab59176fee57": "ParaSwap",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap router",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap router",
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap router",
    "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "Sushi router",
}
AGG = {"0x", "1inch", "ParaSwap"}


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as out, gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as f:
        f.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode())
    tmp.replace(path)


def read_json(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def cached(root, key, fn):
    path = root / (key + ".json.gz")
    if not path.exists():
        write_json(path, fn())
    return read_json(path)


def require(p, msg):
    if not p:
        raise ValueError(msg)


def call(label, method, params, keep_error=False):
    x = bulk(label, [(method, params)], keep_error)[0]
    return x


def bulk(label, methods, keep_error=False, attempts=6):
    import time
    from urllib.error import HTTPError

    chunk = int(
        os.getenv("JOURNAL_BATCH_" + label.upper(), "3" if label == "t" else "8")
    )
    if len(methods) > chunk:
        return [
            x
            for i in range(0, len(methods), chunk)
            for x in bulk(label, methods[i : i + chunk], keep_error, attempts)
        ]
    url = os.getenv("JOURNAL_RPC_" + label.upper(), RPCS[label])
    request = [
        dict(jsonrpc="2.0", id=i + 1, method=m, params=p)
        for i, (m, p) in enumerate(methods)
    ]
    blob = request[0] if len(request) == 1 else request
    for trial in range(attempts):
        try:
            q = Request(
                url,
                data=json.dumps(blob).encode(),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ReadOnlyAssetResearch/2.0",
                },
            )
            try:
                with urlopen(q, timeout=55) as o:
                    value = json.load(o)
            except HTTPError as err:
                if not keep_error or err.code not in (400, 500):
                    raise
                value = json.load(err)
                observed = value if isinstance(value, list) else [value]
                if not all(
                    "revert" in str(x.get("error", {})).lower() for x in observed
                ):
                    raise
            if isinstance(value, dict):
                if len(request) > 1:
                    raise ValueError(str(value)[:400])
                value = [value]
            ix = {v["id"]: v for v in value}
            rows = [ix[r["id"]] for r in request]
            if keep_error:
                return [{"request": r, "response": v} for r, v in zip(request, rows)]
            if any("error" in v or v.get("result") is None for v in rows):
                raise ValueError(
                    str(
                        [v for v in rows if "error" in v or v.get("result") is None][:1]
                    )[:500]
                )
            return [v["result"] for v in rows]
        except Exception as ex:
            if getattr(ex, "code", None) == 429 and len(methods) > 1 and trial >= 1:
                m = len(methods) // 2
                return bulk(label, methods[:m], keep_error, attempts) + bulk(
                    label, methods[m:], keep_error, attempts
                )
            if trial == attempts - 1:
                raise
            time.sleep(1 + 2 * trial)
    raise RuntimeError("request not completed")


def number(v):
    return int(v, 16)


def words(d):
    return [int(d[i : i + 64], 16) for i in range(2, len(d), 64)]


def signed(w):
    return w - (1 << 256) if w >= 1 << 255 else w


def address(x):
    return "0x" + x[-40:].lower()


def stamp(x):
    return datetime.fromtimestamp(number(x), timezone.utc)


def bsearch(day):
    goal = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    start, end = 12650000, 13200000
    while end - start > 1:
        mid = (start + end) // 2
        h = call("t", "eth_getBlockByNumber", [hex(mid), False])
        if stamp(h["timestamp"]) < goal:
            start = mid
        else:
            end = mid
    return bulk("t", [("eth_getBlockByNumber", [hex(n), False]) for n in (start, end)])


def bind(root, label):
    prior, at = read_json(root / f"bound_{label}.json.gz")
    goal = datetime.fromisoformat(label).replace(tzinfo=timezone.utc)
    require(
        stamp(prior["timestamp"]) < goal <= stamp(at["timestamp"])
        and at["parentHash"] == prior["hash"]
        and number(prior["number"]) + 1 == number(at["number"]),
        "bad UTC boundary " + label,
    )
    return number(at["number"])


def logs(label, contract, topics, lo, hi):
    try:
        return call(
            label,
            "eth_getLogs",
            [dict(address=contract, topics=topics, fromBlock=hex(lo), toBlock=hex(hi))],
        )
    except Exception:
        if hi - lo < 250:
            raise
        mid = (lo + hi) // 2
        return logs(label, contract, topics, lo, mid) + logs(
            label, contract, topics, mid + 1, hi
        )


def snap(root):
    listed = {
        x["address"].lower(): x
        for x in json.loads((root / "list_2021.json").read_text())["tokens"]
        if x["chainId"] == 1
    }
    mirror = {
        a.lower(): d
        for a, d in json.loads((root / "mirror_20210712.json").read_text()).items()
        if d["symbol"].startswith("m") and d.get("pool") and d["status"] == "LISTED"
    }
    require(len(listed) == 129 and len(mirror) > 0, "wrong pinned list")
    return listed, mirror


def logkey(x):
    return (
        x["blockHash"],
        x["transactionHash"],
        number(x["logIndex"]),
        x["address"].lower(),
        tuple(x["topics"]),
        x["data"],
    )


def match_sources(root, key):
    a, b = (read_json(root / (key + "_" + which + ".json.gz")) for which in "ab")
    require(
        len(a) == len(b)
        and len({logkey(x) for x in a}) == len(a)
        and {logkey(x) for x in a} == {logkey(x) for x in b}
        and not any(x.get("removed") for x in a + b),
        "two-provider coverage differs at " + key,
    )
    am = {logkey(x): x["blockTimestamp"] for x in a if "blockTimestamp" in x}
    require(
        all(x["blockTimestamp"] == am.get(logkey(x), x["blockTimestamp"]) for x in b),
        "timestamp mismatch at " + key,
    )
    return b


def inventory(root, listed, mirror):
    pools = {}
    for venue, (fac, topic, _) in FACTORIES.items():
        for side in (0, 1):
            for e in match_sources(root, f"factory_{venue}_{side}"):
                require(
                    e["address"].lower() == fac and e["topics"][0] == topic,
                    "bad pool source",
                )
                t0, t1 = map(address, e["topics"][1:3])
                require(
                    t0 in listed or t1 in listed or t0 in mirror or t1 in mirror,
                    "wrong pool topics",
                )
                w = words(e["data"])
                pool = "0x" + f"{w[1] if venue == 'v3' else w[0]:040x}"
                record = {
                    "pool": pool,
                    "venue": venue,
                    "token0": t0,
                    "token1": t1,
                    "fee_millionths": number(e["topics"][3]) if venue == "v3" else 3000,
                    "block": number(e["blockNumber"]),
                    "created_utc": stamp(e["blockTimestamp"]).isoformat(),
                    "hash": e["transactionHash"],
                }
                require(
                    pool not in pools or pools[pool] == record,
                    "multiple records for pool",
                )
                pools[pool] = record
    return dict(sorted(pools.items()))


def log_tasks(pools, bs):
    for name, i, j in SEGMENTS:
        for venue, (_, _, topic) in FACTORIES.items():
            addrs = [
                a
                for a, p in pools.items()
                if p["venue"] == venue and p["block"] < bs[j]
            ]
            for k in range(0, len(addrs), 18):
                yield (
                    f"swap_{venue}_{name}_{k}",
                    addrs[k : k + 18],
                    topic,
                    bs[i],
                    bs[j] - 1,
                )


def swap_logs(root, pools, bs):
    all_swaps = []
    for key, addrs, topic, a, b in log_tasks(pools, bs):
        es = match_sources(root, key)
        require(
            all(
                e["address"].lower() in addrs
                and e["topics"][0] == topic
                and a <= number(e["blockNumber"]) <= b
                for e in es
            ),
            "swap outside query",
        )
        all_swaps.extend(es)
    return sorted(
        all_swaps, key=lambda x: (number(x["blockNumber"]), number(x["logIndex"]))
    )


def digest_receipt(x):
    return {
        k: x[k]
        for k in (
            "blockHash",
            "blockNumber",
            "transactionHash",
            "from",
            "to",
            "status",
            "gasUsed",
            "effectiveGasPrice",
        )
    } | {"logs": [logkey(e) for e in x["logs"]]}


def collect(root, workers, receipts=True):
    listed, mirror = snap(root)
    with ThreadPoolExecutor(max_workers=workers) as p:
        # Frozen blocks and every receipt are checked against the dual-source mainnet log hashes.
        # Historical mirror endpoints may not expose eth_chainId on free tiers.
        list(p.map(lambda d: cached(root, "bound_" + d, lambda: bsearch(d)), DAYS))
        bs = [bind(root, d) for d in DAYS]
        print("boundaries", dict(zip(DAYS, bs)), flush=True)
        topic_addresses = [
            "0x" + a[2:].zfill(64) for a in sorted(listed.keys() | mirror.keys())
        ]

        def lookup(task):
            venue, side, label = task
            fac, ptopic, _ = FACTORIES[venue]
            qs = [ptopic] + ([None] if side else []) + [topic_addresses]
            cached(
                root,
                f"factory_{venue}_{side}_{label}",
                lambda: logs(label, fac, qs, 9_000_000, bs[-1] - 1),
            )

        list(
            p.map(lookup, [(v, s, l) for v in FACTORIES for s in (0, 1) for l in "ab"])
        )
        pools = inventory(root, listed, mirror)
        print(
            "pools all and by protocol",
            len(pools),
            Counter(x["venue"] for x in pools.values()),
            flush=True,
        )

        def query(chunk):
            key, addr, topic, a, b, l = chunk
            cached(root, f"{key}_{l}", lambda: logs(l, addr, [topic], a, b))

        list(p.map(query, [(*q, l) for q in log_tasks(pools, bs) for l in "ab"]))
        ss = swap_logs(root, pools, bs)
        txs = sorted({x["transactionHash"] for x in ss})
        print("swap logs/unique tx", len(ss), len(txs), flush=True)
        if not receipts:
            return
        jobs = [(i, txs[i : i + 24]) for i in range(0, len(txs), 24)]

        def receipts_batch(q):
            i, ids = q
            provider_names = "axtcm"
            existing = {
                l: read_json(root / f"receipt_{i}_{l}.json.gz")
                for l in provider_names
                if (root / f"receipt_{i}_{l}.json.gz").exists()
            }
            # All observed logs were matched across two providers. Receipt details require
            # a complete primary source and retain corroborating responses where available.
            if not existing:
                methods = [("eth_getTransactionReceipt", [h]) for h in ids]
                errors = []
                priority = (
                    provider_names[(i // 24) % len(provider_names) :]
                    + provider_names[: (i // 24) % len(provider_names)]
                )
                for label in priority:
                    try:
                        cached(
                            root,
                            f"receipt_{i}_{label}",
                            lambda: bulk(label, methods, attempts=2),
                        )
                        break
                    except Exception as e:
                        errors.append((label, type(e).__name__, str(e)[:115]))
                else:
                    print("failed receipt batch", i, errors, flush=True)
                    return False
            return True

        status = list(p.map(receipts_batch, jobs))
        print("complete primary receipt batches", sum(status), len(jobs), flush=True)
        require(
            all(status), "receipt batches incomplete; resume after provider cool-down"
        )


def transaction_index(root, swaps):
    tids = sorted({x["transactionHash"] for x in swaps})
    result = {}
    for i in range(0, len(tids), 24):
        data = [
            read_json(root / f"receipt_{i}_{l}.json.gz")
            for l in "axtcm"
            if (root / f"receipt_{i}_{l}.json.gz").exists()
        ]
        require(
            data and all(len(s) == len(tids[i : i + 24]) for s in data),
            "receipt batch incomplete",
        )
        for index, h in enumerate(tids[i : i + 24]):
            r = data[0][index]
            require(
                r["transactionHash"] == h and r["status"] == "0x1",
                "receipt mismatch " + h,
            )
            require(
                all(digest_receipt(r) == digest_receipt(s[index]) for s in data[1:]),
                "corroborating receipt mismatch " + h,
            )
            result[h] = r
    for x in swaps:
        h = result[x["transactionHash"]]
        require(
            x["blockHash"] == h["blockHash"]
            and number(h["blockNumber"]) == number(x["blockNumber"])
            and logkey(x) in map(logkey, h["logs"]),
            "event/receipt mismatch " + x["transactionHash"],
        )
    return result


def unpack(e, p, h, router):
    w = words(e["data"])
    if p["venue"] == "v3":
        d0, d1 = signed(w[0]), signed(w[1])
        a0i, a1i, a0o, a1o = max(0, d0), max(0, d1), max(0, -d0), max(0, -d1)
    else:
        a0i, a1i, a0o, a1o = w
    t = stamp(e["blockTimestamp"])
    return {
        "hash": e["transactionHash"],
        "idx": number(e["logIndex"]),
        "block": number(e["blockNumber"]),
        "utc": t.isoformat(),
        "event_day": (t.date() - EVENT.date()).days,
        "pool": p["pool"],
        "venue": p["venue"],
        "token0": p["token0"],
        "token1": p["token1"],
        "amount0_in": a0i,
        "amount0_out": a0o,
        "amount1_in": a1i,
        "amount1_out": a1o,
        "sender": h["from"],
        "destination": h["to"],
        "path_type": router,
        "gas_wei": number(h["gasUsed"]) * number(h["effectiveGasPrice"]),
    }


def csv_out(path, rows):
    import csv

    if rows:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def export(root, out):
    out.mkdir(parents=True, exist_ok=True)
    listed, mirror = snap(root)
    bs = [bind(root, d) for d in DAYS]
    pools = inventory(root, listed, mirror)
    logs_all = swap_logs(root, pools, bs)
    txs = transaction_index(root, logs_all)
    records = []
    for e in logs_all:
        h = txs[e["transactionHash"]]
        where = (h["to"] or "").lower()
        router = ROUTES.get(
            where, "direct pool" if where in pools else "other/unidentified"
        )
        records.append(unpack(e, pools[e["address"].lower()], h, router))
    csv_out(out / "pools.csv", list(pools.values()))
    csv_out(out / "swaps.csv", records)
    print("export", len(pools), len(records), len(txs), flush=True)
    return bs, pools, records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=ROOT / "derived")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--only-logs", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.collect:
        collect(args.raw, args.workers, not args.only_logs)
    if not args.only_logs:
        export(args.raw, args.out)
