"""
Clinical scoring engines for sepsis risk assessment.

Implements 4 validated clinical scoring systems:
- SIRS (Systemic Inflammatory Response Syndrome)
- qSOFA (quick Sequential Organ Failure Assessment)
- SOFA (Sequential Organ Failure Assessment)
- NEWS2 (National Early Warning Score 2)
"""
from typing import Optional
from .models import Vitals, LabValues, ClinicalContext, SepsisScores, SepsisStage, AlertLevel


def score_sirs(vitals: Vitals, labs: LabValues) -> int:
    """
    Calculate SIRS criteria count (0-4).
    SIRS requires >= 2 criteria for positive screen.

    Criteria:
    1. Temperature > 38.3°C or < 36.0°C
    2. Heart rate > 90 bpm
    3. Respiratory rate > 20 /min OR PaCO2 < 32 mmHg
    4. WBC > 12,000/mm³ or < 4,000/mm³ OR >10% immature bands
    """
    count = 0

    # Criterion 1: Temperature
    if vitals.temperature_c > 38.3 or vitals.temperature_c < 36.0:
        count += 1

    # Criterion 2: Heart rate
    if vitals.heart_rate > 90:
        count += 1

    # Criterion 3: Respiratory / PaCO2
    if vitals.respiratory_rate > 20:
        count += 1
    elif labs.paco2_mmhg is not None and labs.paco2_mmhg < 32:
        count += 1

    # Criterion 4: WBC
    if labs.wbc_count is not None:
        if labs.wbc_count > 12.0 or labs.wbc_count < 4.0:
            count += 1
    elif labs.bands_percent is not None and labs.bands_percent > 10:
        count += 1

    return count


def score_qsofa(vitals: Vitals, context: ClinicalContext) -> int:
    """
    Calculate qSOFA score (0-3).
    Score >= 2 indicates high risk for poor outcomes.

    Criteria (each = 1 point):
    1. Respiratory rate >= 22 /min
    2. Altered mentation (GCS < 15)
    3. Systolic BP <= 100 mmHg
    """
    score = 0

    if vitals.respiratory_rate >= 22:
        score += 1

    if vitals.gcs_score < 15 or context.altered_mentation:
        score += 1

    if vitals.systolic_bp <= 100:
        score += 1

    return score


def score_news2(vitals: Vitals) -> int:
    """
    Calculate NEWS2 (National Early Warning Score 2).
    Used in UK NHS and many international hospitals.
    Range: 0-20. Score >= 7 = urgent response required.
    """
    score = 0

    # Respiratory rate
    rr = vitals.respiratory_rate
    if rr <= 8:
        score += 3
    elif rr <= 11:
        score += 1
    elif rr <= 20:
        score += 0
    elif rr <= 24:
        score += 2
    else:
        score += 3

    # Oxygen saturation (SpO2 Scale 1)
    spo2 = vitals.oxygen_saturation
    if spo2 <= 91:
        score += 3
    elif spo2 <= 93:
        score += 2
    elif spo2 <= 95:
        score += 1
    else:
        score += 0

    # Systolic blood pressure
    sbp = vitals.systolic_bp
    if sbp <= 90:
        score += 3
    elif sbp <= 100:
        score += 2
    elif sbp <= 110:
        score += 1
    elif sbp <= 219:
        score += 0
    else:
        score += 3

    # Heart rate
    hr = vitals.heart_rate
    if hr <= 40:
        score += 3
    elif hr <= 50:
        score += 1
    elif hr <= 90:
        score += 0
    elif hr <= 110:
        score += 1
    elif hr <= 130:
        score += 2
    else:
        score += 3

    # Temperature
    temp = vitals.temperature_c
    if temp <= 35.0:
        score += 3
    elif temp <= 36.0:
        score += 1
    elif temp <= 38.0:
        score += 0
    elif temp <= 39.0:
        score += 1
    else:
        score += 2

    # Level of consciousness (GCS-based, simplified as AVPU)
    if vitals.gcs_score < 15:
        score += 3

    return score


