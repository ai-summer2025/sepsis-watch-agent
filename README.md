# 🚨 SepsisWatch Agent

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 46 passing](https://img.shields.io/badge/tests-46%20passing-brightgreen)](test_main.py)
[![Zero API Keys](https://img.shields.io/badge/API%20Keys-Zero%20Required-green)](README.md)

**Agentic AI for sepsis early warning, risk stratification, and care bundle recommendations.**

Sepsis kills 1.7 million Americans per year and costs the healthcare system $62 billion annually. Every hour of delayed treatment increases mortality by ~7%. SepsisWatch is a **7-step agentic AI** that autonomously monitors patient data, computes 4 validated clinical scoring systems, retrieves current evidence from PubMed, and generates time-critical care bundles — all in under 5 seconds, with zero API keys and zero cost.

---

## The Problem

### Sepsis Is the #1 Hospital Killer — And It's Still Frequently Missed

- **350,000 patients** die from sepsis in the US each year (CDC, 2024)
- **70% of sepsis cases** are missed in the early, most-treatable stages
- Clinicians must manually compute 4 different scoring systems (SIRS, qSOFA, SOFA, NEWS2) — each requiring different inputs, different thresholds, and different clinical responses
- **Current EHR alerts** are siloed: they fire individual metrics but never synthesize them into actionable escalation plans with care bundles
- **The Surviving Sepsis Campaign** publishes complex 1-hour, 3-hour, and 6-hour care bundles that nurses and residents often don't have memorized under pressure

### Why Current Tools Fall Short

Most existing sepsis screening tools are:
- **Single-metric alerts** (e.g., "lactate is high") with no context or response plan
- **Static dashboards** that require a human to synthesize 6 different data fields manually
- **Vendor-locked** inside expensive EHR modules with no transparency or customizability
- **Not agentic** — they detect but don't reason, prioritize, or recommend

---

## How It Works: 7-Step Agentic Loop

```
Patient Data Input
       │
       ▼
┌──────────────────────────────────────────────────┐
│  STEP 1: INGEST — Parse & validate vitals, labs  │
│           Clinical context, data quality check    │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│  STEP 2: SCORE — Compute 4 clinical scores       │
│    • SIRS  (0-4 criteria)                        │
│    • qSOFA (0-3, validated for ward use)         │
│    • SOFA  (0-24, organ dysfunction scoring)     │
│    • NEWS2 (0-20, NHS/international standard)    │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│  STEP 3: CLASSIFY — Sepsis-3 Stage Determination │
│    NO SEPSIS → WATCH → SUSPECT → SEPSIS → SHOCK  │
│    Using Singer et al. JAMA 2016 Sepsis-3 defs   │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│  STEP 4: EVIDENCE — Live PubMed Query            │
│    • NCBI E-utilities API (free, no key)         │
│    • Surviving Sepsis Campaign 2021 guidelines   │
│    • Stage-matched evidence retrieval            │
│    • Curated fallback cache if offline           │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│  STEP 5: ALERT — Tiered Clinical Alert           │
│    🟢 GREEN → 🟡 WATCH → 🟠 SUSPECT             │
│    🔴 SEPSIS → 🚨 CRITICAL (Septic Shock)       │
│    Full reasoning chain included                  │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│  STEP 6: BUNDLE — Surviving Sepsis Care Bundles  │
│    • 1-Hour Bundle: cultures, antibiotics, fluids│
│    • 3-Hour Bundle: reassessment, source control │
│    • 6-Hour Bundle: ICU plan, de-escalation      │
│    Source-specific antibiotic recommendations    │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│  STEP 7: MONITOR — Checkpoint Scheduling         │
│    Time-based reassessment intervals by stage    │
│    Trigger conditions for re-escalation          │
│    Response-tracking loop initialization         │
└────────────────────┴─────────────────────────────┘
```

---

## Clinical Scoring Systems Implemented

| Score | Range | Positive Threshold | Purpose |
|-------|-------|--------------------|---------|
| **SIRS** | 0-4 | ≥2 criteria | Inflammatory response screen |
| **qSOFA** | 0-3 | ≥2 points | Ward-level sepsis risk (Seymour 2016) |
| **SOFA** | 0-24 | ≥2 + infection | Sepsis-3 organ dysfunction definition |
| **NEWS2** | 0-20 | ≥7 urgent | NHS national deterioration score |

### Sepsis Stage Classification (Sepsis-3)

| Stage | Criteria | Alert | Time to Act |
|-------|----------|-------|-------------|
| NO SEPSIS | No criteria met | 🟢 Green | Routine |
| WATCH | SIRS ≥2 or NEWS2 ≥7 | 🟡 Yellow | 60 min |
| SUSPECT | qSOFA ≥2 + infection signs | 🟠 Orange | 30 min |
| SEPSIS | SOFA ≥2 + suspected infection | 🔴 Red | 15 min |
| SEPTIC SHOCK | Vasopressors + MAP <65 + lactate >2 | 🚨 Critical | Immediate |

---

## Installation

```bash
git clone https://github.com/ai-summer2025/sepsis-watch-agent.git
cd sepsis-watch-agent
pip install -r requirements.txt
```

**No API keys required.** All external calls use the free NCBI E-utilities API (PubMed). The system includes a curated evidence fallback cache for offline use.

---

## Usage

### Run all 4 clinical scenarios (recommended first run)

```bash
python main.py
```

This runs 4 scenarios across the full sepsis severity spectrum:
- **Scenario A** — 72yo UTI patient, early vital instability (WATCH)
- **Scenario B** — 58yo pneumonia, qSOFA ≥2 (SUSPECT)  
- **Scenario C** — 45yo post-op abdominal sepsis, SOFA ≥2 (SEPSIS)
- **Scenario D** — 66yo neutropenic fever, vasopressors, lactate 5.2 (SEPTIC SHOCK)

### Run a specific scenario

```bash
python main.py --scenario D          # Septic shock scenario
python main.py --scenario B --monitor  # Include monitoring checkpoints
```

### Interactive mode — enter real or custom patient data

```bash
python main.py --custom
```

### Run tests

```bash
python -m pytest test_main.py -v
# 46 passed in ~3s
```

---

## Example Output (Scenario C — Confirmed Sepsis)

```
🏥🏥🏥 SEPSIS WATCH AGENT — PATIENT PT-2403 🏥🏥🏥
Initiating 7-step agentic sepsis assessment...

============================================================
AGENT STEP 1: INGEST
============================================================
  Patient: PT-2403 | Age: 45y
  Suspected source: abdominal
  Vitals: T=39.8°C  HR=132bpm  RR=28/min  BP=88/55mmHg  SpO2=91%  GCS=13
  MAP: 66 mmHg
  Labs: WBC=22.4 | Lactate=3.1mmol/L | Cr=2.1mg/dL | Plt=98

============================================================
AGENT STEP 2: SCORE
============================================================
  Score Results:
  ┌─────────────────────────────────────────────┐
  │  SIRS:  4/4 criteria ⚠️
  │  qSOFA: 3/3 🔴 HIGH RISK
  │  SOFA:  9/24 🔴 ORGAN DYSFUNCTION
  │  NEWS2: 12/20 🔴 URGENT
  └─────────────────────────────────────────────┘

============================================================
AGENT STEP 3: CLASSIFY
============================================================
  → Stage: SEPSIS
  → Alert: 🔴 RED
  → Description: SEPSIS confirmed (Sepsis-3) — initiate protocol

...

============================================================
AGENT STEP 6: BUNDLE
============================================================
  ⏱️  1-HOUR BUNDLE (4 actions):
     ▸ 🧫 BLOOD CULTURES: Obtain at least 2 sets BEFORE antibiotics...
     ▸ 💊 ANTIBIOTICS: Meropenem 1g IV q8h + Metronidazole 500mg IV q8h...
     ▸ 💧 IV FLUIDS: Administer 30 mL/kg IV crystalloid...
     ▸ 📊 MEASURE LACTATE: Draw serum lactate immediately...

  ⏱️  3-HOUR BUNDLE (5 actions):
     ▸ 🔄 REASSESS FLUID RESPONSE...
     ▸ 📊 REPEAT LACTATE: Goal clearance ≥10%...
     ▸ 📍 IDENTIFY SOURCE: CT abdomen/pelvis + surgical consult...

  ⏱️  6-HOUR BUNDLE (7 actions):
     ▸ 🏥 DISPOSITION: ICU admission if SOFA ≥6...
     ▸ 💉 STEROID CONSIDERATION: Hydrocortisone 200mg/day...

══════════════════════════════════════════════════════════════
  🔴 FINAL ASSESSMENT — PATIENT PT-2403
══════════════════════════════════════════════════════════════
  Stage:      SEPSIS (SEPSIS confirmed — initiate protocol)
  Alert:      RED
  Act within: 15 minutes
  Escalation: Ward MD → Senior Resident → Attending (15 min)
  Care bundles ready: 3 (1-hour, 3-hour, 6-hour)
  Evidence citations: 4

  ⏱️  Assessment completed in 1.34s
══════════════════════════════════════════════════════════════
```

---

## Architecture

```
sepsis-watch-agent/
├── main.py                  # CLI entry point (4 scenarios + interactive)
├── src/
│   ├── __init__.py
│   ├── agent.py             # SepsisWatchAgent — 7-step agentic loop
│   ├── models.py            # Data models (Vitals, Labs, SepsisAlert, etc.)
│   ├── scoring.py           # SIRS, qSOFA, SOFA, NEWS2 implementations
│   ├── bundles.py           # SSC care bundle generator (1h/3h/6h)
│   └── evidence.py          # PubMed NCBI API client + curated cache
├── data/
│   └── sample_patients.json # 4 realistic clinical scenarios
├── test_main.py             # 46 tests across 7 test groups
├── requirements.txt
└── .gitignore
```

---

## Why This Matters

**Time is the key variable in sepsis.** Every hour of antibiotic delay increases mortality by 7-10% (Kumar et al., Critical Care Medicine 2006). Every hour SepsisWatch shaves off recognition-to-treatment time is measurable lives saved.

### The agent's clinical value chain:

1. **Recognition** — 4 scoring systems catch what a single alert misses
2. **Reasoning** — Sepsis-3 classification with explicit clinical rationale
3. **Evidence** — Live PubMed integration pulls current Surviving Sepsis Campaign guidelines
4. **Action** — Specific antibiotic recommendations by infection source (10 source types)
5. **Escalation** — Clear chain of command, with timing thresholds that match clinical reality
6. **Monitoring** — Checkpoint scheduling based on severity, so no patient falls through the cracks

### What a Healthcare CTO or YC Partner sees:

- **Zero-cost, zero-lock-in** clinical decision support (vs. $50K/year EHR modules)
- **Auditable reasoning** — every recommendation cited to evidence
- **Open source** — hospitals can fork, customize to their antibiogram, and deploy
- **Composable** — designed to plug into FHIR pipelines, nurse alert systems, or ED triage dashboards

---

## Extending SepsisWatch

SepsisWatch is designed to be extended:

- **Connect to real vitals**: Swap `Vitals` objects for FHIR R4 `Observation` resources
- **EHR integration**: The `ClinicalContext` dataclass mirrors HL7 `Condition` and `MedicationRequest` resources
- **Custom antibiograms**: Extend `bundles.py` with your institution's local antibiotic resistance patterns
- **Alert routing**: Wire `SepsisAlert` to your paging/EHR alerting system
- **Continuous monitoring**: Run `agent.run()` on a schedule with new vitals for real-time surveillance

---

## Evidence & Clinical References

This agent implements guidelines from:

- **Sepsis-3**: Singer M, et al. *The Third International Consensus Definitions for Sepsis and Septic Shock.* JAMA 2016. PMID: 27718378
- **SSC 2021**: Evans L, et al. *Surviving Sepsis Campaign International Guidelines 2021.* Critical Care Medicine 2021. PMID: 32940622
- **qSOFA**: Seymour CW, et al. *Assessment of Clinical Criteria for Sepsis.* JAMA 2016. PMID: 26903335
- **NEWS2**: Royal College of Physicians. *National Early Warning Score 2 (NEWS2).* RCP 2017.
- **Hour-1 Bundle**: Levy MM, et al. *The Surviving Sepsis Campaign Bundle: 2018 update.* CCM 2018.
- **Live evidence**: PubMed NCBI E-utilities API (free, no registration required)

---

## Contributing

Contributions welcome! Priority areas:

- [ ] FHIR R4 connector for real EHR integration
- [ ] Pediatric sepsis scoring (pSOFA, PELOD-2)
- [ ] Procalcitonin-guided antibiotic de-escalation logic
- [ ] Sepsis phenotyping (hyperinflammatory vs. immunosuppressed)
- [ ] Streaming mode for continuous ICU monitoring
- [ ] REST API wrapper for EHR integration

To contribute:
```bash
git clone https://github.com/ai-summer2025/sepsis-watch-agent.git
cd sepsis-watch-agent
# Make your changes
python -m pytest test_main.py -v  # All 46 tests must pass
# Submit PR with description of clinical significance
```

---

## License

MIT License — see [LICENSE](LICENSE).

Free for clinical research, educational use, and open-source health IT projects. If you deploy this in a production clinical environment, please consult with your clinical informatics and patient safety teams. This tool is designed to support clinical decision-making, not replace it.

---

## Disclaimer

SepsisWatch is a clinical decision support research tool. It is not FDA-cleared and should not be used as a standalone medical device. Always apply clinical judgment. Sepsis management requires individualized patient assessment by qualified healthcare professionals.

---

*Built with Python 3.9+ · No paid APIs · No proprietary dependencies · Fork and deploy freely.*
