"""Alternative raw-field audit of the central conclusions, without using the main analyzer."""

import csv, gzip, json, sqlite3, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"


def record(name):
    with gzip.open(RAW / name, "rt") as f:
        return json.load(f)


def check():
    db = sqlite3.connect(":memory:")
    db.execute(
        "create table market (venue text, day text, px real, primary key(venue,day))"
    )
    for name in ("mtgox", "bitstamp", "bitfinex"):
        with gzip.open(RAW / (name + ".csv.gz"), "rt") as f:
            for row in csv.DictReader(f):
                if "2014-01-24" <= row["Time"][:10] <= "2014-02-25":
                    db.execute(
                        "insert into market values(?,?,?)",
                        (name, row["Time"][:10], float(row["avg"])),
                    )
    for comparator in ("bitstamp", "bitfinex"):
        for lo, hi, expected in [
            ("2014-01-24", "2014-02-06", 17.29),
            (
                "2014-02-08",
                "2014-02-21",
                -39.63 if comparator == "bitstamp" else -39.60,
            ),
        ]:
            values = list(
                db.execute(
                    "select 100*(g.px/r.px-1) from market g join market r using(day) where g.venue='mtgox' and r.venue=? and g.day between ? and ?",
                    (comparator, lo, hi),
                )
            )
            assert (
                len(values) == 14
                and round(statistics.median(x[0] for x in values), 2) == expected
            )
    eligible = []
    for label in ("A", "B"):
        b = int(record(label + "_balance_pre_day_d.json.gz")["response"]["result"], 16)
        h = record(label + "_history_in_a.json.gz")["response"]["result"]
        sale = record(label + "_sim_replay_a.json.gz")["response"]["result"][0][
            "calls"
        ][0]
        payer = record(label + "_sim_replay_a.json.gz")["params"][0]["blockStateCalls"][
            0
        ]["calls"][0]["from"]
        txnet = {}
        for style in ("replay", "router_approved", "curve_approved"):
            raw = record(label + "_sim_" + style + "_a.json.gz")
            calls = raw["response"]["result"][0]["calls"]
            rates = [
                int(c["gasPrice"], 16)
                for c in raw["params"][0]["blockStateCalls"][0]["calls"]
            ]
            assert all(x["status"] == "0x1" for x in calls)
            netgas = sum(int(c["gasUsed"], 16) * r for c, r in zip(calls, rates))
            final = [
                int(log["data"], 16)
                for log in calls[-1]["logs"]
                if log["address"].lower() == "0x" + "ee" * 20
                and log["topics"][-1][-40:] == payer[2:]
            ]
            assert len(final) == 1
            txnet[style] = final[0] - netgas
        assert txnet["curve_approved"] > txnet["replay"] > txnet["router_approved"]
        input_wei = int(
            record(label + "_v3_full_d.json.gz")["params"][0]["data"][
                10 + 3 * 64 : 10 + 4 * 64
            ],
            16,
        )
        new = sum(int(x["data"], 16) for x in h if int(x["blockNumber"], 16) > 12879308)
        eligible.append(b >= input_wei and new == 0)
    assert eligible == [False, True]
    cases = partial = 0
    for p in RAW.glob("fills_2021*_a.json.gz"):
        records = record(p.name)
        for entry in records:
            q = int(entry["params"][0]["data"][10 + 3 * 64 : 10 + 4 * 64], 16)
            calls = [
                c["action"]["input"]
                for c in entry["response"]["result"]["trace"]
                if c["action"].get("input", "").startswith("0xfa461e33")
            ]
            assert len(calls) == 1
            used = int(calls[0][10:74], 16)
            assert 0 < used <= q
            if used < q:
                partial += 1
                assert q == 5 * 10**18
            cases += 1
    assert (cases, partial) == (112, 28)
    print(
        "Independent arithmetic and raw-field checks passed: 4 market medians; A/B holdings; 2 paired route rankings; 112 input traces, 28 partial."
    )


if __name__ == "__main__":
    check()
