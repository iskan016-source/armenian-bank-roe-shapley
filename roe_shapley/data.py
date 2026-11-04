"""Loading the three input datasets.

* OctoBI ratios: NIM, CIR, credit cost, leverage inputs and reported ROE for
  every Armenian bank at year-end. The raw platform export is long-format
  (one row per bank x ratio x date x ratio type); ``build_octobi_panel``
  reduces it to the small bank-year table the models actually use.
* IFRS fee & trading income, hand-collected from each bank's annual report.
* Table A1 of Melik-Parsadanyan (2026), used for the replication check.
"""

from pathlib import Path

import pandas as pd

from . import config

# OctoBI ratio name -> column name in the derived panel
OCTOBI_RATIOS = {
    "NIM": "nim",
    "CIR": "cir",
    "CCR": "ccr",
    "Assets/Equity": "assets_to_equity",
    "IEA/Assets": "iea_to_assets",
    "Net Loan Portfolio/Assets": "net_loans_to_assets",
    "ROE": "roe",
}
REQUIRED = ["nim", "cir", "ccr", "assets_to_equity", "iea_to_assets", "roe"]

# OctoBI publishes several variants of some ratios. Prefer the period average
# (balance-sheet ratios), then the point-in-time value, then year-to-date
# (flow ratios such as NIM, CIR, ROE are only available YTD or quarterly).
TYPE_PRIORITY = {"average": 0, "as of date": 1, "YTD": 2}


def find_raw_octobi_export(raw_dir: Path = config.RAW_DIR) -> Path:
    matches = sorted(raw_dir.glob(config.OCTOBI_RAW_GLOB))
    if not matches:
        raise FileNotFoundError(
            f"No OctoBI export matching {config.OCTOBI_RAW_GLOB!r} in {raw_dir}"
        )
    return matches[-1]


def build_octobi_panel(raw_csv: Path, years=config.YEARS) -> pd.DataFrame:
    """Reduce the raw OctoBI export to one row per bank-year (values in %)."""
    raw = pd.read_csv(raw_csv)
    year_ends = [f"{y}-12-31" for y in years]
    raw = raw[
        raw["ratio_name"].isin(OCTOBI_RATIOS)
        & raw["date"].isin(year_ends)
        & ~raw["bank"].isin(config.EXCLUDED_ENTITIES)
    ].copy()

    raw["priority"] = raw["type"].map(TYPE_PRIORITY).fillna(99)
    best = (
        raw.sort_values("priority")
        .groupby(["bank", "date", "ratio_name"], as_index=False)
        .first()
    )
    panel = (
        best.pivot(index=["bank", "date"], columns="ratio_name", values="ratio")
        .rename(columns=OCTOBI_RATIOS)
        .reset_index()
    )
    panel.insert(1, "year", panel.pop("date").str[:4].astype(int))
    panel = panel.dropna(subset=REQUIRED)
    cols = ["bank", "year", *OCTOBI_RATIOS.values()]
    return panel[cols].sort_values(["year", "bank"]).reset_index(drop=True)


def load_octobi_panel() -> pd.DataFrame:
    """Bank-year OctoBI ratios as decimals (3.5% -> 0.035)."""
    if config.OCTOBI_PANEL.exists():
        panel = pd.read_csv(config.OCTOBI_PANEL)
    else:
        panel = build_octobi_panel(find_raw_octobi_export())
    ratio_cols = list(OCTOBI_RATIOS.values())
    panel[ratio_cols] = panel[ratio_cols] / 100.0
    return panel


def load_ifrs_fees() -> pd.DataFrame:
    """Net fee & commission and net trading/FX income, as a share of total assets."""
    return pd.read_csv(config.IFRS_FEES)


def load_paper_table_a1() -> pd.DataFrame:
    return pd.read_csv(config.PAPER_TABLE_A1)
