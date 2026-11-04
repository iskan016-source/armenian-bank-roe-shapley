import numpy as np
import pandas as pd
import pytest

from roe_shapley import analyses
from roe_shapley import components as c
from roe_shapley.shapley import jackknife, r_squared, shapley_r2


def test_shares_sum_to_100():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(30, 4)), columns=list("abcd"))
    df["y"] = df @ [1, 2, 0.5, 0] + rng.normal(scale=0.5, size=30)
    shares, r2 = shapley_r2(df, list("abcd"), target="y")
    assert shares.sum() == pytest.approx(100)
    assert r2 == pytest.approx(r_squared(df[list("abcd")].to_numpy(), df["y"].to_numpy()))


def test_uncorrelated_predictors_get_their_own_r2():
    # With orthogonal predictors, each Shapley value equals its univariate R^2.
    a = np.array([1, -1, 1, -1, 1, -1, 1, -1], dtype=float)
    b = np.array([1, 1, -1, -1, 1, 1, -1, -1], dtype=float)
    df = pd.DataFrame({"a": a, "b": b, "y": 3 * a + b})
    shares, r2 = shapley_r2(df, ["a", "b"], target="y")
    assert r2 == pytest.approx(1.0)
    assert shares["a"] == pytest.approx(90.0)
    assert shares["b"] == pytest.approx(10.0)


def test_jackknife_runs_once_per_bank():
    rng = np.random.default_rng(1)
    df = pd.DataFrame(rng.normal(size=(12, 3)), columns=list("abc"))
    df["y"] = df.sum(axis=1)
    jk = jackknife(df, list("abc"), target="y")
    assert (jk["runs"] == 12).all()
    assert jk["times_ranked_first"].sum() == 12


def test_identity_reproduces_paper_roe():
    a1 = analyses.load_paper_table_a1()
    assert analyses.replicate_paper()["max_identity_gap_pp"] < 0.05
    assert len(a1) == 10


def test_replicates_paper_table_a1():
    shares = analyses.replicate_paper()["shares"][2023]
    assert shares["model_R2_pct"] == pytest.approx(99.8, abs=0.05)
    assert shares["CIR"] == pytest.approx(49.5, abs=0.05)
    assert shares[c.SIX].idxmax() == "CIR"


def test_primary_model_headline_numbers():
    shares = analyses.six_component_ifrs()["shares"]
    assert shares.loc["n_banks"].tolist() == [16, 16]
    assert shares.loc["Leverage", 2024] == pytest.approx(29.1, abs=0.05)
    assert shares.loc["Leverage", 2025] == pytest.approx(31.2, abs=0.05)
    assert shares.loc["model_R2_pct", 2024] == pytest.approx(90.8, abs=0.05)
