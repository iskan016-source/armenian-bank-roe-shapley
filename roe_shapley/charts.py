"""Figures written to results/figures/."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import components as c  # noqa: E402
from . import config  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
PEER = "#c9c8c2"
HIGHLIGHT = "#eb6834"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # categorical slots 1-4
YEAR_STEPS = {2024: "#9cc3ef", 2025: "#2a78d6"}       # one hue, light -> dark

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": INK_2,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK,
    "text.color": INK,
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _save(fig, name):
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES_DIR / name
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def shapley_shares(jk):
    """Grouped bars of 6-component Shapley shares with jackknife ranges."""
    years = sorted(jk.index.get_level_values(0).unique())
    order = (jk["share_pct"].groupby(level=1).mean().sort_values().index)
    y = np.arange(len(order))
    h = 0.36

    fig, ax = plt.subplots(figsize=(8, 5.2))
    for i, year in enumerate(years):
        d = jk.loc[year].reindex(order)
        pos = y + (i - 0.5) * h * 1.08
        ax.barh(pos, d["share_pct"], height=h, color=YEAR_STEPS[year], label=str(year), zorder=2)
        ax.hlines(pos, d["jackknife_min"], d["jackknife_max"], color=INK_2, lw=1, zorder=3)
        for p, v, hi in zip(pos, d["share_pct"], d["jackknife_max"]):
            ax.text(max(v, hi) + 0.8, p, f"{v:.1f}%", va="center", fontsize=8.5, color=INK_2)

    ax.set_yticks(y, [c.LABELS[o] for o in order])
    ax.set_xlabel("Share of explained cross-bank variance in pre-tax ROE (%)")
    ax.set_xlim(0, 45)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, loc="lower right", title="Year", title_fontsize=9)
    ax.set_title("What explains ROE differences across Armenian banks?",
                 loc="left", fontsize=12, fontweight="bold", pad=22)
    ax.text(0, 1.02, "Shapley (LMG) decomposition of R², 16 banks, IFRS fee & trading data. "
            "Lines show leave-one-bank-out range.", transform=ax.transAxes,
            fontsize=8.5, color=INK_2)
    return _save(fig, "shapley_shares_2024_2025.png")


def four_component_trend(shares, jk):
    """Line chart of 4-component Shapley shares, 2022-2025."""
    years = [int(y) for y in shares.columns]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for color, comp in zip(SERIES, c.FOUR):
        vals = shares.loc[comp].to_numpy(dtype=float)
        ax.plot(years, vals, color=color, lw=2, marker="o", ms=7,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)

    # Direct end labels, nudged apart so close values don't collide
    ends = sorted((float(shares.loc[comp, years[-1]]), comp) for comp in c.FOUR)
    min_gap, placed = 4.5, []
    for v, comp in ends:
        y = max(v, placed[-1] + min_gap) if placed else v
        placed.append(y)
        ax.text(years[-1] + 0.08, y, f"{c.LABELS[comp].split(' (')[0]}  {v:.0f}%",
                color=INK, va="center", fontsize=9)

    nim22 = jk.loc[(2022, "NIM")]
    ax.annotate(f"Unstable: jackknife range\n{nim22.jackknife_min:.0f}–{nim22.jackknife_max:.0f}%",
                xy=(2022, shares.loc["NIM", 2022]), xytext=(2022.25, 72),
                fontsize=8, color=INK_2, arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
    ax.set_xticks(years, [str(y) for y in years])
    ax.set_xlim(years[0] - 0.2, years[-1] + 0.95)
    ax.set_ylim(0, 80)
    ax.set_ylabel("Shapley share (%)")
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_title("The dominant ROE driver shifts over time", loc="left",
                 fontsize=12, fontweight="bold", pad=22)
    ax.text(0, 1.02, "4-component model (NIM, CIR, provisioning, leverage), 17 banks, OctoBI data",
            transform=ax.transAxes, fontsize=8.5, color=INK_2)
    return _save(fig, "shapley_trend_2022_2025.png")


def peer_positioning(df, year, bank="AMIO", estimated=("VTB",)):
    """One panel per component, banks sorted best-to-worst, `bank` highlighted."""
    panels = c.SIX
    fig, axes = plt.subplots(2, 3, figsize=(15, 10.5))
    for ax, comp in zip(axes.flat, panels):
        better_high = c.HIGHER_IS_BETTER[comp]
        s = df[comp].sort_values(ascending=better_high)  # best ends up on top
        is_ratio = comp == "Leverage"
        vals = s.to_numpy() * (1 if is_ratio else 100)
        names = [f"{b}*" if b in estimated and comp in ("fee_yield", "trading_yield") else b
                 for b in s.index]
        colors = [HIGHLIGHT if b == bank else PEER for b in s.index]
        ax.barh(names, vals, color=colors, height=0.72, zorder=2)

        med = np.median(vals)
        ax.axvline(med, color=INK_2, lw=1, ls=(0, (4, 3)), zorder=3)
        ax.text(med, len(s) - 0.3, f" median {med:.1f}{'x' if is_ratio else '%'}",
                fontsize=8, color=INK_2, va="bottom")

        i = list(s.index).index(bank)
        rank = len(s) - i
        unit = "x" if is_ratio else "%"
        ax.text(vals[i], i, f"  {vals[i]:.2f}{unit}", va="center", fontsize=8.5,
                color=INK, fontweight="bold", zorder=4)
        arrow = "higher is better" if better_high else "lower is better"
        ax.set_title(f"{c.LABELS[comp]}  ({arrow})\n{bank}: #{rank} of {len(s)}",
                     loc="left", fontsize=10, fontweight="bold")
        ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
        ax.tick_params(axis="y", length=0, labelsize=8.5)
        for lbl in ax.get_yticklabels():
            if lbl.get_text() == bank:
                lbl.set_fontweight("bold")
        ax.set_xlabel("IEA / equity (x)" if is_ratio else "% of interest-earning assets"
                      if comp != "CIR" else "% of operating income", fontsize=8.5)

    fig.suptitle(f"{bank} vs. the Armenian banking sector, {year}", x=0.01, ha="left",
                 fontsize=14, fontweight="bold")
    fig.text(0.01, 0.005, "* Fee and trading yields estimated from the ROE identity "
             "(no public IFRS report). Sources: OctoBI, bank IFRS annual reports.",
             fontsize=8.5, color=INK_2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    return _save(fig, f"peer_positioning_{bank}_{year}.png")
