"""Recover full address denominators, mined attempts, sensitivity statistics and trustee bounds."""

import argparse, csv, gzip, json, re, sys
from pathlib import Path
from collections import Counter
from decimal import Decimal as D
from datetime import date, timedelta, datetime
from statistics import median
from hashlib import sha256
import panel_methods as pm

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
PANEL = ROOT / "panel"
sys.path.insert(0, str(ROOT.parent))
from protocol import read, sales, T


def rows(file):
    with (
        gzip.open(file, "rt", encoding="utf-8-sig")
        if str(file).endswith("gz")
        else file.open(encoding="utf-8-sig")
    ) as f:
        return list(csv.DictReader(f))


def write(out, name, data):
    with (out / (name + ".csv")).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)


def raw(name, tag):
    return read(RAW / f"{name}_{tag}.json.gz")["response"]["result"]


def cohort(out):
    root = PANEL
    listed, mirror = pm.snap(root)
    bs = [pm.bind(root, d) for d in pm.DAYS]
    pools = pm.inventory(root, listed, mirror)
    logs = pm.swap_logs(root, pools, bs)
    assert all(
        int(e["blockNumber"], 16) >= pools[e["address"].lower()]["block"] for e in logs
    )
    matched = {
        a: p for a, p in pools.items() if {p["token0"], p["token1"]} & listed.keys()
    }
    write(out, "listed_pools", list(matched.values()))
    market_events = []
    for e in logs:
        addr = e["address"].lower()
        if addr not in matched:
            continue
        pool = matched[addr]
        w = pm.words(e["data"])
        if pool["venue"] == "v3":
            dx, dy = map(pm.signed, w[:2])
        else:
            dx, dy = w[0] - w[2], w[1] - w[3]
        market_events.append(
            dict(
                venue=pool["venue"],
                pool=addr,
                block=int(e["blockNumber"], 16),
                block_hash=e["blockHash"],
                tx=e["transactionHash"],
                log_index=int(e["logIndex"], 16),
                token0=pool["token0"],
                token1=pool["token1"],
                net_token0_into_pool=dx,
                net_token1_into_pool=dy,
            )
        )
    write(out, "listed_swaps", market_events)
    per = []
    summary = []
    for name, i, j in [
        ("pre7", 2, 3),
        ("post7", 4, 5),
        ("pre14", 1, 3),
        ("post14", 4, 6),
        ("event", 3, 4),
        ("pre30", 0, 3),
        ("post30", 4, 7),
        ("full61", 0, 7),
    ]:
        lo, stop = bs[i], bs[j]
        for v in ["v3", "three_venues"]:
            inventory = {
                k: p
                for k, p in pools.items()
                if (v == "three_venues" or p["venue"] == v)
                and p["block"] < stop
                and ({p["token0"], p["token1"]} & listed.keys())
            }
            hit = [
                e
                for e in logs
                if e["address"].lower() in inventory
                and lo <= int(e["blockNumber"], 16) < stop
            ]
            group = []
            for addr, asset in listed.items():
                eligible = {
                    x
                    for x, p in inventory.items()
                    if addr in (p["token0"], p["token1"])
                }
                observed = [e for e in hit if e["address"].lower() in eligible]
                r = dict(
                    window=name,
                    scope=v,
                    first_block=lo,
                    last_block=stop - 1,
                    token=addr,
                    symbol=asset["symbol"],
                    pools=len(eligible),
                    swap_logs=len(observed),
                    unique_txs=len({e["transactionHash"] for e in observed}),
                    category="no_pool"
                    if not eligible
                    else "pool_zero"
                    if not observed
                    else "positive",
                )
                group.append(r)
            counts = Counter(r["category"] for r in group)
            assert (
                len(group) == len(set(x["token"] for x in group)) == 129
                and sum(counts.values()) == 129
            )
            summary.append(
                dict(
                    window=name,
                    scope=v,
                    first_block=lo,
                    last_block=stop - 1,
                    addresses=len(group),
                    no_pool=counts["no_pool"],
                    pool_zero=counts["pool_zero"],
                    positive=counts["positive"],
                    zero_logs=counts["no_pool"] + counts["pool_zero"],
                    pools=len(inventory),
                    logs=len(hit),
                    txs=len({e["transactionHash"] for e in hit}),
                )
            )
            per.extend(group)
    write(out, "address_by_window", per)
    write(out, "window_totals", summary)
    write(
        out,
        "restricted_addresses",
        [
            dict(address=a, symbol=v["symbol"], name=v["name"], chainId=v["chainId"])
            for a, v in listed.items()
        ],
    )


