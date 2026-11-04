# Methodology notes and limitations

## Mapping OctoBI ratios to the identity

| Paper | Constructed as |
|---|---|
| A/E (IEA / equity) | `Assets/Equity × IEA/Assets` |
| γ (impairment / IEA) | `CCR × (Net loans/Assets) / (IEA/Assets)`. CCR is on a loan basis, so it is rescaled to IEA |
| f, x (per IEA) | IFRS income / total assets ÷ (IEA/Assets) |

The **target** in every decomposition is pre-tax ROE computed from the identity itself, `[(NIM + f + x)(1 − CIR) − γ] · A/E`, as in the paper.

## Why the R² is high, and why that's expected

The target is a deterministic function of the drivers. The R² is below 100% only because the identity is multiplicative while the regression is linear. So the R² measures how well a linear approximation captures the identity. It is not evidence for a behavioral model. What the decomposition tells you is which drivers account for the cross-bank *spread* in ROE in a given year. It does not say which lever a particular bank should pull.

## Four-driver trend model

For 2022–2023 there is no fee or trading income data, so the trend model uses the reduced form `A/E · [NIM(1 − CIR) − γ]`. This is a synthetic target that leaves out non-interest income. Read the trend as directional, and use the 6-driver model for levels.

## Shares are relative

A Shapley share is a share of explained *variance across banks*. A driver can matter a lot for every bank and still get a small share if all banks have similar values for it. Cost efficiency in 2024–25 is an example.

## Small samples

With 16–17 banks and 6 drivers there are only about 9 residual degrees of freedom. The jackknife ranges are the best guide to how stable each share is. Treat any share whose range crosses another driver's share as a tie.

## What was dropped

An earlier version estimated fee and trading yields for every year by solving the identity for `f + x` and splitting it with a fixed fee share. Because the split is fixed, f and x are perfectly collinear in that version, and each always gets exactly half of their combined Shapley share. It has been removed. The same back-calculation is still used for one purpose: estimating VTB's fee and trading yields in the peer-positioning charts, where they are marked with an asterisk.

## Tax

The paper uses bank-specific effective tax rates from IFRS. OctoBI does not provide them, so the reconciliation uses the 18% statutory rate. The decompositions themselves are pre-tax and don't depend on this assumption.
