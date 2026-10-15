"""
Surviving Sepsis Campaign (SSC) Care Bundles.

Based on SSC 2018 Hour-1 Bundle and 2021 International Guidelines.
These are evidence-based time-critical action sets.
"""
from typing import List
from .models import CareBundle, SepsisStage, Vitals, LabValues, ClinicalContext


def get_one_hour_bundle(
    vitals: Vitals,
    labs: LabValues,
    context: ClinicalContext
) -> CareBundle:
    """
    SSC Hour-1 Bundle (updated 2018/2021).
    All actions should ideally be initiated within 60 minutes of recognition.
    """
    actions = []

    # 1. Lactate
    if labs.lactate_mmol is None:
        actions.append("📊 MEASURE LACTATE: Draw serum lactate immediately (target: <2 mmol/L)")
    elif labs.lactate_mmol >= 4.0:
        actions.append(
            f"🚨 HIGH LACTATE ({labs.lactate_mmol:.1f} mmol/L): Re-measure after resuscitation — "
            "indicates tissue hypoperfusion; septic shock if ≥2 mmol/L after adequate fluids"
        )

    # 2. Blood cultures before antibiotics
    if not context.on_antibiotics:
        actions.append(
            "🧫 BLOOD CULTURES: Obtain at least 2 sets (aerobic + anaerobic) BEFORE antibiotics — "
            "do not delay antibiotics >45 minutes waiting for cultures"
        )

    # 3. Broad-spectrum antibiotics
    if not context.on_antibiotics:
        abx_choice = _get_antibiotic_recommendation(context.suspected_infection_source)
        actions.append(f"💊 ANTIBIOTICS: Administer broad-spectrum IV antibiotics within 1 hour — {abx_choice}")
    else:
        actions.append("✅ ANTIBIOTICS: Patient already on antibiotics — review adequacy of coverage for source")

    # 4. IV fluids
    if vitals.mean_arterial_pressure < 65 or vitals.systolic_bp < 90:
        actions.append(
            "💧 IV FLUIDS: Administer 30 mL/kg IV crystalloid (0.9% NaCl or Lactated Ringer's) "
            "for hypotension or lactate ≥4 mmol/L — reassess response every 500 mL"
        )

    # 5. Vasopressors
    if vitals.mean_arterial_pressure < 65:
        actions.append(
            "🩸 VASOPRESSORS: If MAP <65 mmHg persists after fluid challenge — start Norepinephrine "
            "0.01-0.5 mcg/kg/min (first-line); target MAP ≥65 mmHg"
        )
    elif context.vasopressor_required:
        actions.append(
            "🩸 VASOPRESSORS: Patient on vasopressors — ensure MAP ≥65 mmHg; "
            "consider adding Vasopressin 0.03 units/min if norepinephrine dose high"
        )

    return CareBundle(
        time_target="1-hour",
        actions=actions,
        completed=[False] * len(actions)
    )


def get_three_hour_bundle(
    vitals: Vitals,
    labs: LabValues,
    context: ClinicalContext
) -> CareBundle:
    """
    SSC 3-Hour Bundle actions (reassessment and escalation).
    """
    actions = [
        "🔄 REASSESS FLUID RESPONSE: Evaluate MAP, urine output (target >0.5 mL/kg/hr), "
        "heart rate, capillary refill — avoid fluid overload",
        "📊 REPEAT LACTATE: If initial lactate ≥2 mmol/L — recheck at 2-4 hours; "
        "clearance ≥10% is a positive resuscitation target",
        "🫁 OXYGENATION REVIEW: Target SpO2 ≥94%; consider high-flow nasal cannula "
        "if SpO2 <90% on 4L/min O2 — avoid routine intubation",
        "🧪 LABS: CBC, BMP, LFTs, coagulation (PT/PTT), procalcitonin, BNP if cardiac concern",
        "📍 IDENTIFY SOURCE: Imaging (CXR, CT abdomen/pelvis) + surgical/procedural "
        "source control if indicated (abscess, empyema, perforated viscus)",
    ]

    if vitals.urine_output_ml_hr is not None and vitals.urine_output_ml_hr < 0.5:
        actions.append(
            f"⚠️ OLIGURIA: Urine output {vitals.urine_output_ml_hr:.1f} mL/hr — "
            "evaluate for AKI (check creatinine trend); avoid nephrotoxins; "
            "consider renal protective dosing adjustments"
        )

    if labs.glucose_mg_dl is not None and labs.glucose_mg_dl > 180:
        actions.append(
            f"📈 HYPERGLYCEMIA: Glucose {labs.glucose_mg_dl:.0f} mg/dL — "
            "initiate insulin protocol; target glucose 140-180 mg/dL (NICE-SUGAR protocol)"
        )

    return CareBundle(
        time_target="3-hour",
        actions=actions,
        completed=[False] * len(actions)
    )


