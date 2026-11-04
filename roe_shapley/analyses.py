"""Each analysis returns DataFrames and writes them to results/tables/."""

from itertools import combinations
from math import factorial

import numpy as np
import pandas as pd

from . import components as c
from . import config
from .data import load_ifrs_fees, load_octobi_panel, load_paper_table_a1
from .shapley import jackknife, r_squared, shapley_r2


def _save(df: pd.DataFrame, name: str) -> pd.DataFrame:
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df.round(4).to_csv(config.TABLES_DIR / f"{name}.csv")
    return df


def _shares_table(results: dict) -> pd.DataFrame:
    """{year: (shares, r2, n)} -> components x years, plus R^2 and n rows."""
    table = pd.DataFrame({y: s for y, (s, _, _) in results.items()})
    table.loc["model_R2_pct"] = [100 * r2 for _, r2, _ in results.values()]
    table.loc["n_banks"] = [n for _, _, n in results.values()]
    return table


# --------------------------------------------------------------------------
# Datasets
# --------------------------------------------------------------------------

def ifrs_dataset(year: int, panel=None, ifrs=None) -> pd.DataFrame:
    """Primary 6-component data: OctoBI ratios + hand-collected IFRS fee/trading income.

    Only banks with an IFRS record are kept (VTB has no public IFRS report).
    """
    panel = load_octobi_panel() if panel is None else panel
    ifrs = load_ifrs_fees() if ifrs is None else ifrs
    comp = c.add_ifrs_fees(c.octobi_components(panel, year), ifrs, year)
    return c.model_table(comp, c.SIX)


def peer_dataset(year: int) -> pd.DataFrame:
    """All banks for peer positioning: IFRS fee/trading where available,
    back-calculated from reported ROE otherwise (VTB)."""
    panel, ifrs = load_octobi_panel(), load_ifrs_fees()
    share = c.fee_share(ifrs["fee_yield"], ifrs["trading_yield"])
    comp = c.add_ifrs_fees(c.octobi_components(panel, year), ifrs, year)
    comp = c.add_backcalc_fees(comp, share, only_missing=True)
    return c.model_table(comp, c.SIX)


# --------------------------------------------------------------------------
# 1. Replication of Melik-Parsadanyan (2026), Table A1, 2023
# --------------------------------------------------------------------------

def replicate_paper() -> dict:
    a1 = load_paper_table_a1().set_index("bank")
    df = pd.DataFrame({
        "NIM": a1["NIM"],
        "fee_yield": a1["fee_yield"],
        "trading_yield": a1["trading_yield"],
        "CIR": a1["CIR"],
        "Provisioning": a1["provision_rate"],
        "Leverage": a1["AE"],
    })
    df["pretax_roe"] = c.pretax_roe(df)
    # Identity check: Eq. 4 with each bank's own effective tax rate vs reported ROE
    identity_gap_pp = 100 * (df["pretax_roe"] * (1 - a1["tax_rate"]) - a1["roe_reported"])

    shares, r2 = shapley_r2(df, c.SIX)
    table = _shares_table({2023: (shares, r2, len(df))})
    _save(table, "01_paper_replication_2023")
    return {"shares": table, "max_identity_gap_pp": float(identity_gap_pp.abs().max())}


# --------------------------------------------------------------------------
# 2. Primary model: 6 components with IFRS fee/trading data, 2024-2025
# --------------------------------------------------------------------------

def six_component_ifrs() -> dict:
    panel, ifrs = load_octobi_panel(), load_ifrs_fees()
    results, robustness = {}, []
    for year in config.IFRS_YEARS:
        df = ifrs_dataset(year, panel, ifrs)
        shares, r2 = shapley_r2(df, c.SIX)
        results[year] = (shares, r2, len(df))
        jk = jackknife(df, c.SIX)
        robustness.append(jk.assign(year=year).set_index("year", append=True))
    table = _save(_shares_table(results), "02_shapley_6comp_ifrs_2024_2025")
    jk = _save(pd.concat(robustness).swaplevel().sort_index(), "02_jackknife_6comp_ifrs")
    return {"shares": table, "jackknife": jk}


# --------------------------------------------------------------------------
# 3. Four-component trend, 2022-2025 (OctoBI only)
# --------------------------------------------------------------------------

def four_component_trend() -> dict:
    """NIM, CIR, Provisioning, Leverage for all four years.

    Fee and trading income are not in OctoBI for 2022-23, so the target here is
    the 4-component reduced form Leverage * [NIM * (1 - CIR) - gamma], not the
    banks' full reported ROE.
    """
    panel = load_octobi_panel()
    results, robustness = {}, []
    for year in config.YEARS:
        df = c.model_table(c.octobi_components(panel, year), c.FOUR)
        shares, r2 = shapley_r2(df, c.FOUR)
        results[year] = (shares, r2, len(df))
        robustness.append(jackknife(df, c.FOUR).assign(year=year).set_index("year", append=True))
    table = _save(_shares_table(results), "03_shapley_4comp_2022_2025")
    jk = _save(pd.concat(robustness).swaplevel().sort_index(), "03_jackknife_4comp")
    return {"shares": table, "jackknife": jk}


