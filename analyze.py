"""Reconcile paired provider results; produce deterministic, auditable economic measurements."""

from datetime import date, timedelta
from decimal import Decimal as D, getcontext
from statistics import median
import argparse
import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from protocol import ROOT, RAW, T, TRANSFER, Q, C, W, read, sales, tasks, word, calldata
from routes import variants
from grid import sizes, dates
from fills import delta

getcontext().prec = 70
ONE = 10**18
NATIVE = "0x" + "ee" * 20


def outcsv(root, name, rows):
    with (root / (name + ".csv")).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def event(x):
    return (
        x["address"].lower(),
        tuple(t.lower() for t in x["topics"]),
        int(x["data"], 16) if x["data"] != "0x" else "",
        x.get("blockHash"),
        x.get("transactionHash"),
        x.get("logIndex"),
    )


def pair(name, tags, raw, normalize=lambda x: x):
    a, b = (read(raw / (name + "_" + t + ".json.gz")) for t in tags)
    assert a["method"] == b["method"] and a["params"] == b["params"], name
    va, vb = (item["response"]["result"] for item in (a, b))
    assert normalize(va) == normalize(vb), name
    return va


def integer(name, raw):
    return int(pair(name, ("t", "d"), raw), 16)


def cashflow(x, who, token, destination=True):
    idx = 2 if destination else 1
    return sum(
        int(e["data"], 16)
        for e in x["logs"]
        if e["address"].lower() == token
        and e["topics"][0].lower() == TRANSFER
        and e["topics"][idx].lower() == "0x" + word(who)
    )


def representation(result):
    b = result[0]
    return (
        b["parentHash"],
        b["number"],
        [
            (
                x["status"],
                x["gasUsed"],
                x["returnData"],
                x.get("error", {}).get("data"),
                [
                    (v["address"].lower(), tuple(v["topics"]), v["data"])
                    for v in x["logs"]
                ],
            )
            for x in b["calls"]
        ],
    )


def trace_amounts(name, index, raw, params):
    records = [
        read(raw / ("fills_" + name + "_" + tag + ".json.gz"))[index]
        for tag in ("d", "a")
    ]
    for x in records:
        assert x["params"] == [params[0], ["trace"], params[1]]
    a, b = [delta(x["response"]) for x in records]
    assert a == b
    return a


