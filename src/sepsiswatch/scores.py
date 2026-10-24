"""Sepsis screening and severity scores, implemented from the source definitions.

SIRS    Bone RC et al. Chest 1992;101(6):1644-1655 (ACCP/SCCM consensus)
qSOFA   Seymour CW et al. JAMA 2016;315(8):762-774; Singer M et al. JAMA 2016;315(8):801-810 (Sepsis-3)
SOFA    Vincent JL et al. Intensive Care Med 1996;22(7):707-710
NEWS2   Royal College of Physicians. National Early Warning Score (NEWS) 2. London: RCP, 2017
S/F     Rice TW et al. Chest 2007;132(2):410-417 (SpO2/FiO2 as a surrogate for PaO2/FiO2)

Every score returns its components plus the list of inputs that were missing.
Missing components score 0, the usual convention, and are always reported so a
low score is never mistaken for a normal patient.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import Observation


@dataclass
class Score:
    name: str
    total: int
    components: Dict[str, int]
    missing: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------- SIRS
def sirs(o: Observation) -> Score:
    c: Dict[str, int] = {}
    missing = []
    if o.temp_c is None:
        missing.append("temperature")
    c["temperature"] = int(o.temp_c is not None and (o.temp_c > 38.0 or o.temp_c < 36.0))
    if o.heart_rate is None:
        missing.append("heart_rate")
    c["heart_rate"] = int(o.heart_rate is not None and o.heart_rate > 90)
    if o.resp_rate is None and o.paco2 is None:
        missing.append("resp_rate/paco2")
    c["respiratory"] = int((o.resp_rate is not None and o.resp_rate > 20) or (o.paco2 is not None and o.paco2 < 32))
    if o.wbc is None and o.bands_pct is None:
        missing.append("wbc")
    c["wbc"] = int((o.wbc is not None and (o.wbc > 12 or o.wbc < 4)) or (o.bands_pct is not None and o.bands_pct > 10))
    return Score("SIRS", sum(c.values()), c, missing)


# ---------------------------------------------------------------- qSOFA
def qsofa(o: Observation) -> Score:
    missing = [n for n, v in (("resp_rate", o.resp_rate), ("sbp", o.sbp)) if v is None]
    if o.altered_mentation is None:
        missing.append("mentation (GCS or ACVPU)")
    c = {"resp_rate": int(o.resp_rate is not None and o.resp_rate >= 22),
         "altered_mentation": int(bool(o.altered_mentation)),
         "sbp": int(o.sbp is not None and o.sbp <= 100)}
    return Score("qSOFA", sum(c.values()), c, missing)


# ---------------------------------------------------------------- NEWS2 (SpO2 scale 1)
def _band(x: float, bands: List[Tuple[float, int]], top: int) -> int:
    """bands: list of (upper_inclusive, points) in ascending order; values above the last band score `top`."""
    for upper, pts in bands:
        if x <= upper:
            return pts
    return top


def news2(o: Observation) -> Score:
    c: Dict[str, int] = {}
    missing = []

    def add(name, value, fn):
        if value is None:
            missing.append(name)
            c[name] = 0
        else:
            c[name] = fn(value)

    add("resp_rate", o.resp_rate, lambda v: _band(v, [(8, 3), (11, 1), (20, 0), (24, 2)], 3))
    add("spo2", o.spo2, lambda v: _band(v, [(91, 3), (93, 2), (95, 1)], 0))
    add("air_or_oxygen", o.on_oxygen, lambda v: 2 if v else 0)
    add("sbp", o.sbp, lambda v: _band(v, [(90, 3), (100, 2), (110, 1), (219, 0)], 3))
    add("heart_rate", o.heart_rate, lambda v: _band(v, [(40, 3), (50, 1), (90, 0), (110, 1), (130, 2)], 3))
    if o.consciousness is None and o.gcs is None:
        missing.append("consciousness")
        c["consciousness"] = 0
    else:
        c["consciousness"] = 3 if o.altered_mentation else 0
    add("temperature", o.temp_c, lambda v: _band(v, [(35.0, 3), (36.0, 1), (38.0, 0), (39.0, 1)], 2))
    notes = ["SpO2 scale 1 used; scale 2 (target 88-92%) applies to confirmed hypercapnic respiratory failure."]
    return Score("NEWS2", sum(c.values()), c, missing, notes)


def news2_response(s: Score) -> str:
    if s.total >= 7:
        return "high: emergency assessment by a critical-care-competent team"
    if s.total >= 5:
        return "medium: urgent review by a clinician"
    if any(v == 3 for v in s.components.values()):
        return "low-medium: urgent ward-based review (a single parameter scores 3)"
    return "low: ward-based assessment"


# ---------------------------------------------------------------- SOFA
def _vasopressor_points(v: Dict[str, float]) -> int:
    v = {k.lower(): d for k, d in v.items()}
    dopa, epi, ne = v.get("dopamine", 0), v.get("epinephrine", 0), v.get("norepinephrine", 0)
    if dopa > 15 or epi > 0.1 or ne > 0.1:
        return 4
    if dopa > 5 or epi > 0 or ne > 0:
        return 3
    if dopa > 0 or "dobutamine" in v:
        return 2
    return 0


def pf_ratio(o: Observation) -> Tuple[Optional[float], bool]:
    """Return (PaO2/FiO2, estimated). Falls back to the Rice S/F conversion when SpO2 <= 97%."""
    if o.pao2 is not None and o.fio2:
        return o.pao2 / o.fio2, False
    fio2 = o.fio2 if o.fio2 else (0.21 if o.on_oxygen is False else None)
    if o.spo2 is not None and fio2 and o.spo2 <= 97:
        sf = o.spo2 / fio2
        return (sf - 64) / 0.84, True
    return None, False


def sofa(o: Observation) -> Score:
    c: Dict[str, int] = {}
    missing: List[str] = []
    notes: List[str] = []

    pf, est = pf_ratio(o)
    if pf is None:
        missing.append("respiration (PaO2/FiO2)")
        c["respiration"] = 0
    else:
        if est:
            notes.append(f"Respiration uses SpO2/FiO2-estimated P/F ratio {pf:.0f}.")
        if pf < 100 and o.respiratory_support:
            c["respiration"] = 4
        elif pf < 200 and o.respiratory_support:
            c["respiration"] = 3
        elif pf < 300:
            c["respiration"] = 2
        elif pf < 400:
            c["respiration"] = 1
        else:
            c["respiration"] = 0

    if o.platelets is None:
        missing.append("coagulation (platelets)")
        c["coagulation"] = 0
    else:
        p = o.platelets
        c["coagulation"] = 0 if p >= 150 else 1 if p >= 100 else 2 if p >= 50 else 3 if p >= 20 else 4

    if o.bilirubin is None:
        missing.append("liver (bilirubin)")
        c["liver"] = 0
    else:
        b = o.bilirubin
        c["liver"] = 0 if b < 1.2 else 1 if b < 2.0 else 2 if b < 6.0 else 3 if b < 12.0 else 4

    vp = _vasopressor_points(o.vasopressors)
    if vp:
        c["cardiovascular"] = vp
    elif o.map is None:
        missing.append("cardiovascular (MAP)")
        c["cardiovascular"] = 0
    else:
        c["cardiovascular"] = 1 if o.map < 70 else 0

    if o.gcs is None:
        missing.append("cns (GCS)")
        c["cns"] = 0
    else:
        g = o.gcs
        c["cns"] = 0 if g == 15 else 1 if g >= 13 else 2 if g >= 10 else 3 if g >= 6 else 4

    renal_cr = None if o.creatinine is None else (
        0 if o.creatinine < 1.2 else 1 if o.creatinine < 2.0 else 2 if o.creatinine < 3.5
        else 3 if o.creatinine < 5.0 else 4)
    renal_uo = None if o.urine_output_ml_24h is None else (
        4 if o.urine_output_ml_24h < 200 else 3 if o.urine_output_ml_24h < 500 else 0)
    if renal_cr is None and renal_uo is None:
        missing.append("renal (creatinine or urine output)")
    c["renal"] = max(renal_cr or 0, renal_uo or 0)
    return Score("SOFA", sum(c.values()), c, missing, notes)

# NEWS2 note: confusion assessment maps to the altered consciousness item (score 3).
# A score of 0 on all items yields NEWS2 = 0 (low risk); the alert threshold is >= 7.

# SOFA organ-failure components and their maximum individual scores:
#   Respiratory (PaO2/FiO2)  → 0-4
#   Coagulation (platelets)  → 0-4
#   Liver (bilirubin)        → 0-4
#   Cardiovascular (MAP/vasopressors) → 0-4
#   CNS (GCS)                → 0-4
#   Renal (creatinine/UO)    → 0-4
# Total SOFA >= 2 confirms organ dysfunction for Sepsis-3.
