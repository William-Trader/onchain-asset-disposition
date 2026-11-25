"""Counterfactual quote-to-payment test. All requests are simulation-only."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
from protocol import ROOT, RAW, T, W, R, C, X, calldata, word, sales, save_rpc


def multicall(parts):
    chunks = [word(len(x) // 2) + x.ljust((len(x) + 63) // 64 * 64, "0") for x in parts]
    offsets = []
    n = len(parts) * 32
    for chunk in chunks:
        offsets.append(word(n))
        n += len(chunk) // 2
    return calldata("ac9650d8", 32, len(parts)) + "".join(offsets + chunks)


def variants(s):
    sender = s["sender"]
    q = int(s["input_raw"])
    lim = int(s["minimum_wei"])
    b = hex(int(s["block"]) - 1)
    base = ROOT / "evidence/baseline/raw"
    tx = (
        json.loads((base / ("tx_" + s["hash"] + ".json")).read_text())
        if (base / ("tx_" + s["hash"] + ".json")).exists()
        else json.loads((base / ("transaction_" + s["hash"] + ".json")).read_text())
    )

    def msg(to, data):
        return {
            "from": sender,
            "to": to,
            "gas": hex(1600000),
            "gasPrice": tx["gasPrice"],
            "data": data,
            "value": "0x0",
        }

    official = msg(
        R,
        multicall(
            [
                calldata(
                    "414bf389",
                    T,
                    W,
                    500,
                    R,
                    int(datetime.fromisoformat(s["utc"]).timestamp()) + 600,
                    q,
                    lim,
                    0,
                )[2:],
                calldata("49404b7c", lim, sender)[2:],
            ]
        ),
    )
    curve = msg(C, calldata("3df02124", 1, 0, q, lim))
    original = msg(X, tx["input"])
    for name, ops in [
        ("replay", [original]),
        ("router_raw", [official]),
        ("router_approved", [msg(T, calldata("095ea7b3", R, q)), official]),
        ("curve_raw", [curve]),
        ("curve_approved", [msg(T, calldata("095ea7b3", C, q)), curve]),
    ]:
        yield name, b, ops


def collect(args):
    jobs = []
    for k, s in zip(("pre", "A", "B"), sales()):
        for n, b, ops in variants(s):
            for tag in ("d", "a"):
                p = [
                    {
                        "blockStateCalls": [{"calls": ops}],
                        "traceTransfers": True,
                        "validation": False,
                    },
                    b,
                ]
                jobs.append((tag, k + "_sim_" + n, "eth_simulateV1", p, args.raw))
    with ThreadPoolExecutor(6) as ex:
        for job, v in zip(jobs, ex.map(lambda a: save_rpc(*a), jobs)):
            print(
                job[0:2],
                v.get("error")
                or [
                    (x.get("status"), x.get("gasUsed"), x.get("error"))
                    for x in v["result"][0]["calls"]
                ],
                flush=True,
            )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW)
    collect(ap.parse_args())