# --------------------------------------------------------------------------
# 4. Does Eq. 4 reproduce reported ROE?
# --------------------------------------------------------------------------

def reconcile_roe() -> dict:
    """Compare Eq. 4 (t = 18%) to reported ROE for the IFRS banks.

    The residual is mostly bank-specific effective tax rates; the implied rate
    is the t that would close the gap exactly.
    """
    panel, ifrs = load_octobi_panel(), load_ifrs_fees()
    frames, summary = [], {}
    for year in config.IFRS_YEARS:
        df = ifrs_dataset(year, panel, ifrs)
        calc = df["pretax_roe"] * (1 - config.TAX_RATE)
        out = pd.DataFrame({
            "year": year,
            "reported_roe_pct": 100 * df["ROE"],
            "eq4_roe_pct": 100 * calc,
            "gap_pp": 100 * (calc - df["ROE"]),
            "implied_tax_rate_pct": 100 * (1 - df["ROE"] / df["pretax_roe"]),
        })
        frames.append(out)
        summary[year] = {
            "n_banks": len(out),
            "mean_abs_gap_pp": out["gap_pp"].abs().mean(),
            "median_abs_gap_pp": out["gap_pp"].abs().median(),
            "max_abs_gap_pp": out["gap_pp"].abs().max(),
        }
    detail = _save(pd.concat(frames).set_index("year", append=True).swaplevel().sort_index(),
                   "04_roe_reconciliation")
    summary = _save(pd.DataFrame(summary), "04_roe_reconciliation_summary")
    return {"detail": detail, "summary": summary}


# --------------------------------------------------------------------------
# 5. Why the paper's R^2 (10 banks) is not comparable to ours (16 banks)
# --------------------------------------------------------------------------

def r2_vs_sample_size(year: int = 2024, trials: int = 500, seed: int = 42) -> dict:
    df = ifrs_dataset(year)
    rng = np.random.default_rng(seed)
    y, X = df["pretax_roe"].to_numpy(), df[c.SIX].to_numpy()
    rows = {}
    for n in range(len(df), len(c.SIX) + 1, -1):
        r2s = [r_squared(X[idx], y[idx])
               for idx in (rng.choice(len(df), n, replace=False) for _ in range(trials))]
        rows[n] = {"residual_df": n - len(c.SIX) - 1, "mean_R2_pct": 100 * np.mean(r2s),
                   "min_R2_pct": 100 * np.min(r2s), "max_R2_pct": 100 * np.max(r2s)}
    table = pd.DataFrame(rows).T.rename_axis("n_banks")
    return {"table": _save(table, "05_r2_vs_sample_size")}


# --------------------------------------------------------------------------
# 6. Peer positioning of one bank
# --------------------------------------------------------------------------

def peer_ranks(bank: str = "AMIO") -> dict:
    """Rank `bank` on each component (1 = best), and attribute its year-on-year
    change in pre-tax ROE to components (Shapley over the 6 component changes)."""
    rows = {}
    data = {y: peer_dataset(y) for y in config.IFRS_YEARS}
    for year, df in data.items():
        for comp in c.SIX + ["ROE"]:
            ranks = df[comp].rank(ascending=not c.HIGHER_IS_BETTER[comp], method="min")
            rows[(year, comp)] = {
                "value": df.at[bank, comp],
                "sector_median": df[comp].median(),
                "rank_1_is_best": int(ranks[bank]),
                "n_banks": len(df),
            }
    ranks = pd.DataFrame(rows).T.rename_axis(["year", "component"])
    ranks = _save(ranks.astype({"rank_1_is_best": int, "n_banks": int}), f"06_peer_ranks_{bank}")

    # Exact Shapley attribution of the change in pre-tax ROE between the two years:
    # average over all orders of switching components from year-1 to year-2 values.
    y1, y2 = config.IFRS_YEARS
    a, b = data[y1].loc[bank, c.SIX], data[y2].loc[bank, c.SIX]
    n = len(c.SIX)

    def roe_with(switched):
        mix = a.copy()
        mix[list(switched)] = b[list(switched)]
        return float(c.pretax_roe(mix.to_frame().T).iloc[0])

    contrib = {}
    for comp in c.SIX:
        others = [o for o in c.SIX if o != comp]
        contrib[comp] = sum(
            factorial(k) * factorial(n - k - 1) / factorial(n)
            * (roe_with(s + (comp,)) - roe_with(s))
            for k in range(n) for s in combinations(others, k)
        )
    change = pd.Series(contrib, name="contribution_pp") * 100
    change.loc["total_change_pp"] = 100 * (roe_with(c.SIX) - roe_with(()))
    _save(change.to_frame(), f"06_pretax_roe_change_{bank}_{y1}_{y2}")
    return {"ranks": ranks, "roe_change": change}
