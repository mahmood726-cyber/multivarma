# MultivarMA

Browser-based multivariate meta-analysis using the Riley random-effects model for joint synthesis of 2-3 correlated outcomes.

## Features

- **Riley Multivariate RE Model**: Iterative GLS estimation with method-of-moments tau estimation
- **Borrowing of Strength (BOS)**: Quantifies precision gain from multivariate vs univariate analysis
- **Missing outcomes**: Studies with partial data still contribute via large-variance imputation
- **Joint Forest Plot**: Side-by-side forest columns with multivariate (solid) and univariate (dashed) summary diamonds
- **Between-study correlation heatmap**: Visualizes the estimated Tau matrix
- **BOS bar chart**: Shows percentage improvement in SE for each outcome
- **2 or 3 outcome modes**: Toggle between bivariate and trivariate analysis
- **Correlation slider**: Adjust within-study correlation from -0.95 to 0.95
- **Export**: CSV results and SVG forest plots

## Statistical Methods

- Within-study covariance: `cov_jl = rho * sqrt(v_j * v_l)` (Bland method)
- Between-study variance: DerSimonian-Laird initialization, iterative multivariate update
- Confidence intervals: t-distribution with k-p degrees of freedom
- Matrix operations: closed-form 2x2 and 3x3 inverse (cofactor expansion)
- PSD enforcement: eigenvalue clamping (Higham-style) for Tau matrix

## Demo Data

Berkey 1998 periodontal dataset (5 studies, PD + AL outcomes) is built in.

## Usage

Open `index.html` in any modern browser. No server or CDN required.

## Testing

```bash
python -m pytest test_app.py -v
```

17 Selenium tests covering: correctness against R mvmeta reference values, BOS behavior, missing data handling, SVG rendering, export, and edge cases (k=2, negative correlation, 3-outcome mode).

## Reference

- Riley RD, et al. (2017). Multivariate meta-analysis. *Research Synthesis Methods*.
- Berkey CS, et al. (1998). Meta-analysis of multiple outcomes by regression with random effects. *Statistics in Medicine*.

## Author

Mahmood Ahmad, Tahir Heart Institute
