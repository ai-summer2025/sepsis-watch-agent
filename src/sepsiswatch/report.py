from __future__ import annotations

from .assess import Assessment

LABEL = {"septic_shock": "SEPTIC SHOCK (Sepsis-3 criteria met)", "sepsis": "SEPSIS (Sepsis-3 criteria met)",
         "possible_sepsis": "POSSIBLE SEPSIS (screen positive)",
         "infection_no_organ_dysfunction": "Infection suspected, no screen positive",
         "deterioration_no_infection_documented": "Clinical deterioration (no infection documented)",
         "low_risk": "Low risk on current data"}


def to_markdown(a: Assessment) -> str:
    out = [f"# Sepsis screen: {a.observation_id}", "", f"**{LABEL[a.category]}**", ""]
    out += [f"- {r}" for r in a.reasons]
    out += ["", "| Score | Total | Components |", "|---|---|---|"]
    for s in a.scores:
        comps = ", ".join(f"{k} {v}" for k, v in s.components.items())
        out.append(f"| {s.name} | {s.total} | {comps} |")
    out += ["", f"NEWS2 response level: {a.news2_response}"]
    notes = [n for s in a.scores for n in s.notes]
    if notes:
        out += [""] + [f"_{n}_" for n in notes]
    if a.missing:
        out += ["", "**Missing inputs (scored as 0):** " + "; ".join(a.missing)]
    if a.actions:
        out += ["", "## Suggested next steps", ""] + [f"- {x}" for x in a.actions]
    out += ["", "_Decision support only. Not a substitute for clinical assessment._"]
    return "\n".join(out)

SECTION_DIVIDER = "─" * 72  # used in plain-text and markdown output
