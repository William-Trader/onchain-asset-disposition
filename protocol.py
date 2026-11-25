"""Read-only paired historical RPC requests. Each file binds parameters to a full JSON-RPC response."""

import csv, gzip, json, os, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
T = "0x5e74c9036fb86bd7ecdcb084a0673efc32ea31cb"
W = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
R = "0xe592427a0aece92de3edee1f18e0157c05861564"
X = "0xdef1c0ded9bec7f1a1670819833240f027b25eff"
C = "0xc5424b857f758e906013f3555dad202e4bdb4567"
Q = "0xb27308f9f90d607463bb33ea1bebb41c27ce5ab6"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ENDPOINTS = {
    "t": os.getenv("TENDERLY_RPC", "https://gateway.tenderly.co/public/mainnet"),
    "d": os.getenv("DRPC_RPC", "https://eth.drpc.org"),
}
ENDPOINTS["a"] = os.getenv("ALCHEMY_RPC", "https://eth-mainnet.g.alchemy.com/v2/demo/")


def word(n):
    return (n.removeprefix("0x") if isinstance(n, str) else hex(n)[2:]).zfill(64)


def calldata(sel, *args):
    return "0x" + sel + "".join(map(word, args))


def dump(p, o):
    p.parent.mkdir(exist_ok=True, parents=True)
    with (
        p.open("wb") as f,
        gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as g,
    ):
        g.write(json.dumps(o, separators=(",", ":")).encode())


def read(p):
    with gzip.open(p, "rt") as f:
        return json.load(f)


def fetch(url, m, ps):
    data = {"id": 1, "jsonrpc": "2.0", "method": m, "params": ps}
    for i in range(4):
        try:
            with urlopen(
                Request(
                    url,
                    json.dumps(data).encode(),
                    {
                        "Content-Type": "application/json",
                        "User-Agent": "research-client/1.0",
                    },
                ),
                timeout=45,
            ) as f:
                return json.load(f)
        except OSError:
            if i == 3:
                raise
            time.sleep(1 + i)


def save_rpc(tag, key, m, ps, root=RAW):
    p = root / (key + "_" + tag + ".json.gz")
    if p.exists():
        a = read(p)
        assert a["params"] == ps and a["method"] == m
    else:
        a = {
            "method": m,
            "params": ps,
            "rpc": tag,
            "response": fetch(ENDPOINTS[tag], m, ps),
        }
        dump(p, a)
    return a["response"]


def sales():
    with (ROOT / "evidence/derived/strict_native_0x.csv").open(
        encoding="utf-8-sig"
    ) as f:
        return list(csv.DictReader(f))


def tasks():
    for label, s in zip(["pre", "A", "B"], sales()):
        w = s["sender"]
        h = int(s["block"])
        q = int(s["input_raw"])
        b = hex(h - 1)

        def call(k, to, input, block=b):
            return (label + "_" + k, "eth_call", [{"to": to, "data": input}, block])

        for k, n in [
            ("pre_day", 12879308),
            ("post_start", 12885654),
            ("presale", h - 1),
            ("postsale", h),
        ]:
            yield call("balance_" + k, T, calldata("70a08231", w), hex(n))
        yield call("proxy_owner", X, "0x8da5cb5b")
        yield call("proxy_impl", X, "0x972fdd26" + "803ba26d".ljust(64, "0"))
        for name, who in [("curve", C), ("router", R), ("0x", X)]:
            yield call("allow_" + name, T, calldata("dd62ed3e", w, who))
        for k, amount in [
            ("small", 10**14),
            ("full", q),
            ("half", q // 2),
            ("double", 2 * q),
            ("ten", 10 * q),
        ]:
            yield call("curve_" + k, C, calldata("5e0d443f", 1, 0, amount))
            yield call("v3_" + k, Q, calldata("f7729d43", T, W, 500, amount, 0))
        for i in (0, 1):
            yield call("curve_coin" + str(i), C, calldata("c6610657", i))
        if label == "pre":
            continue
        for side in ("in", "out"):
            filt = (
                [TRANSFER, None, "0x" + word(w)]
                if side == "in"
                else [TRANSFER, "0x" + word(w)]
            )
            yield (
                label + "_history_" + side,
                "eth_getLogs",
                [{"address": T, "fromBlock": "0x0", "toBlock": hex(h), "topics": filt}],
            )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW)
    args = ap.parse_args()
    with ThreadPoolExecutor(10) as ex:
        fs = {
            ex.submit(save_rpc, tag, k, m, ps, args.raw): (tag, k)
            for k, m, ps in tasks()
            for tag in (("t", "a") if m == "eth_getLogs" else ("t", "d"))
        }
        for f in as_completed(fs):
            v = f.result()
            if "error" in v:
                print(fs[f], v["error"], flush=True)
    for label in ("A", "B"):
        js = read(args.raw / (label + "_history_in_t.json.gz"))["response"]
        if "result" not in js or not js["result"]:
            continue
        n = min(
            int(x["blockNumber"], 16) for x in js["result"] if int(x["data"], 16) > 0
        )
        for tag in ("t", "a"):
            save_rpc(
                tag,
                label + "_first_head",
                "eth_getBlockByNumber",
                [hex(n), False],
                args.raw,
            )


if __name__ == "__main__":
    main()