def markets(out):
    def daily(fname, col):
        return {
            date.fromisoformat(i["Time"][:10]): D(i[col]) for i in rows(fname) if i[col]
        }

    m = {
        v: daily(ROOT.parent / "raw" / f"{v}.csv.gz", "avg")
        for v in ["mtgox", "bitfinex", "bitstamp"]
    }
    for v in ("btce", "kraken"):
        m[v] = daily(RAW / f"{v}_USD_price.csv.gz", "avg")
    vol = {
        v: daily(RAW / f"{v}_USD_volume.csv.gz", "")
        for v in ("mtgox", "bitstamp", "bitfinex")
    }
    eur = daily(RAW / "mtgox_EUR_price.csv.gz", "avg")
    fx = {
        date.fromisoformat(r["TIME_PERIOD"]): D(r["OBS_VALUE"])
        for r in rows(RAW / "fx_usd_eur.csv")
    }
    obs = []
    event = date(2014, 2, 7)
    for t in range(-17, 18):
        d = event + timedelta(days=t)
        v = {k: rates[d] for k, rates in m.items() if d in rates}
        assert len(v) == 5 and min(v.values()) > 0
        base = median(v[x] for x in ("bitstamp", "bitfinex", "btce", "kraken"))
        s = 100 * (v["mtgox"] / base - 1)
        mfx = fx.get(d)
        basket = 100 * (eur[d] * mfx / base - 1) if mfx else None
        obs.append(
            dict(
                offset=t,
                utc=d,
                **v,
                basket=base,
                volume_btc=vol["mtgox"][d],
                bitstamp_vol=vol["bitstamp"][d],
                bitfinex_vol=vol["bitfinex"][d],
                eur_btc_price=eur[d],
                usd_per_eur=mfx,
                basket_pct=s,
                bitstamp_pct=100 * (v["mtgox"] / v["bitstamp"] - 1),
                bitfinex_pct=100 * (v["mtgox"] / v["bitfinex"] - 1),
                btce_pct=100 * (v["mtgox"] / v["btce"] - 1),
                kraken_pct=100 * (v["mtgox"] / v["kraken"] - 1),
                fx_basis_pct=100 * (v["mtgox"] / (eur[d] * mfx) - 1) if mfx else None,
                eur_converted_spread=basket,
            )
        )
    write(out, "market_by_day", obs)
    res = []
    for n in [3, 7, 14, 17]:
        for side in [-1, 1]:
            r = [i for i in obs if 0 < i["offset"] * side <= n]
            valid = [i for i in r if i["usd_per_eur"] is not None]
            assert len(r) == n and all(i["volume_btc"] > 0 for i in r)
            weight = sum(i["volume_btc"] for i in r)
            res.append(
                dict(
                    window=n,
                    side="pre" if side == -1 else "post",
                    days=len(r),
                    basket_median=median(i["basket_pct"] for i in r),
                    basket_weighted=sum(i["basket_pct"] * i["volume_btc"] for i in r)
                    / weight,
                    bitstamp_weighted=sum(
                        i["bitstamp_pct"] * i["volume_btc"] for i in r
                    )
                    / weight,
                    bitstamp_median=median(i["bitstamp_pct"] for i in r),
                    bitfinex_median=median(i["bitfinex_pct"] for i in r),
                    btce_median=median(i["btce_pct"] for i in r),
                    kraken_median=median(i["kraken_pct"] for i in r),
                    fx_days=len(valid),
                    fx_basis_median=median(i["fx_basis_pct"] for i in valid),
                    fx_matched_usd_median=median(i["basket_pct"] for i in valid),
                    eur_converted_median=median(
                        i["eur_converted_spread"] for i in valid
                    ),
                )
            )
    write(out, "market_sensitivity", res)


def transactions(out):
    rec = []
    summary = []
    for key, s in zip("AB", sales()[1:]):
        a = s["sender"]
        info = json.loads((RAW / f"account_{key}.json").read_text())["result"]
        entries = sorted(
            [r for r in info if r["from"].lower() == a], key=lambda r: int(r["nonce"])
        )
        nons = []
        for n in (12789854, 12879308, 12885654, 12974517):
            v = [int(raw(key + "_nonce_" + str(n), t), 16) for t in ["d", "t"]]
            assert v[0] == v[1]
            nons.append(v[0])
        assert [int(r["nonce"]) for r in entries] == list(range(nons[0], nons[-1]))
        group = []
        for r in entries:
            h = r["hash"]
            v1, v2 = [raw("acct_receipt_" + h, t) for t in "ad"]
            fields = (
                "transactionHash",
                "blockHash",
                "blockNumber",
                "status",
                "gasUsed",
                "from",
                "to",
            )
            assert (
                all(v1[k] == v2[k] for k in fields)
                and v2["blockHash"] == r["blockHash"]
                and v2["transactionHash"] == h
                and v1["from"].lower() == a
            )
            status = int(v2["status"], 16)
            assert status == int(r["txreceipt_status"]) == 1 - int(r["isError"])
            block = int(r["blockNumber"])
            period = (
                "pre" if block < 12879309 else "post" if block >= 12885655 else "event"
            )
            outcome = "other"
            tx = r["input"].lower()
            if h == s["hash"]:
                outcome = "strict_sETH_closed"
            if not status:
                tr = raw("failed_trace_" + h, "d")
                tx2 = raw("failed_tx_" + h, "t")
                assert tx2["input"].lower() == tx and tx2["hash"] == h
                assert (
                    tr[0]["error"]
                    and not tx.startswith("0x803ba26d")
                    and all(n.get("action", {}).get("to", "").lower() != T for n in tr)
                )
                outcome = "reverted_other_operation"
            group.append(
                dict(
                    sample=key,
                    period=period,
                    hash=h,
                    nonce=r["nonce"],
                    block=block,
                    to=r["to"],
                    selector=tx[:10],
                    status=status,
                    outcome=outcome,
                )
            )
        for period, low, high in zip(("pre", "event", "post"), nons, nons[1:]):
            sub = [r for r in group if r["period"] == period]
            assert len(sub) == high - low
            summary.append(
                dict(
                    sample=key,
                    period=period,
                    nonce_start=low,
                    nonce_end=high,
                    mined=len(sub),
                    reverted=sum(not i["status"] for i in sub),
                    strict=sum(i["outcome"] == "strict_sETH_closed" for i in sub),
                )
            )
        rec += group
    write(out, "wallet_mined_txs", rec)
    write(out, "wallet_counts", summary)


