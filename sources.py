"""Freeze comparative daily prices and the specific public primary-source artifacts used in the paper."""

import argparse, gzip
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from protocol import RAW

git = "https://raw.githubusercontent.com/"
front = git + "Uniswap/interface/4078390a4890445d1ff0ed5196fd4cb56a44de87/"
zero = (
    git
    + "0xProject/protocol/b46eeadc64485288add5940a210e1a7d0bcb5481/contracts/zero-ex/contracts/src/"
)
URLS = {
    name
    + ".csv.gz": "https://data.bitcoinity.org/export_data.csv?c=e&data_type=price&r=day&t=l&timespan=all&currency=USD&exchange="
    + name
    for name in ["mtgox", "bitstamp", "bitfinex"]
}
URLS.update(
    {
        "swap_page.tsx": front + "src/pages/Swap/index.tsx",
        "tokens_hooks.ts": front + "src/hooks/Tokens.ts",
        "unsupported_footer.tsx": front
        + "src/components/swap/UnsupportedCurrencyFooter.tsx",
        "feature.sol": zero + "features/UniswapV3Feature.sol",
        "registry.sol": zero + "features/SimpleFunctionRegistryFeature.sol",
        "ownership.sol": zero + "features/OwnableFeature.sol",
        "court2019.pdf": "https://www.govinfo.gov/content/pkg/USCOURTS-ilnd-1_14-cv-01437/pdf/USCOURTS-ilnd-1_14-cv-01437-4.pdf",
        "curve_pool.vy": "https://raw.githubusercontent.com/curvefi/curve-contract/master/contracts/pools/seth/StableSwapSETH.vy",
        "router.sol": git + "Uniswap/v3-periphery/v1.0.0/contracts/SwapRouter.sol",
        "router_pay.sol": git
        + "Uniswap/v3-periphery/v1.0.0/contracts/base/PeripheryPayments.sol",
    }
)
URLS.update(
    {
        "trustee2024.pdf": "https://www.mtgox.com/img/pdf/20240705_01_announcement_en.pdf",
        "bitstamp_ohlc.json": "https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=45&end=1393372800",
        "useIsSwapUnsupported.ts": front + "src/hooks/useIsSwapUnsupported.ts",
    }
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW)
    args = ap.parse_args()
    args.raw.mkdir(exist_ok=True, parents=True)

    def get(kv):
        k, url = kv
        try:
            with urlopen(
                Request(url, headers={"User-Agent": "research/1.0"}), timeout=30
            ) as f:
                b = f.read()
            p = args.raw / k
            if k.endswith(".gz"):
                b = gzip.compress(b, mtime=0)
            p.write_bytes(b)
            print(k, len(b), flush=True)
        except OSError as e:
            raise RuntimeError(f"Could not freeze {k} from {url}") from e

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(get, URLS.items()))


if __name__ == "__main__":
    main()
