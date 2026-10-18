"""sepsiswatch check obs.json | sepsiswatch note note.txt [--llm] [--infection/--no-infection]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import load_observation, observation_from_text, run
from .report import to_markdown


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="sepsiswatch", description="Sepsis screening: SIRS, qSOFA, NEWS2, SOFA.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("observation")
    c.add_argument("--format", choices=["markdown", "json"], default="markdown")
    n = sub.add_parser("note")
    n.add_argument("note")
    n.add_argument("--llm", action="store_true")
    n.add_argument("--infection", dest="infection", action="store_true", default=None,
                   help="Clinician suspects infection (overrides extraction)")
    n.add_argument("--no-infection", dest="infection", action="store_false")
    n.add_argument("--format", choices=["markdown", "json"], default="markdown")
    a = p.parse_args(argv)
    if a.cmd == "check":
        obs = load_observation(a.observation)
    else:
        obs = observation_from_text(Path(a.note).read_text(), Path(a.note).stem, a.llm, suspected_infection=a.infection)
    res = run(obs)
    print(json.dumps(res.to_dict(), indent=2) if a.format == "json" else to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
