#!/usr/bin/env python3
"""
SepsisWatch Agent — CLI Interface

Usage:
    python main.py                    # Run all 4 demo scenarios
    python main.py --scenario A       # Run specific scenario (A/B/C/D)
    python main.py --scenario D --verbose
    python main.py --monitor          # Include monitoring checkpoints
    python main.py --custom           # Interactive custom patient input
"""
import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent import SepsisWatchAgent
from src.models import Vitals, LabValues, ClinicalContext


SCENARIOS = {
    "A": {
        "label": "Early Warning (WATCH)",
        "vitals": Vitals(
            temperature_c=38.6, heart_rate=96, respiratory_rate=21,
            systolic_bp=112, diastolic_bp=72, oxygen_saturation=97.0, gcs_score=15
        ),
        "labs": LabValues(wbc_count=13.2, lactate_mmol=1.4, creatinine_mg_dl=1.1, platelet_count=180),
        "context": ClinicalContext(
            patient_id="PT-2401", age=72,
            suspected_infection_source="UTI", known_infection=True
        )
    },
    "B": {
        "label": "Suspected Sepsis",
        "vitals": Vitals(
            temperature_c=39.2, heart_rate=118, respiratory_rate=24,
            systolic_bp=98, diastolic_bp=62, oxygen_saturation=93.5, gcs_score=14
        ),
        "labs": LabValues(wbc_count=18.7, lactate_mmol=1.9, creatinine_mg_dl=1.4, platelet_count=145),
        "context": ClinicalContext(
            patient_id="PT-2402", age=58,
            suspected_infection_source="pneumonia", known_infection=True, altered_mentation=True
        )
    },
    "C": {
        "label": "Confirmed Sepsis",
        "vitals": Vitals(
            temperature_c=39.8, heart_rate=132, respiratory_rate=28,
            systolic_bp=88, diastolic_bp=55, oxygen_saturation=91.0,
            gcs_score=13, urine_output_ml_hr=18.0
        ),
        "labs": LabValues(
            wbc_count=22.4, lactate_mmol=3.1, creatinine_mg_dl=2.1,
            platelet_count=98, bilirubin_mg_dl=2.3
        ),
        "context": ClinicalContext(
            patient_id="PT-2403", age=45,
            suspected_infection_source="abdominal", known_infection=True, altered_mentation=True
        )
    },
    "D": {
        "label": "Septic Shock",
        "vitals": Vitals(
            temperature_c=40.1, heart_rate=148, respiratory_rate=32,
            systolic_bp=76, diastolic_bp=42, oxygen_saturation=87.0,
            gcs_score=11, urine_output_ml_hr=8.0
        ),
        "labs": LabValues(
            wbc_count=0.8, lactate_mmol=5.2, creatinine_mg_dl=3.4,
            platelet_count=32, bilirubin_mg_dl=4.1, glucose_mg_dl=212
        ),
        "context": ClinicalContext(
            patient_id="PT-2404", age=66,
            suspected_infection_source="unknown",
            immunocompromised=True, vasopressor_required=True, altered_mentation=True
        )
    }
}


def run_demo(scenario_key: str, verbose: bool = True, simulate_monitoring: bool = False):
    """Run a demo scenario."""
    if scenario_key not in SCENARIOS:
        print(f"Unknown scenario '{scenario_key}'. Available: A, B, C, D")
        sys.exit(1)

    s = SCENARIOS[scenario_key]
    print(f"\n{'█'*60}")
    print(f"  DEMO SCENARIO {scenario_key}: {s['label']}")
    print(f"{'█'*60}")

    agent = SepsisWatchAgent(verbose=verbose)
    alert = agent.run(
        vitals=s["vitals"],
        labs=s["labs"],
        context=s["context"],
        simulate_monitoring=simulate_monitoring
    )
    return alert


