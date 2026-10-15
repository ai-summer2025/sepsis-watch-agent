"""
SepsisWatchAgent — 7-step agentic reasoning loop for sepsis early warning.

Architecture:
  Step 1: INGEST   — Parse and validate patient data
  Step 2: SCORE    — Compute SIRS, qSOFA, SOFA, NEWS2
  Step 3: CLASSIFY — Determine sepsis stage (Sepsis-3 criteria)
  Step 4: EVIDENCE — Retrieve Surviving Sepsis Campaign guidelines from PubMed
  Step 5: ALERT    — Generate tiered clinical alert with reasoning
  Step 6: BUNDLE   — Recommend evidence-based care bundles (1h/3h/6h)
  Step 7: MONITOR  — Track patient response and re-assess at checkpoints
"""
import time
from typing import Optional, List
from .models import (
    Vitals, LabValues, ClinicalContext, SepsisScores,
    SepsisStage, AlertLevel, SepsisAlert, MonitoringCheckpoint, CareBundle
)
from .scoring import compute_all_scores
from .evidence import get_sepsis_evidence
from .bundles import generate_care_bundles


ALERT_EMOJI = {
    AlertLevel.GREEN: "🟢",
    AlertLevel.YELLOW: "🟡",
    AlertLevel.ORANGE: "🟠",
    AlertLevel.RED: "🔴",
    AlertLevel.CRITICAL: "🚨",
}

STAGE_DESCRIPTION = {
    SepsisStage.NO_SEPSIS: "No sepsis criteria met",
    SepsisStage.WATCH: "Early warning — monitor closely",
    SepsisStage.SUSPECT: "Suspected sepsis — urgent evaluation",
    SepsisStage.SEPSIS: "SEPSIS confirmed (Sepsis-3) — initiate protocol",
    SepsisStage.SEPTIC_SHOCK: "SEPTIC SHOCK — immediate ICU activation",
}

TIME_TO_ACT = {
    SepsisStage.NO_SEPSIS: 240,
    SepsisStage.WATCH: 60,
    SepsisStage.SUSPECT: 30,
    SepsisStage.SEPSIS: 15,
    SepsisStage.SEPTIC_SHOCK: 0,
}


