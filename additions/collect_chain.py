"""Read-only capture of published wallets' mined attempts and contemporaneous governance receipts."""

import sys, json, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from protocol import fetch, ENDPOINTS, dump, read, sales

FACTORY = "0x1f98431c8ad98523631ae4a59f267346ea31f984"
POOL = "0xbb6642dda99c7fb1ecf310baa3477fa7ba3e7c82"


def rpc(tag, name, method, params, out):
    path = out / (name + "_" + tag + ".json.gz")
    if not path.exists():
        rep = fetch(ENDPOINTS[tag], method, params)
        if "result" not in rep or rep["result"] is None:
            raise ValueError((tag, name, rep))
        dump(path, {"method": method, "params": params, "response": rep})
    rec = read(path)
    assert rec["params"] == params and rec["method"] == method
    return rec["response"]["result"]


def collect(out):
    jobs = []
    for l, s in zip("AB", sales()[1:]):
        addr = s["sender"]
        for n in (12789854, 12974517, 12879308, 12885654):
            for tag in ["t", "d"]:
                jobs.append(
                    (
                        tag,
                        l + "_nonce_" + str(n),
                        "eth_getTransactionCount",
                        [addr, hex(n)],
                        out,
                    )
                )
        for r in json.loads((out / ("account_" + l + ".json")).read_text())["result"]:
            if r["from"].lower() != addr:
                continue
            for tag in ["a", "d"]:
                jobs.append(
                    (
                        tag,
                        "acct_receipt_" + r["hash"],
                        "eth_getTransactionReceipt",
                        [r["hash"]],
                        out,
                    )
                )
            if r["isError"] == "1":
                jobs.append(
                    (
                        "d",
                        "failed_trace_" + r["hash"],
                        "trace_transaction",
                        [r["hash"]],
                        out,
                    )
                )
                jobs.append(
                    (
                        "t",
                        "failed_tx_" + r["hash"],
                        "eth_getTransactionByHash",
                        [r["hash"]],
                        out,
                    )
                )
    for label, sig, contract in [
        ("owner", "OwnerChanged(address,address)", FACTORY),
        ("fee", "SetFeeProtocol(uint8,uint8,uint8,uint8)", POOL),
    ]:
        topic = rpc(
            "t", "topic_" + label, "web3_sha3", ["0x" + sig.encode().hex()], out
        )
        for tag in ("t", "a"):
            logs = rpc(
                tag,
                label + "_logs",
                "eth_getLogs",
                [
                    dict(
                        address=contract,
                        topics=[topic],
                        fromBlock=hex(12369621),
                        toBlock=hex(12974517),
                    )
                ],
                out,
            )
            for e in logs:
                if int(e["blockNumber"], 16) == 12369621:
                    continue
                jobs.append(
                    (
                        tag,
                        "gov_receipt_" + e["transactionHash"],
                        "eth_getTransactionReceipt",
                        [e["transactionHash"]],
                        out,
                    )
                )
    for tag in ["t", "d"]:
        jobs.append(
            (
                tag,
                "gov_owner",
                "eth_call",
                [{"to": FACTORY, "data": "0x8da5cb5b"}, hex(12879308)],
                out,
            )
        )
    with ThreadPoolExecutor(7) as ex:
        list(ex.map(lambda j: rpc(*j), jobs))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "raw")
    collect(p.parse_args().out)
