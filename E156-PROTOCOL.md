# E156-PROTOCOL

## Project
MultivarMA -- Browser Multivariate Meta-Analysis (Riley Model)

## Dates
- Created: 2026-04-09
- Last updated: 2026-04-09

## E156 Body (CURRENT)
How much precision does multivariate pooling of correlated outcomes gain over separate univariate syntheses? We implement the Riley random-effects model in a zero-dependency browser tool that jointly estimates 2-3 outcome means with iterative generalised least squares and method-of-moments between-study variance. Applied to the Berkey 1998 periodontal benchmark (k=5, PD+AL), the engine recovers pooled PD approx -0.33 and AL approx -0.22, matching R mvmeta within rounding tolerance. Borrowing-of-strength reaches 5-15% SE reduction when within-study correlation exceeds 0.4, collapses toward zero when rho=0, and remains valid with missing outcomes via large-variance imputation. The tool demonstrates that correlated-outcome synthesis is tractable in the browser with closed-form matrix algebra and no external dependencies. All results are conditional on correct specification of within-study correlations, which are rarely reported and typically assumed.

## Dashboard
https://mahmood726-cyber.github.io/MultivarMA/
