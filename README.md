# sepsis-watch-agent

[![CI](https://github.com/ai-summer2025/sepsis-watch-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ai-summer2025/sepsis-watch-agent/actions/workflows/ci.yml)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Sepsis screening and Sepsis-3 classification from a set of vitals and labs: **SIRS, qSOFA, NEWS2 and SOFA**, computed from their source definitions, combined into a category (septic shock, sepsis, possible sepsis, and so on) with Surviving Sepsis Campaign next steps. Input is structured JSON or a free-text clinical note; an optional LLM step extracts the values and must quote the text behind each one.

> **Decision support only.** Not a medical device and not a validated early-warning system. All bundled data is synthetic.

## How it works

```
 clinical note ──► extraction ──────────► Observation ──► SIRS · qSOFA · NEWS2 · SOFA ──► Sepsis-3 category ──► next steps
                   regex baseline              ▲          (components + missing inputs)    + reasons            (SSC 2021, Hour-1)
                   or LLM + grounding check    │
 observation JSON ─────────────────────────────┘
```

- **Missing data is never silent.** Missing components score 0 (the usual convention) and are listed in the output, so "SOFA 2" with five missing organ systems is visibly different from a complete SOFA of 2.
- **No single-score screening.** SSC 2021 recommends against using qSOFA alone, so the screen combines SIRS, NEWS2 and qSOFA; Sepsis-3 categories use SOFA change from baseline.
- **The LLM only extracts**, with an exact quote per value, and is told to use the most recent measurement. Values whose quote is not in the note are dropped.

## Scores and definitions

| | Definition used | Source |
|---|---|---|
| SIRS | T > 38 or < 36 °C; HR > 90; RR > 20 or PaCO2 < 32; WBC > 12 or < 4 or bands > 10% | Bone et al., *Chest* 1992 (ACCP/SCCM) |
| qSOFA | RR ≥ 22; altered mentation; SBP ≤ 100 | Seymour et al., *JAMA* 2016 |
| NEWS2 | 7 parameters, SpO2 scale 1, ACVPU; response thresholds 5 and 7 and any single 3 | Royal College of Physicians, 2017 |
| SOFA | 6 organ systems, 0-4 each; P/F with respiratory support for 3-4; vasopressor tiers; creatinine or 24 h urine output | Vincent et al., *Intensive Care Med* 1996 |
| S/F surrogate | P/F estimated from SpO2/FiO2 when no blood gas and SpO2 ≤ 97% | Rice et al., *Chest* 2007 |
| Sepsis / septic shock | Suspected infection + SOFA rise ≥ 2; shock adds vasopressors and lactate > 2 mmol/L | Singer et al., *JAMA* 2016 (Sepsis-3) |
| Next steps | Lactate, cultures, antibiotics within 1 h (3 h for possible sepsis without shock), 30 mL/kg crystalloid, MAP 65 | Evans et al., *Crit Care Med* 2021 (SSC); Levy et al., 2018 (Hour-1 bundle) |

## Quickstart

```bash
pip install -e .
sepsiswatch check data/observations/septic_shock.json
sepsiswatch note data/notes/rapid_response.txt            # regex baseline
sepsiswatch note data/notes/rapid_response.txt --llm      # LLM extraction
docker build -t sepsiswatch . && docker run --rm sepsiswatch
```

LLM configuration: `ANTHROPIC_API_KEY=...`, or `LLM_PROVIDER=openai LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=llama3.1` for a local model (recommended for real patient data). No SDK dependencies.

## Evaluation

`python eval/run_eval.py` regenerates [`eval/RESULTS.md`](eval/RESULTS.md); CI fails on regression. 56 tests, including every threshold boundary in the four scores.

**Score implementation:** 6 observations scored by hand, including one with every input exactly on its threshold and one with every SOFA system at 4. All totals, SOFA components and categories match.

**Extraction:** 5 synthetic notes (ED triage, rapid response, post-op check, MICU admission, ward observations).

| Method | Field accuracy | Sepsis-3 category accuracy |
|---|---|---|
| Regex baseline | 0.89 | 1.00 |
| LLM + grounding | run `python eval/run_eval.py --llm` | |

The baseline's main failure is time: in the rapid-response note it reads the **first** set of vitals (HR 102, BP 108/66) instead of the deteriorated repeat set 30 minutes later, so qSOFA drops from 3 to 1. The category is still right here because SOFA carries it, but this is exactly the error the LLM prompt targets ("use the latest"). The LLM row is left for you to run with your own credentials.

## Limitations

- A single time point. Real early-warning systems use trends; baseline SOFA is assumed 0 unless supplied.
- "Suspected infection" comes from the note or the clinician; the tool does not infer it from vitals.
- NEWS2 uses SpO2 scale 1 only (scale 2 for hypercapnic respiratory failure is not implemented).
- Not validated against outcomes; no claim of sensitivity or specificity for sepsis is made.

## Roadmap

- Time series input (several observations) with trend-aware alerting
- FHIR R4 `Observation` input (LOINC-coded vitals and labs) and a CDS Hooks service
- Retrospective evaluation on MIMIC-IV Sepsis-3 cohorts (alert timing versus antibiotic time)

## Project history

Replaces the earlier prototype in this repository. The prototype's SOFA scored respiration from invented SpO2 bands instead of PaO2/FiO2, applied the renal urine-output criterion as "< 0.5 mL/h", and its SIRS temperature threshold was 38.3 °C instead of 38 °C. All are corrected and covered by boundary tests. See [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).
