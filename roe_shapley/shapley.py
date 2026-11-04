"""Shapley (LMG) decomposition of OLS R^2.

Each component is a "player"; the value of a coalition S is the R^2 of an OLS
regression of the target on the components in S (with an intercept). A
component's Shapley value is its average marginal contribution to R^2 across
all orderings in which components can enter the model:

    phi_i = sum over S not containing i of  |S|! (N - |S| - 1)! / N!  *  [R^2(S + i) - R^2(S)]

The phi_i sum exactly to the full-model R^2. We report them as shares of it,
so they sum to 100%.
"""

from itertools import combinations
from math import factorial

import numpy as np
import pandas as pd


def r_squared(X: np.ndarray, y: np.ndarray) -> float:
    if X.shape[1] == 0:
        return 0.0
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return 1.0 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))


def shapley_r2(data: pd.DataFrame, players, target: str = "pretax_roe"):
    """Return (shares in %, as a Series indexed by player; full-model R^2)."""
    players = list(players)
    n = len(players)
    y = data[target].to_numpy(dtype=float)
    X = data[players].to_numpy(dtype=float)

    r2 = {}
    for k in range(n + 1):
        for subset in combinations(range(n), k):
            r2[frozenset(subset)] = r_squared(X[:, list(subset)], y)

    phi = np.zeros(n)
    for i in range(n):
        others = [j for j in range(n) if j != i]
        for k in range(n):
            weight = factorial(k) * factorial(n - k - 1) / factorial(n)
            for subset in combinations(others, k):
                s = frozenset(subset)
                phi[i] += weight * (r2[s | {i}] - r2[s])

    full = r2[frozenset(range(n))]
    return pd.Series(100 * phi / full, index=players, name="share_pct"), full


def jackknife(data: pd.DataFrame, players, target: str = "pretax_roe") -> pd.DataFrame:
    """Leave-one-bank-out robustness: share range and how often each player ranks #1."""
    full, _ = shapley_r2(data, players, target)
    runs = pd.DataFrame(
        [shapley_r2(data.drop(index=bank), players, target)[0] for bank in data.index],
        index=data.index,
    )
    top = runs.idxmax(axis=1).value_counts().reindex(full.index, fill_value=0)
    return pd.DataFrame({
        "share_pct": full,
        "jackknife_min": runs.min(),
        "jackknife_max": runs.max(),
        "times_ranked_first": top,
        "runs": len(runs),
    })