def trustee(out):
    latest = date(2014, 2, 7)
    events = []
    for day in ("20240705", "20240716", "20240724", "20240731", "20240821", "20250327"):
        d = datetime.strptime(day, "%Y%m%d").date()
        if day == "20240705":
            t = (RAW / "trustee_20240705.txt").read_text()
            assert re.search(r"some of the rehabilitation creditors", t, re.I | re.S)
            lower = 1
            phrase = "some"
        else:
            t = (RAW / f"trustee_{day}.txt").read_text()
            m = re.search(r"over\s+([\d,]+)\s+rehabilitation creditors", t, re.I)
            assert m
            lower = int(m.group(1).replace(",", "")) + 1
            phrase = m.group(0)
        events.append(
            dict(
                date=d,
                days_from_halt=(d - latest).days,
                confirmed_integer_lower_bound=lower,
                source_text=phrase,
            )
        )
    write(out, "payment_bounds", events)
    t = (RAW / "plan_en.txt").read_text()
    assert (
        "200,000 yen or (b) the Allowed Cryptocurrency" in t
        and "Repayment Rate of (1) above is 21%" in t
    )
    rates = []
    for C in (100000, 200000, 500000, 1000000, 10000000):
        small = min(C, 200000)
        early = D(".21") * (C - small)
        rates.append(
            dict(
                claim_base_yen=C,
                small_yen=small,
                early_yen=early,
                model_total_yen=small + early,
                model_rate_pct=100 * (small + early) / C,
            )
        )
    write(out, "schedule_rates", rates)


def governance(out):
    all_logs = [raw("owner_logs", t) for t in ("t", "a")]
    comps = lambda a: [(r["transactionHash"], r["topics"], r["blockHash"]) for r in a]
    assert comps(all_logs[0]) == comps(all_logs[1])
    log = all_logs[0][-1]
    h = log["transactionHash"]
    for t in ("t", "a"):
        r = raw("gov_receipt_" + h, t)
        assert (
            int(r["status"], 16) == 1
            and log["blockHash"] == r["blockHash"]
            and any(
                x["topics"] == log["topics"] and x["address"] == log["address"]
                for x in r["logs"]
            )
        )
    owner = log["topics"][-1][-40:]
    assert all(raw("gov_owner", t)[-40:] == owner for t in ("t", "d"))
    assert raw("fee_logs", "t") == raw("fee_logs", "a") == []
    write(
        out,
        "governance",
        [
            dict(
                block=int(log["blockNumber"], 16),
                hash=h,
                owner="0x" + owner,
                pool_fee_protocol_events=0,
                through_block=12974517,
            )
        ],
    )


def forum(out):
    meta = json.loads((RAW / "forum_evidence.json").read_text())
    blob = (RAW / "forum_topic.json").read_bytes()
    assert sha256(blob).hexdigest() == meta["download_sha256"]
    source = json.loads(blob)
    index = {p["post_number"]: p for p in source["post_stream"]["posts"]}
    rows = []
    for item in meta["posts"]:
        post = index[item["post_number"]]
        assert (
            post["created_at"] == item["time_utc"]
            and post["username"] == item["username"]
            and item["excerpt"] in post["cooked"]
        )
        rows.append(item)
    write(out, "forum_posts", rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "derived")
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--panel", type=Path, default=PANEL)
    args = parser.parse_args()
    RAW, PANEL = args.raw, args.panel
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    for fun in (cohort, markets, transactions, trustee, governance, forum):
        fun(out)