def score_sofa(vitals: Vitals, labs: LabValues, context: ClinicalContext) -> int:
    """
    Calculate SOFA score (Sequential Organ Failure Assessment).
    Range: 0-24. Each organ system contributes 0-4 points.
    Score >= 2 with suspected infection = Sepsis-3 definition.

    Organ systems: Respiratory, Coagulation, Liver, Cardiovascular, CNS, Renal
    """
    score = 0

    # Respiratory: approximated from SpO2
    spo2 = vitals.oxygen_saturation
    if spo2 >= 95:
        score += 0
    elif spo2 >= 91:
        score += 1
    elif spo2 >= 88:
        score += 2
    elif spo2 >= 85:
        score += 3
    else:
        score += 4

    if context.mechanical_ventilation:
        score += 1

    # Coagulation: Platelets (x10^9/L)
    if labs.platelet_count is not None:
        plts = labs.platelet_count
        if plts >= 150:
            score += 0
        elif plts >= 100:
            score += 1
        elif plts >= 50:
            score += 2
        elif plts >= 20:
            score += 3
        else:
            score += 4

    # Liver: Bilirubin (mg/dL)
    if labs.bilirubin_mg_dl is not None:
        bili = labs.bilirubin_mg_dl
        if bili < 1.2:
            score += 0
        elif bili <= 1.9:
            score += 1
        elif bili <= 5.9:
            score += 2
        elif bili <= 11.9:
            score += 3
        else:
            score += 4

    # Cardiovascular: MAP and vasopressor use
    map_val = vitals.mean_arterial_pressure
    if map_val >= 70 and not context.vasopressor_required:
        score += 0
    elif map_val < 70 and not context.vasopressor_required:
        score += 1
    elif context.vasopressor_required:
        score += 3

    # CNS: GCS
    gcs = vitals.gcs_score
    if gcs == 15:
        score += 0
    elif gcs >= 13:
        score += 1
    elif gcs >= 10:
        score += 2
    elif gcs >= 6:
        score += 3
    else:
        score += 4

    # Renal: Creatinine and urine output
    if labs.creatinine_mg_dl is not None:
        cr = labs.creatinine_mg_dl
        if cr < 1.2:
            score += 0
        elif cr <= 1.9:
            score += 1
        elif cr <= 3.4:
            score += 2
        elif cr <= 4.9:
            score += 3
        else:
            score += 4

    if vitals.urine_output_ml_hr is not None and vitals.urine_output_ml_hr < 0.5:
        score = min(score + 1, 24)

    return score


def classify_sepsis_stage(
    vitals: Vitals,
    labs: LabValues,
    context: ClinicalContext,
    sirs: int,
    qsofa: int,
    sofa: int,
    news2: int
) -> tuple[SepsisStage, AlertLevel]:
    """
    Classify sepsis stage using Sepsis-3 definitions and multi-score approach.

    Sepsis-3 (Singer et al. JAMA 2016):
    - Sepsis: Suspected infection + SOFA >= 2 (or delta SOFA >= 2)
    - Septic Shock: Sepsis + vasopressors needed + lactate > 2 mmol/L
    """
    has_suspected_infection = (
        context.known_infection or
        bool(context.suspected_infection_source) or
        context.on_antibiotics
    )

    # Septic Shock: Vasopressors + lactate > 2 after adequate resuscitation
    if (context.vasopressor_required and
            labs.lactate_mmol is not None and
            labs.lactate_mmol > 2.0):
        return SepsisStage.SEPTIC_SHOCK, AlertLevel.CRITICAL

    # Septic Shock without confirmed lactate (clinical suspicion)
    if context.vasopressor_required and vitals.mean_arterial_pressure < 65:
        return SepsisStage.SEPTIC_SHOCK, AlertLevel.CRITICAL

    # Sepsis-3: Infection + organ dysfunction (SOFA >= 2)
    if has_suspected_infection and sofa >= 2:
        return SepsisStage.SEPSIS, AlertLevel.RED

    # High suspicion: qSOFA >= 2 with infection signs
    if qsofa >= 2 and (has_suspected_infection or sirs >= 2):
        return SepsisStage.SUSPECT, AlertLevel.ORANGE

    # Early warning: SIRS >= 2 or NEWS2 >= 7
    if sirs >= 2 or news2 >= 7:
        return SepsisStage.WATCH, AlertLevel.YELLOW

    # High lactate without clinical sepsis criteria (occult sepsis risk)
    if labs.lactate_mmol is not None and labs.lactate_mmol >= 2.0:
        return SepsisStage.WATCH, AlertLevel.YELLOW

    # Low-level NEWS2 alert
    if news2 >= 5:
        return SepsisStage.WATCH, AlertLevel.YELLOW

    return SepsisStage.NO_SEPSIS, AlertLevel.GREEN


def compute_all_scores(
    vitals: Vitals,
    labs: LabValues,
    context: ClinicalContext
) -> SepsisScores:
    """Compute all sepsis scores and return unified SepsisScores object."""
    sirs = score_sirs(vitals, labs)
    qsofa = score_qsofa(vitals, context)
    sofa = score_sofa(vitals, labs, context)
    news2 = score_news2(vitals)

    stage, alert_level = classify_sepsis_stage(
        vitals, labs, context, sirs, qsofa, sofa, news2
    )

    return SepsisScores(
        sirs_criteria_met=sirs,
        qsofa_score=qsofa,
        sofa_score=sofa,
        news2_score=news2,
        stage=stage,
        alert_level=alert_level
    )