def main(raw, dest):
    dest.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "evidence"
    paths = []
    history = []
    summary = {}
    bench = []
    hold = []
    summarg = []
    # Bind the per-case calldata and ledger requests to the study contract, sender and block.
    for k, m, ps in tasks():
        sample = read(raw / (k + "_t.json.gz"))
        assert (sample["params"], sample["method"]) == (ps, m), k
    for l, s in zip(("pre", "A", "B"), sales()):
        addr = s["sender"]
        sold = int(s["input_raw"])
        price = int(s["gas_price_wei"])
        out = int(s["native_eth_wei"])
        base_net = out - int(s["gas_wei"])
        for n, block, ops in variants(s):
            first = read(raw / (l + "_sim_" + n + "_d.json.gz"))
            cfg, anchor = first["params"]
            assert (
                cfg
                == {
                    "blockStateCalls": [{"calls": ops}],
                    "traceTransfers": True,
                    "validation": False,
                }
                and anchor == block
            )
            resp = pair(l + "_sim_" + n, ("d", "a"), raw, representation)[0]
            actual = json.loads(
                (
                    archive / "baseline/raw" / ("block_" + s["block"] + ".json")
                ).read_text()
            )
            assert resp["parentHash"] == actual["parentHash"] and int(
                resp["number"], 16
            ) == int(s["block"])
            calls = resp["calls"]
            assert len(calls) == len(ops)
            status = [int(x["status"], 16) for x in calls]
            success = all(status)
            assert success == (not n.endswith("_raw")), n
            gas = [int(x["gasUsed"], 16) for x in calls]
            gross = cashflow(calls[-1], addr, NATIVE)
            totalgas = sum(gas)
            if success:
                assert (
                    cashflow(calls[-1], addr, T, False) - cashflow(calls[-1], addr, T)
                    == sold
                )
                expected = integer(
                    l + ("_curve_full" if n.startswith("curve") else "_v3_full"), raw
                )
                assert gross == expected > 0
                if n == "replay":
                    assert out == gross and totalgas == int(s["gas_used"])
            else:
                assert gross == 0
            net = gross - totalgas * price if success else None
            paths.append(
                dict(
                    sample=l,
                    scenario=n,
                    success=success,
                    approval_gas=gas[0] if len(gas) > 1 else 0,
                    swap_gas=gas[-1],
                    gas_price_wei=price,
                    gross_eth_wei=gross if success else None,
                    net_eth_wei=net,
                    delta_net_vs_real_wei=net - base_net if success else None,
                )
            )
        for i, (name, mult) in enumerate(
            [
                ("small", None),
                ("half", "0.5"),
                ("full", "1"),
                ("double", "2"),
                ("ten", "10"),
            ]
        ):
            c = integer(l + "_curve_" + name, raw)
            v = integer(l + "_v3_" + name, raw)
            q = 10**14 if mult is None else int(D(sold) * D(mult))
            used, paid = trace_amounts(
                l, i, raw, read(raw / (l + "_v3_" + name + "_t.json.gz"))["params"]
            )
            assert 0 < used <= q and paid == v
            bench.append(
                dict(
                    sample=l,
                    size=name,
                    input_wei=q,
                    used_wei=used,
                    v3_output_wei=v,
                    curve_output_wei=c,
                    v3_shortfall_bps=10000 * (1 - D(v) / c) if used == q else None,
                )
            )
        assert integer(l + "_curve_coin0", raw) == int(NATIVE, 16) and integer(
            l + "_curve_coin1", raw
        ) == int(T, 16)
        allowances = {
            i: integer(l + "_allow_" + i, raw) for i in ["curve", "router", "0x"]
        }
        assert (
            not allowances["curve"]
            and not allowances["router"]
            and allowances["0x"] >= sold
        )
        margin = 10000 * (1 - D(s["minimum_wei"]) / out)
        summarg.append(
            dict(
                sample=l,
                minimum_wei=s["minimum_wei"],
                actual_wei=out,
                headroom_bps=margin,
                proxy_owner=hex(integer(l + "_proxy_owner", raw)),
                selector_implementation=hex(integer(l + "_proxy_impl", raw)),
                **{"allow_" + a: v for a, v in allowances.items()},
            )
        )
        if l == "pre":
            continue
        sets = {}
        for direction in ("in", "out"):
            ev = pair(
                l + "_history_" + direction,
                ("t", "a"),
                raw,
                lambda x: sorted(event(e) for e in x),
            )
            for e in ev:
                assert (
                    not e["removed"]
                    and e["address"].lower() == T
                    and e["topics"][2 if direction == "in" else 1] == "0x" + word(addr)
                )
                history.append(
                    dict(
                        sample=l,
                        side=direction,
                        block=int(e["blockNumber"], 16),
                        hash=e["transactionHash"],
                        log_index=int(e["logIndex"], 16),
                        amount_wei=int(e["data"], 16),
                    )
                )
            sets[direction] = ev
        first = min(
            int(z["blockNumber"], 16) for z in sets["in"] if int(z["data"], 16) > 0
        )
        h = pair(
            l + "_first_head",
            ("t", "a"),
            raw,
            lambda x: (x["hash"], x["number"], x["timestamp"]),
        )
        assert int(h["number"], 16) == first
        fields = {}
        for k, n in [
            ("pre_day", 12879308),
            ("post_start", 12885654),
            ("presale", int(s["block"]) - 1),
            ("postsale", int(s["block"])),
        ]:
            fields[k] = integer(l + "_balance_" + k, raw)
            sums = [
                sum(
                    int(z["data"], 16)
                    for z in sets[direction]
                    if int(z["blockNumber"], 16) <= n
                )
                for direction in ("in", "out")
            ]
            assert sums[0] - sums[1] == fields[k]
        between_in = sum(
            int(z["data"], 16)
            for z in sets["in"]
            if 12879308 < int(z["blockNumber"], 16) <= int(s["block"])
        )
        assert fields["presale"] - fields["postsale"] == sold
        hold.append(
            dict(
                sample=l,
                address=addr,
                first_block=first,
                first_utc=datetime.fromtimestamp(
                    int(h["timestamp"], 16), timezone.utc
                ).isoformat(),
                first_tx=min(
                    (z for z in sets["in"] if int(z["data"], 16) > 0),
                    key=lambda z: (int(z["blockNumber"], 16), int(z["logIndex"], 16)),
                )["transactionHash"],
                **fields,
                post_cutoff_in_wei=between_in,
                sold_wei=sold,
            )
        )
    outcsv(dest, "holdings", hold)
    outcsv(dest, "transfers", history)
    outcsv(dest, "counterfactuals", paths)
    outcsv(dest, "trade_quotes", bench)
    outcsv(dest, "conditions", summarg)
    mkts = {}
    for venue in ("mtgox", "bitstamp", "bitfinex"):
        with gzip.open(raw / (venue + ".csv.gz"), "rt") as f:
            mkts[venue] = {
                r["Time"][:10]: D(r["avg"]) for r in csv.DictReader(f) if r["avg"]
            }
    ohlc = {
        datetime.fromtimestamp(int(r["timestamp"]), timezone.utc).date().isoformat(): r
        for r in json.loads((raw / "bitstamp_ohlc.json").read_text())["data"]["ohlc"]
    }
    spread = []
    for n in range(-14, 19):
        day = str(date(2014, 2, 7) + timedelta(days=n))
        g, b, f = [mkts[v][day] for v in ("mtgox", "bitstamp", "bitfinex")]
        assert min(g, b, f) > 0 and D(ohlc[day]["low"]) <= b <= D(ohlc[day]["high"])
        spread.append(
            dict(
                date=day,
                offset=n,
                gox_usd=g,
                bitstamp_usd=b,
                bitfinex_usd=f,
                gox_vs_stamp_pct=100 * (g / b - 1),
                gox_vs_finex_pct=100 * (g / f - 1),
            )
        )
    outcsv(dest, "gox_market", spread)
    summary["spreads"] = {}
    for start, end in [
        (-14, -1),
        (1, 14),
        (1, 7),
        (8, 14),
        (0, 0),
        (11, 11),
        (17, 17),
        (18, 18),
    ]:
        subset = [r for r in spread if start <= r["offset"] <= end]
        summary["spreads"][f"{start}..{end}"] = {
            k: str(median([r[k] for r in subset]))
            for k in ("gox_vs_stamp_pct", "gox_vs_finex_pct")
        }
    summary["elapsed_days"] = (date(2024, 7, 5) - date(2014, 2, 7)).days
    tokens = json.loads((archive / "baseline/raw/list_2021.json").read_text())["tokens"]
    from collections import Counter

    groups = Counter(
        "Synth prefix"
        if t["name"].startswith("Synth ")
        else "Call or Put"
        if any(z in t["name"].lower() for z in (" call ", " put "))
        else "Mirrored or M prefix"
        if t["name"].startswith(("Mirrored ", "M "))
        else "Other names"
        for t in tokens
        if t["chainId"] == 1
    )
    summary["list_name_groups"] = dict(groups)
    grid = []
    for day in dates:
        h = read(raw / ("utc_" + str(day) + ".json.gz"))
        lo, hi = h["headers"]
        stamp = int(
            datetime.combine(day, datetime.min.time(), timezone.utc).timestamp()
        )
        assert (
            int(lo["timestamp"], 16) < stamp <= int(hi["timestamp"], 16)
            and lo["hash"] == hi["parentHash"]
            and int(hi["number"], 16) == h["height"] == int(lo["number"], 16) + 1
        )
        left, right = (
            read(raw / ("quotes_" + str(day) + "_" + tag + ".json.gz"))
            for tag in ("t", "d")
        )
        assert len(left) == len(right) == len(sizes) * 2
        for j, q in enumerate(sizes):
            vals = []
            for i, (venue, to, data) in enumerate(
                [
                    ("v3", Q, calldata("f7729d43", T, W, 500, q, 0)),
                    ("curve", C, calldata("5e0d443f", 1, 0, q)),
                ]
            ):
                a, b = left[2 * j + i], right[2 * j + i]
                assert (
                    a["venue"] == b["venue"] == venue
                    and a["input_wei"] == b["input_wei"] == q
                    and a["params"]
                    == b["params"]
                    == [{"to": to, "data": data}, hex(h["height"])]
                )
                v = int(a["response"]["result"], 16)
                assert v == int(b["response"]["result"], 16) > 0
                vals.append(v)
            v, c = vals
            used, paid = trace_amounts(str(day), j, raw, left[2 * j]["params"])
            assert 0 < used <= q and paid == v
            grid.append(
                dict(
                    day=str(day),
                    block=h["height"],
                    size_wei=q,
                    used_wei=used,
                    v3_wei=v,
                    curve_wei=c,
                    curve_adv_bps=10000 * (1 - D(v) / c) if used == q else None,
                )
            )
    outcsv(dest, "daily_quotes", grid)
    summary["grid"] = {}
    for q in sizes:
        rows = [r for r in grid if r["size_wei"] == q]
        full = [r for r in rows if r["used_wei"] == q]
        summary["grid"][str(q)] = {
            "full": len(full),
            "partial": len(rows) - len(full),
            "min_used": str(min(r["used_wei"] for r in rows)),
            "max_used": str(max(r["used_wei"] for r in rows)),
            "curve_higher": sum(r["curve_wei"] > r["v3_wei"] for r in full),
            "median_bps": str(median(r["curve_adv_bps"] for r in full))
            if full
            else None,
            "n": len(rows),
            "pre_curve_higher": sum(
                r["curve_wei"] > r["v3_wei"] for r in full if r["day"] < "2021-07-23"
            ),
            "post_curve_higher": sum(
                r["curve_wei"] > r["v3_wei"] for r in full if r["day"] > "2021-07-23"
            ),
        }

    (dest / "summary.json").write_bytes(
        (json.dumps(summary, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--out", type=Path, default=ROOT / "derived")
    args = ap.parse_args()
    main(args.raw, args.out)
