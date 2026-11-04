# Data

All ratios are year-end (31 December) values.

## `octobi_ratios_2022_2025.csv`

One row per bank-year (17 banks × 4 years). Values are in percent, as OctoBI publishes them, so `assets_to_equity = 602` means 6.02x.

| Column | OctoBI ratio | Variant used |
|---|---|---|
| `nim` | NIM | YTD |
| `cir` | CIR | YTD |
| `ccr` | CCR (credit cost ratio, on a loan basis) | YTD |
| `assets_to_equity` | Assets/Equity | period average |
| `iea_to_assets` | IEA/Assets | period average |
| `net_loans_to_assets` | Net Loan Portfolio/Assets | period average |
| `roe` | ROE (after tax) | YTD |

This file is derived from a raw OctoBI export, which is not redistributed here. With an export in `data/raw/`, rebuild the file with:

```bash
python -m roe_shapley build-panel
```

## `ifrs_fee_trading_2024_2025.csv`

Net fee & commission income and net trading/FX income, collected by hand from each bank's audited IFRS annual report, 16 banks × 2 years. Amounts are in thousands of AMD. `fee_yield` and `trading_yield` are expressed as a share of total assets. The code converts them to an interest-earning-asset basis to match the paper.

## `paper_table_a1_2023.csv`

The dataset published in Melik-Parsadanyan (2026), Table A1: 10 banks, 2023, all six drivers plus effective tax rates and reported ROE.

## Sample and adjustments

| Bank | Treatment | Reason |
|---|---|---|
| HSBC Armenia | Excluded from all analyses | Acquired by Ardshinbank on 29 Nov 2024 |
| VTB Armenia | Excluded from the 6-driver model; included in the 4-driver trend; fee/trading estimated in peer charts | No public IFRS annual report |
| Mellat | Mark-to-market revaluation swings removed from trading income (+3.55bn AMD in 2024, −3.56bn AMD in 2025) | Non-cash IFRS 9 revaluation that reverses the next year. Leaving it in would make Mellat an extreme outlier in both years |
| Converse | Negative 2025 trading yield kept | A real FX loss as the dram appreciated, not a data error |
| Fast Bank | Both years from the full-year IFRS report (published Jan 2026, in Armenian) | |
