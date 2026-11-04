"""The ROE accounting identity and the per-bank component tables.

Melik-Parsadanyan (2026), Eq. 4:

    ROE = [(NIM + f + x) * (1 - CIR) - gamma] * (A/E) * (1 - t)

    NIM    net interest margin                      (on interest-earning assets, IEA)
    f      net fee & commission income / IEA
    x      net trading & FX income / IEA
    CIR    cost-to-income ratio
    gamma  net loan-impairment charge / IEA         ("Provisioning")
    A/E    IEA / equity                             ("Leverage")
    t      effective tax rate

All decompositions use pre-tax ROE (the identity without the (1 - t) term),
so that differences in tax position do not show up as operating performance.
"""

import pandas as pd

from . import config

SIX = ["NIM", "fee_yield", "trading_yield", "CIR", "Provisioning", "Leverage"]
FOUR = ["NIM", "CIR", "Provisioning", "Leverage"]

LABELS = {
    "NIM": "Net interest margin",
    "fee_yield": "Fee yield",
    "trading_yield": "Trading & FX yield",
    "CIR": "Cost-to-income",
    "Provisioning": "Provisioning",
    "Leverage": "Leverage (IEA/Equity)",
}

# For peer rankings: is a higher value better for the bank?
HIGHER_IS_BETTER = {
    "NIM": True,
    "fee_yield": True,
    "trading_yield": True,
    "CIR": False,
    "Provisioning": False,
    "Leverage": True,
    "ROE": True,
}


def pretax_roe(df: pd.DataFrame) -> pd.Series:
    """Eq. 4 without the tax term. Missing f / x are treated as zero."""
    income = df["NIM"] + df.get("fee_yield", 0.0) + df.get("trading_yield", 0.0)
    return df["Leverage"] * (income * (1 - df["CIR"]) - df["Provisioning"])


def implied_non_interest_yield(df: pd.DataFrame, tax_rate: float = config.TAX_RATE) -> pd.Series:
    """Solve Eq. 4 for f + x given reported (after-tax) ROE:

        f + x = [ROE / (1 - t) / (A/E) + gamma] / (1 - CIR) - NIM
    """
    pretax = df["ROE"] / (1 - tax_rate)
    return (pretax / df["Leverage"] + df["Provisioning"]) / (1 - df["CIR"]) - df["NIM"]


def fee_share(fee: pd.Series, trading: pd.Series, positive_only: bool = True) -> float:
    """Average fee share of non-interest income across banks."""
    total = fee + trading
    mask = total > 0 if positive_only else total.notna()
    return float((fee[mask] / total[mask]).mean())


def octobi_components(panel: pd.DataFrame, year: int) -> pd.DataFrame:
    """NIM, CIR, Provisioning, Leverage and reported ROE for one year, indexed by bank."""
    p = panel[panel["year"] == year].set_index("bank")
    out = pd.DataFrame(index=p.index)
    out["NIM"] = p["nim"]
    out["CIR"] = p["cir"]
    # OctoBI's credit cost ratio is on a loan basis; rescale to the IEA basis.
    out["Provisioning"] = p["ccr"] * p["net_loans_to_assets"] / p["iea_to_assets"]
    # A/E in the paper is IEA / equity.
    out["Leverage"] = p["assets_to_equity"] * p["iea_to_assets"]
    out["ROE"] = p["roe"]
    out["iea_to_assets"] = p["iea_to_assets"]
    return out


def add_ifrs_fees(comp: pd.DataFrame, ifrs: pd.DataFrame, year: int) -> pd.DataFrame:
    """Attach hand-collected IFRS fee and trading yields (converted to an IEA basis).

    Banks without an IFRS record get NaN.
    """
    y = ifrs[ifrs["year"] == year].set_index("bank")
    out = comp.copy()
    for col in ("fee_yield", "trading_yield"):
        out[col] = y[col].reindex(out.index) / out["iea_to_assets"]
    out["fee_source"] = out["fee_yield"].notna().map({True: "IFRS", False: None})
    return out


def add_backcalc_fees(comp: pd.DataFrame, share: float, only_missing: bool = False) -> pd.DataFrame:
    """Recover f + x from reported ROE via Eq. 4, then split with a fixed fee share."""
    out = comp.copy()
    non_interest = implied_non_interest_yield(out)
    mask = out["fee_yield"].isna() if only_missing and "fee_yield" in out else slice(None)
    out.loc[mask, "fee_yield"] = non_interest[mask] * share
    out.loc[mask, "trading_yield"] = non_interest[mask] * (1 - share)
    if "fee_source" not in out:
        out["fee_source"] = None
    out.loc[mask, "fee_source"] = "back-calculated"
    return out


def model_table(comp: pd.DataFrame, players) -> pd.DataFrame:
    """Keep the model inputs and add the pre-tax ROE target."""
    out = comp.dropna(subset=list(players)).copy()
    out["pretax_roe"] = pretax_roe(out[list(players)])
    return out
