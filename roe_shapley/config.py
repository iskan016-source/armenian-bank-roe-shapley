"""Paths and constants shared by every analysis."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RESULTS_DIR = ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"

# Inputs
OCTOBI_RAW_GLOB = "OctoBI_*Ratios*.csv"              # raw export, not committed
OCTOBI_PANEL = DATA_DIR / "octobi_ratios_2022_2025.csv"  # derived, committed
IFRS_FEES = DATA_DIR / "ifrs_fee_trading_2024_2025.csv"
PAPER_TABLE_A1 = DATA_DIR / "paper_table_a1_2023.csv"

# Armenian statutory corporate income tax rate, used where bank-specific
# effective rates are not available.
TAX_RATE = 0.18

# "Banking Sector" is an aggregate row, not a bank. HSBC Armenia was acquired
# by Ardshinbank on 29 Nov 2024 and is excluded from every analysis.
EXCLUDED_ENTITIES = ("Banking Sector", "HSBC")

YEARS = (2022, 2023, 2024, 2025)
IFRS_YEARS = (2024, 2025)
