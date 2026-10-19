import json
from pathlib import Path

from sepsiswatch import Observation, assess
from sepsiswatch.cli import main
from sepsiswatch.extract import extract_llm, extract_rules

ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, reply):
        self.reply = reply

    def complete(self, system, user):
        return self.reply


def test_shock_requires_lactate_above_2():
    base = dict(suspected_infection=True, map=60, platelets=80, vasopressors={"norepinephrine": 0.05})
    assert assess(Observation(lactate=2.0, **base)).category == "sepsis"
    assert assess(Observation(lactate=2.1, **base)).category == "septic_shock"


def test_baseline_sofa_is_subtracted():
    o = Observation(suspected_infection=True, platelets=80, bilirubin=2.5, baseline_sofa=3)
    assert assess(o).category != "sepsis"


def test_possible_sepsis_actions_use_three_hour_window():
    a = assess(Observation(suspected_infection=True, heart_rate=110, temp_c=38.6, resp_rate=18, sbp=120, gcs=15))
    assert a.category == "possible_sepsis"
    assert any("within 3 hours" in x for x in a.actions)


def test_rules_extraction_converts_fahrenheit_and_finds_pressors():
    f = extract_rules("T 101.8F HR 118 BP 92/54 RR 24 SpO2 93% RA. "
                      "norepinephrine 0.08 mcg/kg/min. concern for pneumonia")
    assert f["temp_c"] == 38.8 and f["sbp"] == 92 and f["on_oxygen"] is False
    assert f["vasopressors"] == {"norepinephrine": 0.08} and f["suspected_infection"]


def test_llm_extraction_requires_evidence():
    note = "Repeat HR 126. Lactate 4.6."
    reply = json.dumps({"fields": {"heart_rate": {"value": 126, "evidence": "HR 126"},
                                   "lactate": {"value": 6.4, "evidence": "Lactate 6.4"}},
                        "vasopressors": [{"drug": "norepinephrine", "dose_mcg_kg_min": 0.1, "evidence": "norepi"}]})
    assert extract_llm(note, FakeClient(reply)) == {"heart_rate": 126}


def test_cli(capsys):
    assert main(["check", str(ROOT / "data/observations/septic_shock.json"), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["category"] == "septic_shock"
    assert main(["note", str(ROOT / "data/notes/rapid_response.txt")]) == 0
    assert "SEPTIC SHOCK" in capsys.readouterr().out


def test_eval_does_not_regress():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "eval/run_eval.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
