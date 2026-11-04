"""Command-line entry point.

    python -m roe_shapley              # run everything
    python -m roe_shapley replicate    # one analysis
    python -m roe_shapley --help
"""

import argparse

import pandas as pd

from . import analyses, charts, config
from .data import build_octobi_panel, find_raw_octobi_export

pd.set_option("display.width", 120)
pd.set_option("display.float_format", "{:.2f}".format)


def _header(title):
    print(f"\n{'=' * 72}\n  {title}\n{'=' * 72}")


def build_panel(_):
    raw = find_raw_octobi_export()
    panel = build_octobi_panel(raw)
    panel.to_csv(config.OCTOBI_PANEL, index=False)
    print(f"Wrote {config.OCTOBI_PANEL.relative_to(config.ROOT)} "
          f"({len(panel)} bank-years) from {raw.name}")


def replicate(_):
    _header("1. Replication: Melik-Parsadanyan (2026), Table A1, 10 banks, 2023")
    r = analyses.replicate_paper()
    print(r["shares"])
    print(f"\nEq. 4 vs reported ROE, largest gap: {r['max_identity_gap_pp']:.3f} pp")


def ifrs(args):
    _header("2. Primary model: 6 components, IFRS fee/trading data, 2024-2025")
    r = analyses.six_component_ifrs()
    print(r["shares"])
    print("\nJackknife (leave-one-bank-out):")
    print(r["jackknife"])
    if not args.no_charts:
        print(f"\nSaved {charts.shapley_shares(r['jackknife']).relative_to(config.ROOT)}")


def trend(args):
    _header("3. Trend: 4 components (OctoBI only), 2022-2025")
    r = analyses.four_component_trend()
    print(r["shares"])
    print("\nJackknife (leave-one-bank-out):")
    print(r["jackknife"])
    if not args.no_charts:
        path = charts.four_component_trend(r["shares"].loc[analyses.c.FOUR], r["jackknife"])
        print(f"\nSaved {path.relative_to(config.ROOT)}")


def reconcile(_):
    _header("4. Does the identity reproduce reported ROE? (t = 18%)")
    r = analyses.reconcile_roe()
    print(r["summary"])


def r2_demo(_):
    _header("5. R² vs sample size (2024, random subsamples)")
    print(analyses.r2_vs_sample_size()["table"])


def peers(args):
    _header(f"6. Peer positioning: {args.bank}")
    r = analyses.peer_ranks(args.bank)
    print(r["ranks"])
    print(f"\nAttribution of {args.bank}'s change in pre-tax ROE, "
          f"{config.IFRS_YEARS[0]} -> {config.IFRS_YEARS[1]} (pp):")
    print(r["roe_change"])
    if not args.no_charts:
        for year in config.IFRS_YEARS:
            path = charts.peer_positioning(analyses.peer_dataset(year), year, args.bank)
            print(f"Saved {path.relative_to(config.ROOT)}")


COMMANDS = {
    "replicate": replicate,
    "ifrs": ifrs,
    "trend": trend,
    "reconcile": reconcile,
    "r2-demo": r2_demo,
    "peers": peers,
}


def main():
    parser = argparse.ArgumentParser(prog="python -m roe_shapley", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", default="all",
                        choices=["all", "build-panel", *COMMANDS])
    parser.add_argument("--bank", default="AMIO", help="bank to highlight in `peers`")
    parser.add_argument("--no-charts", action="store_true", help="skip writing figures")
    args = parser.parse_args()

    if args.command == "build-panel":
        build_panel(args)
    elif args.command == "all":
        for fn in COMMANDS.values():
            fn(args)
    else:
        COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