def get_six_hour_bundle(
    vitals: Vitals,
    labs: LabValues,
    context: ClinicalContext,
    stage: SepsisStage
) -> CareBundle:
    """
    SSC 6-Hour Bundle (ICU-level management and monitoring).
    """
    actions = [
        "🏥 DISPOSITION: ICU admission if Septic Shock or SOFA ≥6 — "
        "contact critical care for beds and co-management",
        "📊 LACTATE CLEARANCE TARGET: Recheck lactate at 6 hours — "
        "goal clearance ≥10% from initial level; persistent elevation = poor prognosis",
        "💉 STEROID CONSIDERATION: If vasopressor-refractory shock (norepinephrine >0.25 mcg/kg/min) — "
        "consider Hydrocortisone 200mg/day IV (ADRENAL/APROCCHSS evidence)",
        "🩸 TRANSFUSION: Transfuse pRBCs if Hgb <7 g/dL (threshold 9 g/dL for cardiac ischemia/acute MI)",
        "📝 ANTIBIOTIC DE-ESCALATION PLAN: Review cultures at 48-72h — "
        "de-escalate based on sensitivities; target 7-day course for most sources",
        "🔧 MECHANICAL VENTILATION: If intubated — target tidal volume 6 mL/kg IBW, "
        "plateau pressure ≤30 cmH₂O, prone positioning if P/F ratio <150",
    ]

    if stage == SepsisStage.SEPTIC_SHOCK:
        actions.insert(0,
            "🚨 SEPTIC SHOCK PROTOCOL: Activate rapid response / code sepsis team — "
            "norepinephrine + vasopressin ± epinephrine; CVP and arterial line placement"
        )

    actions.append(
        "📋 FAMILY COMMUNICATION: Early goals-of-care discussion if high severity — "
        "involve palliative care if SOFA ≥11 or poor prognosis likely"
    )

    return CareBundle(
        time_target="6-hour",
        actions=actions,
        completed=[False] * len(actions)
    )


def _get_antibiotic_recommendation(infection_source: str) -> str:
    """Return empiric antibiotic recommendation by infection source."""
    source = infection_source.lower() if infection_source else ""

    recommendations = {
        "pneumonia": (
            "Piperacillin-Tazobactam 4.5g IV q6h + Azithromycin 500mg IV daily "
            "(CAP) OR Meropenem 1g IV q8h + Vancomycin (HAP/VAP; MRSA cover)"
        ),
        "uti": (
            "Ceftriaxone 2g IV q24h (uncomplicated); "
            "Pip-Tazo 3.375g IV q6h (complicated/instrumented); "
            "add Vancomycin if urosepsis with MRSA risk"
        ),
        "urinary": (
            "Ceftriaxone 2g IV q24h (uncomplicated); "
            "Pip-Tazo 3.375g IV q6h (complicated/instrumented)"
        ),
        "abdominal": (
            "Meropenem 1g IV q8h + Metronidazole 500mg IV q8h "
            "(broad anaerobic + GN coverage for gut flora)"
        ),
        "skin": (
            "Pip-Tazo 4.5g IV q6h + Vancomycin 25-30 mg/kg IV q8-12h "
            "(SSTI/necrotizing fasciitis — surgical consult urgently)"
        ),
        "meningitis": (
            "Ceftriaxone 2g IV q12h + Vancomycin 25mg/kg IV q8h + Dexamethasone 0.15mg/kg IV q6h "
            "(dexamethasone before or with first antibiotic dose)"
        ),
        "endocarditis": (
            "Vancomycin 25mg/kg IV q8h + Gentamicin 3mg/kg IV q24h "
            "(native valve); consult ID and cardiac surgery"
        ),
    }

    for key, rec in recommendations.items():
        if key in source:
            return rec

    return (
        "Pip-Tazo 4.5g IV q6h + Vancomycin 25mg/kg IV q8h (unknown source — broad-spectrum empiric). "
        "Adjust based on cultures, local antibiogram, and ID consult"
    )


def generate_care_bundles(
    vitals: Vitals,
    labs: LabValues,
    context: ClinicalContext,
    stage: SepsisStage
) -> List[CareBundle]:
    """Generate all relevant care bundles based on sepsis stage."""
    bundles = []

    if stage in (SepsisStage.SUSPECT, SepsisStage.SEPSIS, SepsisStage.SEPTIC_SHOCK):
        bundles.append(get_one_hour_bundle(vitals, labs, context))
        bundles.append(get_three_hour_bundle(vitals, labs, context))
        bundles.append(get_six_hour_bundle(vitals, labs, context, stage))
    elif stage == SepsisStage.WATCH:
        bundles.append(get_three_hour_bundle(vitals, labs, context))

    return bundles