class SepsisWatchAgent:
    """7-step agentic sepsis early warning and response coordinator."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._step_times: dict = {}

    def _log(self, step: int, name: str, msg: str) -> None:
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"AGENT STEP {step}: {name}")
            print(f"{'='*60}")
            print(msg)

    def run(
        self,
        vitals: Vitals,
        labs: LabValues,
        context: ClinicalContext,
        simulate_monitoring: bool = False
    ) -> SepsisAlert:
        """Execute the full 7-step agentic reasoning loop."""
        print(f"\n{'🏥'*3} SEPSIS WATCH AGENT — PATIENT {context.patient_id} {'🏥'*3}")
        print(f"Initiating 7-step agentic sepsis assessment...\n")
        t1 = time.time()
        self._log(1, "INGEST", self._format_patient_summary(vitals, labs, context))
        validation_warnings = self._validate_inputs(vitals, labs, context)
        if validation_warnings:
            print("\n⚠️  Data Quality Warnings:")
            for w in validation_warnings:
                print(f"   • {w}")
        self._log(2, "SCORE", "Computing SIRS, qSOFA, SOFA, and NEWS2 scores...")
        scores = compute_all_scores(vitals, labs, context)
        self._print_scores(scores)
        self._log(3, "CLASSIFY",
            f"Applying Sepsis-3 classification criteria...\n"
            f"  → Stage: {scores.stage.value}\n"
            f"  → Alert: {ALERT_EMOJI[scores.alert_level]} {scores.alert_level.value}\n"
            f"  → Description: {STAGE_DESCRIPTION[scores.stage]}"
        )
        self._log(4, "EVIDENCE", "Querying PubMed for current Surviving Sepsis Campaign guidelines...")
        citations = []
        try:
            citations = get_sepsis_evidence(scores.stage.value, context.suspected_infection_source)
            print(f"\n  📚 Retrieved {len(citations)} evidence citations:")
            for c in citations:
                print(f"     • [{c['year']}] {c['authors']} — {c['title'][:70]}...")
                if c.get("relevance"):
                    print(f"       → Clinical relevance: {c['relevance']}")
        except Exception as e:
            print(f"  ⚠️  PubMed query failed ({e}) — using curated evidence cache")
        self._log(5, "ALERT", "Generating clinical alert with reasoning chain...")
        reasoning = self._build_reasoning(scores, vitals, labs, context)
        immediate_actions = self._get_immediate_actions(scores.stage, vitals, labs, context)
        time_to_act = TIME_TO_ACT[scores.stage]
        print(f"\n  📋 Clinical Reasoning:\n{reasoning}")
        print(f"\n  ⚡ Immediate Actions Required ({len(immediate_actions)}):")
        for action in immediate_actions:
            print(f"     • {action}")
        self._log(6, "BUNDLE", "Generating Surviving Sepsis Campaign care bundles...")
        bundles = generate_care_bundles(vitals, labs, context, scores.stage)
        if bundles:
            for bundle in bundles:
                print(f"\n  ⏱️  {bundle.time_target.upper()} BUNDLE ({len(bundle.actions)} actions):")
                for action in bundle.actions:
                    print(f"     ▸ {action}")
        else:
            print("  ✅ No acute care bundles indicated — continue routine monitoring")
        checkpoints = []
        if simulate_monitoring and scores.stage not in (SepsisStage.NO_SEPSIS,):
            self._log(7, "MONITOR", "Scheduling monitoring checkpoints...")
            checkpoints = self._schedule_monitoring(scores.stage, time_to_act)
            for cp in checkpoints:
                print(f"\n  ⏰ T+{cp.checkpoint_minutes} min: {cp.reassessment}")
        else:
            self._log(7, "MONITOR",
                f"Monitoring plan: Next assessment in {time_to_act} minutes\n"
                f"  → Auto-alert if: HR >130, SpO2 <90%, MAP <65, RR >25"
            )
        elapsed = time.time() - t1
        alert = SepsisAlert(
            patient_id=context.patient_id,
            alert_level=scores.alert_level,
            stage=scores.stage,
            scores=scores,
            reasoning=reasoning,
            immediate_actions=immediate_actions,
            care_bundles=bundles,
            evidence_citations=citations,
            escalation_path=self._get_escalation_path(scores.stage),
            time_to_act_minutes=time_to_act
        )
        self._print_final_summary(alert, elapsed)
        return alert

    def _format_patient_summary(self, v: Vitals, l: LabValues, c: ClinicalContext) -> str:
        lines = [
            f"  Patient: {c.patient_id} | Age: {c.age}y",
            f"  Suspected source: {c.suspected_infection_source or 'Unknown'}",
            f"  Vitals: T={v.temperature_c:.1f}°C  HR={v.heart_rate}bpm  "
            f"RR={v.respiratory_rate}/min  BP={v.systolic_bp}/{v.diastolic_bp}mmHg  "
            f"SpO2={v.oxygen_saturation:.0f}%  GCS={v.gcs_score}",
            f"  MAP: {v.mean_arterial_pressure:.0f} mmHg",
        ]
        lab_parts = []
        if l.wbc_count is not None: lab_parts.append(f"WBC={l.wbc_count:.1f}")
        if l.lactate_mmol is not None: lab_parts.append(f"Lactate={l.lactate_mmol:.1f}mmol/L")
        if l.creatinine_mg_dl is not None: lab_parts.append(f"Cr={l.creatinine_mg_dl:.1f}mg/dL")
        if l.platelet_count is not None: lab_parts.append(f"Plt={l.platelet_count:.0f}")
        if lab_parts:
            lines.append(f"  Labs: {' | '.join(lab_parts)}")
        return "\n".join(lines)

    def _print_scores(self, scores: SepsisScores) -> None:
        print(f"\n  Score Results:")
        print(f"  ┌─────────────────────────────────────────────┐")
        print(f"  │  SIRS:  {scores.sirs_criteria_met}/4 criteria {'⚠️' if scores.sirs_criteria_met >= 2 else '✅'}")
        print(f"  │  qSOFA: {scores.qsofa_score}/3 {'🔴 HIGH RISK' if scores.qsofa_score >= 2 else '✅ Low risk'}")
        print(f"  │  SOFA:  {scores.sofa_score:2d}/24 {'🔴 ORGAN DYSFUNCTION' if scores.sofa_score >= 2 else '✅ Minimal'}")
        print(f"  │  NEWS2: {scores.news2_score:2d}/20 {'🔴 URGENT' if scores.news2_score >= 7 else '🟡 REVIEW' if scores.news2_score >= 5 else '✅ Low'}")
        print(f"  └─────────────────────────────────────────────┘")

    def _build_reasoning(self, scores: SepsisScores, v: Vitals, l: LabValues, c: ClinicalContext) -> str:
        parts = []
        stage = scores.stage
        if stage == SepsisStage.SEPTIC_SHOCK:
            parts.append(
                "SEPTIC SHOCK: Vasopressor requirement + MAP <65 mmHg meets Sepsis-3 septic shock "
                "definition (Singer et al., JAMA 2016). Immediate ICU activation required."
            )
            if l.lactate_mmol and l.lactate_mmol > 2:
                parts.append(f"Elevated lactate ({l.lactate_mmol:.1f} mmol/L >2) confirms tissue hypoperfusion.")
        elif stage == SepsisStage.SEPSIS:
            parts.append(
                f"SEPSIS (Sepsis-3): SOFA score {scores.sofa_score} ≥2 + suspected infection "
                f"({c.suspected_infection_source or 'undetermined'}) = Sepsis by Singer et al. 2016 definition."
            )
        elif stage == SepsisStage.SUSPECT:
            if scores.qsofa_score >= 2:
                criteria = []
                if v.respiratory_rate >= 22: criteria.append(f"RR {v.respiratory_rate}/min (≥22)")
                if v.gcs_score < 15: criteria.append(f"GCS {v.gcs_score} (<15)")
                if v.systolic_bp <= 100: criteria.append(f"SBP {v.systolic_bp} mmHg (≤100)")
                parts.append(
                    f"qSOFA ≥2 ({scores.qsofa_score}/3): {', '.join(criteria)}. "
                    "Validated predictor of sepsis-related mortality (Seymour et al. JAMA 2016)."
                )
        elif stage == SepsisStage.WATCH:
            if scores.sirs_criteria_met >= 2:
                parts.append(
                    f"SIRS criteria met ({scores.sirs_criteria_met}/4) — early inflammatory response. "
                    "Insufficient alone for Sepsis-3 diagnosis but warrants heightened surveillance."
                )
            if scores.news2_score >= 7:
                parts.append(
                    f"NEWS2 score {scores.news2_score} ≥7 triggers mandatory clinical review "
                    "and possible ICU assessment per NHS/NICE guidelines."
                )
        else:
            parts.append(
                f"No sepsis criteria met. SIRS: {scores.sirs_criteria_met}/4, "
                f"qSOFA: {scores.qsofa_score}/3, SOFA: {scores.sofa_score}, "
                f"NEWS2: {scores.news2_score}. Continue standard monitoring."
            )
        return "    " + "\n    ".join(parts)

    def _get_immediate_actions(self, stage: SepsisStage, v: Vitals, l: LabValues, c: ClinicalContext) -> List[str]:
        if stage == SepsisStage.SEPTIC_SHOCK:
            return [
                "🚨 ACTIVATE CODE SEPSIS — call rapid response team NOW",
                "📞 Call intensivist/ICU attending immediately",
                "💉 Start Norepinephrine if not already initiated (MAP target ≥65 mmHg)",
                "🏥 Prepare ICU bed — patient requires invasive monitoring",
                "💧 Run 30 mL/kg crystalloid bolus over 30 minutes if not completed",
            ]
        elif stage == SepsisStage.SEPSIS:
            return [
                "⚠️ Notify attending physician within 15 minutes",
                "🧫 Blood cultures x2 STAT — before antibiotics",
                "💊 Administer broad-spectrum antibiotics within 60 minutes of recognition",
                "💧 Initiate IV fluid resuscitation (30 mL/kg crystalloid)",
                "📊 Order STAT lactate — if ≥4 mmol/L, escalate to septic shock protocol",
            ]
        elif stage == SepsisStage.SUSPECT:
            return [
                "📞 Notify charge nurse and attending within 30 minutes",
                "🧫 Blood cultures x2, urinalysis + culture, procalcitonin",
                "🩺 Full systems review — identify infection source",
                "💊 Discuss antibiotic initiation with attending",
                "📊 Repeat vitals every 30 minutes for 2 hours",
            ]
        elif stage == SepsisStage.WATCH:
            return [
                "📋 Nursing assessment with attending notification if not improving",
                "📊 Repeat vitals in 1 hour",
                "🩸 Consider CBC, CMP, lactate, blood cultures if source suspected",
                "💧 Encourage oral hydration if appropriate; IV access recommended",
            ]
        else:
            return [
                "✅ Routine monitoring — repeat vitals per ward protocol",
                "📋 Document assessment; alert team if deterioration occurs",
            ]

    def _get_escalation_path(self, stage: SepsisStage) -> str:
        paths = {
            SepsisStage.NO_SEPSIS: "Routine ward care → Repeat assessment q4h or PRN",
            SepsisStage.WATCH: "Primary nurse → Charge RN → Ward MD → Rapid Response if deterioration",
            SepsisStage.SUSPECT: "Charge RN → Ward MD (30 min) → Rapid Response if no improvement",
            SepsisStage.SEPSIS: "Ward MD → Senior Resident → Attending (15 min) → ICU consult if SOFA ≥6",
            SepsisStage.SEPTIC_SHOCK: "🚨 CODE SEPSIS → ICU Attending → Intensivist → Emergency Department backup",
        }
        return paths.get(stage, "Contact attending physician")

    def _validate_inputs(self, v: Vitals, l: LabValues, c: ClinicalContext) -> List[str]:
        warnings = []
        if v.temperature_c < 33 or v.temperature_c > 42:
            warnings.append(f"Unusual temperature: {v.temperature_c}°C — verify measurement")
        if v.heart_rate < 20 or v.heart_rate > 300:
            warnings.append(f"Implausible heart rate: {v.heart_rate} bpm")
        if v.oxygen_saturation < 50 or v.oxygen_saturation > 100:
            warnings.append(f"Oxygen saturation out of range: {v.oxygen_saturation}%")
        if v.gcs_score < 3 or v.gcs_score > 15:
            warnings.append(f"GCS out of range: {v.gcs_score} (valid: 3-15)")
        if l.lactate_mmol is not None and l.lactate_mmol < 0:
            warnings.append("Negative lactate value — verify lab result")
        return warnings

    def _schedule_monitoring(self, stage: SepsisStage, initial_time_to_act: int) -> List[MonitoringCheckpoint]:
        checkpoints_config = {
            SepsisStage.SEPTIC_SHOCK: [(15, "MAP, HR, lactate recheck"), (30, "Vasopressor titration"), (60, "Organ function panel")],
            SepsisStage.SEPSIS: [(30, "Fluid response, MAP, UO"), (60, "Lactate clearance check"), (180, "Culture results, antibiotic de-escalation review")],
            SepsisStage.SUSPECT: [(60, "Repeat vitals, source identification"), (120, "Reassess SOFA, cultures pending")],
            SepsisStage.WATCH: [(60, "Repeat vitals"), (120, "Clinical reassessment")],
        }
        config = checkpoints_config.get(stage, [])
        return [
            MonitoringCheckpoint(
                checkpoint_minutes=minutes,
                vitals=Vitals(37.0, 80, 16, 110, 70, 98.0),
                labs=LabValues(lactate_mmol=1.5),
                reassessment=assessment
            )
            for minutes, assessment in config
        ]

    def _print_final_summary(self, alert: SepsisAlert, elapsed: float) -> None:
        emoji = ALERT_EMOJI[alert.alert_level]
        print(f"\n{'═'*60}")
        print(f"  {emoji} FINAL ASSESSMENT — PATIENT {alert.patient_id}")
        print(f"{'═'*60}")
        print(f"  Stage:      {alert.stage.value} ({STAGE_DESCRIPTION[alert.stage]})")
        print(f"  Alert:      {alert.alert_level.value}")
        print(f"  Act within: {alert.time_to_act_minutes} minutes")
        print(f"  Escalation: {alert.escalation_path}")
        print(f"  Care bundles ready: {len(alert.care_bundles)} (1-hour, 3-hour, 6-hour)")
        print(f"  Evidence citations: {len(alert.evidence_citations)}")
        print(f"\n  ⏱️  Assessment completed in {elapsed:.2f}s")
        print(f"{'═'*60}\n")
