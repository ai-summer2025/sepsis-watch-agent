# Changelog

## 1.0.0

Rewrite of the prototype as the `sepsiswatch` package.

- SOFA respiration now uses PaO2/FiO2 (or the Rice SpO2/FiO2 surrogate when SpO2 ≤ 97%), with respiratory support
  required for 3-4 points; replaces invented SpO2 bands
- SOFA renal uses creatinine or 24-hour urine output (< 500 / < 200 mL/day); replaces "< 0.5 mL/h"
- SOFA cardiovascular uses the published vasopressor dose tiers
- SIRS temperature threshold corrected to > 38 °C
- NEWS2 implemented with all published bands and the response levels (5, 7, single parameter 3)
- Sepsis-3 categories use SOFA change from a supplied or assumed-zero baseline; septic shock requires lactate > 2
- Missing inputs are listed in every output
- Note extraction: regex baseline and an optional grounded LLM extractor
- Evaluation: 6 hand-scored boundary observations and 5 labeled notes; CI fails on regression
- GitHub Actions on Python 3.9-3.13, ruff, Dockerfile

## [1.1.0] — 2026-10-22

### Added
- `SEVERITY_TIERS` constant documenting the four risk levels
- `MAX_NOTE_CHARS` guard in the pipeline to prevent regex DoS
- `SECTION_DIVIDER` constant for consistent report formatting
- `.editorconfig` for consistent whitespace across editors

### Fixed
- Clarified missing-vital handling: absent vitals default to 0, not an error