def run_interactive() -> None:
    """Interactive mode — enter custom patient data."""
    print("\n🏥 SEPSIS WATCH AGENT — Interactive Mode")
    print("Enter patient data (press Enter for defaults)\n")

    patient_id = input("Patient ID [PT-CUSTOM]: ").strip() or "PT-CUSTOM"
    age = int(input("Age [65]: ").strip() or "65")
    source = input("Suspected infection source [pneumonia]: ").strip() or "pneumonia"

    print("\n--- Vital Signs ---")
    temp = float(input("Temperature °C [38.5]: ").strip() or "38.5")
    hr = int(input("Heart rate bpm [110]: ").strip() or "110")
    rr = int(input("Respiratory rate /min [22]: ").strip() or "22")
    sbp = int(input("Systolic BP mmHg [95]: ").strip() or "95")
    dbp = int(input("Diastolic BP mmHg [60]: ").strip() or "60")
    spo2 = float(input("SpO2 % [93]: ").strip() or "93")
    gcs = int(input("GCS score [14]: ").strip() or "14")

    print("\n--- Laboratory Values ---")
    wbc = float(input("WBC x10^9/L [15.0]: ").strip() or "15.0")
    lactate = float(input("Lactate mmol/L [2.5]: ").strip() or "2.5")
    creatinine = float(input("Creatinine mg/dL [1.5]: ").strip() or "1.5")

    vitals = Vitals(temp, hr, rr, sbp, dbp, spo2, gcs)
    labs = LabValues(wbc_count=wbc, lactate_mmol=lactate, creatinine_mg_dl=creatinine)
    context = ClinicalContext(
        patient_id=patient_id, age=age,
        suspected_infection_source=source, known_infection=True
    )

    agent = SepsisWatchAgent(verbose=True)
    agent.run(vitals=vitals, labs=labs, context=context)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SepsisWatch Agent — Agentic AI for Sepsis Early Warning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  A - Early Warning (WATCH)      72yo UTI, early vital instability
  B - Suspected Sepsis (SUSPECT) 58yo pneumonia, qSOFA >=2
  C - Confirmed Sepsis           45yo post-op abdominal sepsis, SOFA >=2
  D - Septic Shock               66yo neutropenic fever, vasopressors, lactate 5.2

Examples:
  python main.py                     # Run all 4 scenarios
  python main.py --scenario B        # Run scenario B only
  python main.py --scenario D --monitor   # Include monitoring checkpoints
  python main.py --custom            # Interactive mode
        """
    )
    parser.add_argument("--scenario", "-s", choices=["A", "B", "C", "D"],
                        help="Run specific scenario (A, B, C, or D)")
    parser.add_argument("--monitor", "-m", action="store_true",
                        help="Simulate monitoring checkpoints")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress verbose output")
    parser.add_argument("--custom", "-c", action="store_true",
                        help="Interactive mode — enter custom patient data")

    args = parser.parse_args()
    verbose = not args.quiet

    if args.custom:
        run_interactive()
    elif args.scenario:
        run_demo(args.scenario, verbose=verbose, simulate_monitoring=args.monitor)
    else:
        # Default: run all scenarios
        print("\n" + "🏥" * 30)
        print("  SEPSIS WATCH AGENT — Full Demo (4 Scenarios)")
        print("🏥" * 30)
        print("\nRunning all 4 clinical scenarios to demonstrate the agent's")
        print("7-step agentic reasoning loop across the sepsis severity spectrum.\n")

        results = []
        for key in ["A", "B", "C", "D"]:
            alert = run_demo(key, verbose=verbose, simulate_monitoring=args.monitor)
            results.append(alert)

        print("\n" + "═" * 60)
        print("  DEMO COMPLETE — SUMMARY TABLE")
        print("═" * 60)
        print(f"  {'ID':<10} {'Stage':<20} {'Alert':<12} {'SIRS':<6} {'qSOFA':<7} {'SOFA':<6} {'NEWS2':<6}")
        print(f"  {'-'*70}")
        for alert in results:
            s = alert.scores
            print(
                f"  {alert.patient_id:<10} {alert.stage.value:<20} {alert.alert_level.value:<12} "
                f"{s.sirs_criteria_met:<6} {s.qsofa_score:<7} {s.sofa_score:<6} {s.news2_score:<6}"
            )
        print("═" * 60)


if __name__ == "__main__":
    main()
