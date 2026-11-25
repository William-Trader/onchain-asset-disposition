"""A historical comparison of successful net settlements under an explicit fee budget, in bps."""

import argparse, csv
from pathlib import Path
from decimal import Decimal
from protocol import ROOT
from analyze import outcsv


def select(folder, limits=(50, 100, 150, 200)):
    with (folder / "counterfactuals.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    choices = []
    for sample in ("pre", "A", "B"):
        for permit_approval in (False, True):
            for cap in limits:
                pool = []
                for row in rows:
                    if row["sample"] != sample or row["success"] != "True":
                        continue
                    if not permit_approval and int(row["approval_gas"]):
                        continue
                    gross = int(row["gross_eth_wei"])
                    net = int(row["net_eth_wei"])
                    if 10000 * (gross - net) <= cap * gross:
                        pool.append((net, row["scenario"]))
                best = max(pool) if pool else (None, "none")
                choices.append(
                    dict(
                        sample=sample,
                        approval_permitted=permit_approval,
                        gas_cap_bps=cap,
                        eligible=len(pool),
                        best=best[1],
                        net_wei=best[0],
                    )
                )
    return choices


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "derived")
    p.add_argument("--cap", type=Decimal)
    opts = p.parse_args()
    if opts.cap is not None:
        if opts.cap < 0:
            p.error("cap must be nonnegative")
        for row in select(opts.out, (opts.cap,)):
            print(row)
    else:
        outcsv(opts.out, "decision", select(opts.out))
