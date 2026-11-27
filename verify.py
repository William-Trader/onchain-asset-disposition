"""Offline entry point. Rebuild frozen outputs and fail if any byte differs."""

import hashlib, subprocess, sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent


def run(script, *args):
    subprocess.run([sys.executable, str(ROOT / script), *map(str, args)], check=True)


def compare(left, right):
    a = {p.relative_to(left): p.read_bytes() for p in left.rglob("*") if p.is_file()}
    b = {p.relative_to(right): p.read_bytes() for p in right.rglob("*") if p.is_file()}
    if a != b:
        raise ValueError(
            "Output mismatch: "
            + str([str(k) for k in a.keys() | b.keys() if a.get(k) != b.get(k)])
        )


def verify():
    if not __debug__:
        raise RuntimeError("Run Python with assertions enabled (omit -O).")
    manifest = ROOT / "SHA256SUMS.txt"
    if manifest.is_file():
        for line in manifest.read_text().splitlines():
            digest, name = line.split("  ", 1)
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError(name)
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        run("evidence/reproduce_all.py", "--out", tmp / "base")
        compare(ROOT / "evidence/derived", tmp / "base")
        run("analyze.py", "--out", tmp / "new")
        run("decision.py", "--out", tmp / "new")
        compare(ROOT / "derived", tmp / "new")
        run("audit.py")
        run("additions/recalculate.py", "--out", tmp / "expanded")
        compare(ROOT / "additions/derived", tmp / "expanded")
        run("final_review/wallet_probe.py", "--out", tmp / "final")
        run("final_review/review_metrics.py", "--out", tmp / "final")
        run("final_review/settlement.py", "--input", tmp / "final/wallet_inventory_probe.csv", "--out", tmp / "final")
        compare(ROOT / "final_review/derived", tmp / "final")
    print(
        "Offline reproduction passed; historical and new output directories match byte for byte."
    )


if __name__ == "__main__":
    verify()
