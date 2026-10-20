"""Combine scores into a Sepsis-3 category and suggested next steps.

Actions follow the Surviving Sepsis Campaign:
  SSC-2021  Evans L, et al. Crit Care Med 2021;49(11):e1063-e1143
  HOUR-1    Levy MM, Evans LE, Rhodes A. The Surviving Sepsis Campaign bundle: 2018 update.
            Crit Care Med 2018;46(6):997-1000
SSC 2021 recommends against using qSOFA alone as a screening tool, so screening
here uses SIRS, NEWS2 and qSOFA together.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .models import Observation
from .scores import Score, news2, news2_response, qsofa, sirs, sofa

CATEGORIES = ["septic_shock", "sepsis", "possible_sepsis", "infection_no_organ_dysfunction",
              "deterioration_no_infection_documented", "low_risk"]


@dataclass
class Assessment:
    observation_id: str
    category: str
    sofa_delta: int
    scores: List[Score]
    news2_response: str
    reasons: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"observation_id": self.observation_id, "category": self.category,
                "sofa_delta": self.sofa_delta, "news2_response": self.news2_response,
                "scores": [s.__dict__ for s in self.scores], "reasons": self.reasons,
                "actions": self.actions, "missing": self.missing}


def assess(o: Observation) -> Assessment:
    s_sirs, s_q, s_news, s_sofa = sirs(o), qsofa(o), news2(o), sofa(o)
    baseline = o.baseline_sofa or 0
    delta = s_sofa.total - baseline
    reasons: List[str] = []
    on_pressors = any(v > 0 for k, v in o.vasopressors.items()) or "dobutamine" in {
        k.lower() for k in o.vasopressors}

    if o.suspected_infection and delta >= 2 and on_pressors and (o.lactate or 0) > 2:
        cat = "septic_shock"
        reasons.append("Suspected infection, SOFA rise >= 2, vasopressor requirement and lactate > 2 mmol/L "
                       "(Sepsis-3 septic shock; confirm adequate fluid resuscitation and MAP target 65).")
    elif o.suspected_infection and delta >= 2:
        cat = "sepsis"
        reasons.append(f"Suspected infection with SOFA rise of {delta} from baseline {baseline} (Sepsis-3).")
    elif o.suspected_infection and (s_q.total >= 2 or s_news.total >= 5 or s_sirs.total >= 2):
        cat = "possible_sepsis"
        reasons.append(f"Suspected infection with a positive screen (SIRS {s_sirs.total}, qSOFA {s_q.total}, "
                       f"NEWS2 {s_news.total}); organ dysfunction not (yet) shown by SOFA.")
    elif o.suspected_infection:
        cat = "infection_no_organ_dysfunction"
        reasons.append("Suspected infection without a positive screen or SOFA rise.")
    elif s_news.total >= 5 or delta >= 2:
        cat = "deterioration_no_infection_documented"
        reasons.append(f"NEWS2 {s_news.total}, SOFA {s_sofa.total} without documented suspected infection: "
                       "consider infection in the differential.")
    else:
        cat = "low_risk"

    actions: List[str] = []
    if cat in ("septic_shock", "sepsis"):
        actions += [
            "Measure lactate; re-measure within 2-4 hours if > 2 mmol/L. (HOUR-1, SSC-2021)",
            "Obtain blood cultures before antibiotics, without delaying them. (HOUR-1)",
            "Give broad-spectrum antibiotics within 1 hour of recognition. (SSC-2021)",
        ]
        if cat == "septic_shock" or (o.sbp is not None and o.sbp < 90) or (o.lactate or 0) >= 4:
            actions.append("Start 30 mL/kg IV crystalloid within the first 3 hours for hypotension or lactate >= 4, "
                           "reassessing fluid responsiveness. (SSC-2021, weak recommendation)")
        if cat == "septic_shock" or (o.map is not None and o.map < 65):
            actions.append("Use vasopressors (norepinephrine first-line) to target MAP 65 mmHg. (SSC-2021)")
    elif cat == "possible_sepsis":
        actions += [
            "Rapid clinical assessment for infection versus non-infectious causes. (SSC-2021)",
            "Measure lactate and obtain cultures. (SSC-2021)",
            "If concern for infection persists, give antibiotics within 3 hours of recognition. (SSC-2021)",
        ]
    if s_news.total >= 5 or any(v == 3 for v in s_news.components.values()):
        actions.append(f"NEWS2 response: {news2_response(s_news)}. (RCP NEWS2)")

    missing = sorted({f"{s.name}: {m}" for s in (s_sirs, s_q, s_news, s_sofa) for m in s.missing})
    if o.baseline_sofa is None and o.suspected_infection:
        missing.append("baseline SOFA unknown; assumed 0 (Sepsis-3 convention)")
    return Assessment(o.id, cat, delta, [s_sirs, s_q, s_news, s_sofa], news2_response(s_news),
                      reasons, actions, missing)

# assess.py — integrates SIRS, qSOFA, NEWS2 and SOFA into a single risk tier.
