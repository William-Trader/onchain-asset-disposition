from pathlib import Path
import csv, datetime
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent
font = fm.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update(
    {
        "font.family": font.get_name(),
        "axes.unicode_minus": False,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)
navy = "#1c4150"
teal = "#157777"
dark = "#3e4243"
red = "#923c2b"


def draw_gox():
    with (ROOT.parent / "derived/gox_market.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    fig, ax = plt.subplots(figsize=(8.1, 2.4))
    x = [int(r["offset"]) for r in rows]
    a = [float(r["gox_vs_stamp_pct"]) for r in rows]
    b = [float(r["gox_vs_finex_pct"]) for r in rows]
    ax.axhline(0, c="#777", lw=0.8)
    ax.axvline(0, c="#666", lw=0.8, ls=":")
    ax.plot(x, a, color=teal, lw=2, marker="o", ms=2.4, label="相对 Bitstamp")
    ax.plot(x, b, color=red, ls="--", lw=1.2, label="相对 Bitfinex")
    ax.set_xticks(
        [-14, -7, 0, 7, 14, 18],
        ["1/24", "1/31", "2/7\n暂停提现", "2/14", "2/21", "2/25"],
    )
    ax.set_xlabel("UTC 日期（2014 年）")
    ax.set_ylabel("场内相对价格（%）")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(ncols=2, loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(ROOT / "gox.png", dpi=235, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def mechanism():
    fig, ax = plt.subplots(figsize=(8.25, 2.05))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    boxes = [
        (0.19, 0.65, 0.22, 0.24, "客户账户所记 BTC"),
        (0.47, 0.65, 0.21, 0.24, "托管人签署出币"),
        (0.75, 0.65, 0.22, 0.24, "外部地址收币"),
        (0.19, 0.13, 0.22, 0.24, "钱包持有 sETH"),
        (0.47, 0.13, 0.21, 0.24, "0x 调用 v3 池"),
        (0.75, 0.13, 0.22, 0.24, "原钱包实收 ETH"),
    ]
    for i, (x, y, w, h, txt) in enumerate(boxes):
        edge = red if i == 1 else teal if i >= 3 else navy
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.004,rounding_size=0.015",
            ec=edge,
            fc="#fcf3ee" if i == 1 else "#f2f7f7",
            lw=1.1,
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=11, color=dark
        )
    for x, y in [(0.411, 0.77), (0.681, 0.77), (0.411, 0.25), (0.681, 0.25)]:
        ax.annotate(
            "",
            (x + 0.055, y),
            (x, y),
            arrowprops=dict(arrowstyle="->", color=navy, lw=1.15),
        )
    ax.text(0.01, 0.77, "Mt.Gox", ha="left", va="center", weight="bold", color=navy)
    ax.text(0.01, 0.25, "Uniswap v3", ha="left", va="center", weight="bold", color=navy)
    ax.text(0.575, 0.965, "暂停点", ha="center", va="center", color=red)
    ax.text(
        0.47,
        0.49,
        "官方网页入口受限；链上代理可另行调用",
        ha="center",
        color=dark,
        va="center",
        fontsize=10,
    )
    fig.savefig(ROOT / "mechanism.png", dpi=235, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


draw_gox()
mechanism()


def capacity():
    with (ROOT.parent / "derived/daily_quotes.csv").open(encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if int(r["size_wei"]) == 5 * 10**18]
    fig, ax = plt.subplots(figsize=(8.1, 1.85))
    days = [datetime.date.fromisoformat(r["day"]) for r in rows]
    y = [int(r["used_wei"]) / 1e18 for r in rows]
    ax.plot(days[:14], y[:14], color=teal, lw=1.8, marker="o", ms=2.7)
    ax.plot(days[14:], y[14:], color=teal, lw=1.8, marker="o", ms=2.7)
    ax.axhline(5, ls="--", lw=1.0, color=red)
    ax.text(days[0], 4.7, "指定卖量 5 sETH", va="top", color=red, fontsize=9)
    ax.set_ylim(0, 5.4)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("UTC 日期（2021 年）")
    ax.set_ylabel("池回调输入（sETH）")
    ticks = [days[i] for i in (0, 7, 13, 14, 21, 27)]
    ticks.pop(2)
    ax.set_xticks(ticks, [d.strftime("%m/%d") for d in ticks])
    ax.grid(axis="y", alpha=0.17)
    fig.tight_layout()
    fig.savefig(ROOT / "capacity.png", dpi=225, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


capacity()
