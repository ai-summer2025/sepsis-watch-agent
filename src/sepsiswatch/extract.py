"""Nursing/ED note -> Observation.

`extract_rules` is a regex baseline for common charting shorthand
("HR 112, BP 88/52, RR 24, SpO2 91% on 2L, T 38.6"). `extract_llm` asks a model for
the same fields, each with an exact quote; values without a verifiable quote are dropped.
"""
from __future__ import annotations

import re
from typing import Optional

from .llm import is_grounded, parse_json

NUM = r"(\d+(?:\.\d+)?)"
PATTERNS = {
    "heart_rate": rf"\b(?:hr|heart rate|pulse)\s*[:=]?\s*{NUM}",
    "resp_rate": rf"\b(?:rr|resp(?:iratory)? rate)\s*[:=]?\s*{NUM}",
    "spo2": rf"\b(?:spo2|sat(?:uration)?s?|o2 sat)\s*[:=]?\s*{NUM}\s*%?",
    "map": rf"\bmap\s*[:=]?\s*{NUM}",
    "gcs": rf"\bgcs\s*[:=]?\s*{NUM}",
    "wbc": rf"\bwbc\s*[:=]?\s*{NUM}",
    "lactate": rf"\b(?:lactate|lactic acid)\s*[:=]?\s*{NUM}",
    "platelets": rf"\b(?:plt|platelets?)\s*[:=]?\s*{NUM}",
    "bilirubin": rf"\b(?:t\.? ?bili|bilirubin|bili)\s*[:=]?\s*{NUM}",
    "creatinine": rf"\b(?:cr|creat(?:inine)?)\s*[:=]?\s*{NUM}",
    "pao2": rf"\bpao2\s*[:=]?\s*{NUM}",
    "paco2": rf"\bpaco2\s*[:=]?\s*{NUM}",
}
INFECTION = re.compile(r"\b(suspected|concern for|presumed|likely|possible|r/o|rule out)\b[^.\n]{0,40}"
                       r"\b(infection|sepsis|pneumonia|uti|urosepsis|cellulitis|cholangitis|bacteremia)\b"
                       r"|\b(pneumonia|urosepsis|cellulitis|cholangitis|pyelonephritis)\b", re.I)
PRESSORS = ["norepinephrine", "epinephrine", "dopamine", "dobutamine", "vasopressin", "phenylephrine"]


def _num(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None


def extract_rules(text: str) -> dict:
    f: dict = {}
    for k, p in PATTERNS.items():
        v = _num(p, text)
        if v is not None:
            f[k] = v
    if "gcs" in f:
        f["gcs"] = int(f["gcs"])
    bp = re.search(r"\b(?:bp|blood pressure)\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})", text, re.I)
    if bp:
        sbp, dbp = float(bp.group(1)), float(bp.group(2))
        f["sbp"] = sbp
        f.setdefault("map", round((sbp + 2 * dbp) / 3, 1))
    t = re.search(r"\b(?:t|temp(?:erature)?)\s*[:=]?\s*(\d{2,3}(?:\.\d+)?)\s*(°?\s*[cf])?", text, re.I)
    if t:
        val = float(t.group(1))
        unit = (t.group(2) or "").strip(" °").lower()
        f["temp_c"] = round((val - 32) * 5 / 9, 1) if unit == "f" or val > 45 else val
    if re.search(r"room air|\bra\b", text, re.I):
        f["on_oxygen"] = False
    o2 = re.search(r"(\d+(?:\.\d+)?)\s*l(?:pm)?\b|\bnasal cannula|\bnon-?rebreather|\bhigh[- ]flow", text, re.I)
    if o2:
        f["on_oxygen"] = True
        if o2.group(1):
            f["fio2"] = round(min(0.21 + 0.04 * float(o2.group(1)), 0.44), 2)  # nasal cannula rule of thumb
    if re.search(r"\b(new )?confus(ed|ion)|disoriented|delirium", text, re.I):
        f["consciousness"] = "C"
    elif re.search(r"\balert and oriented|\ba&ox?\d|\baox\d", text, re.I):
        f["consciousness"] = "A"
    if re.search(r"\b(intubated|mechanical ventilation|bipap|cpap|niv)\b", text, re.I):
        f["respiratory_support"] = True
    pressors = {}
    for drug in PRESSORS:
        m = re.search(rf"\b{drug}\b[^.\n]{{0,20}}?(\d+(?:\.\d+)?)\s*(?:mcg|µg)/kg/min", text, re.I)
        if m:
            pressors[drug] = float(m.group(1))
    if pressors:
        f["vasopressors"] = pressors
    if INFECTION.search(text):
        f["suspected_infection"] = True
    return f


FIELDS = ["resp_rate", "spo2", "on_oxygen", "fio2", "pao2", "paco2", "respiratory_support", "sbp", "map",
          "heart_rate", "temp_c", "consciousness", "gcs", "wbc", "bands_pct", "lactate", "platelets",
          "bilirubin", "creatinine", "urine_output_ml_24h", "suspected_infection"]

LLM_SYSTEM = """Extract the MOST RECENT vital signs and labs from this clinical note for sepsis scoring.
Return ONLY a JSON object:
{"fields": {<name>: {"value": ..., "evidence": "<exact substring of the note>"}},
 "vasopressors": [{"drug": str, "dose_mcg_kg_min": number, "evidence": str}]}
Allowed field names and units: resp_rate (/min), spo2 (%), on_oxygen (bool), fio2 (fraction),
pao2 (mmHg), paco2 (mmHg), respiratory_support (bool: invasive or non-invasive ventilation),
sbp (mmHg), map (mmHg), heart_rate (/min), temp_c (Celsius; convert Fahrenheit),
consciousness ("A" alert, "C" new confusion, "V", "P", "U"), gcs (int), wbc (x10^9/L),
bands_pct (%), lactate (mmol/L), platelets (x10^9/L), bilirubin (mg/dL), creatinine (mg/dL),
urine_output_ml_24h, suspected_infection (bool: clinicians suspect or treat an infection).
Omit anything not stated. If a value was measured more than once, use the latest."""


def extract_llm(text: str, client) -> dict:
    data = parse_json(client.complete(LLM_SYSTEM, text), dict)
    f: dict = {}
    for k, v in (data.get("fields") or {}).items():
        if k in FIELDS and isinstance(v, dict) and "value" in v and is_grounded(v.get("evidence"), text):
            f[k] = v["value"]
    pressors = {p["drug"].lower(): float(p["dose_mcg_kg_min"]) for p in data.get("vasopressors") or []
                if isinstance(p, dict) and p.get("drug") and p.get("dose_mcg_kg_min") is not None
                and is_grounded(p.get("evidence"), text)}
    if pressors:
        f["vasopressors"] = pressors
    return f

# Missing-value policy: if a vital is absent from the note, its score contribution
# defaults to 0 (not penalised). Callers should check VitalSigns.missing_fields
# and surface a warning when critical labs (lactate, WBC) are unavailable.
