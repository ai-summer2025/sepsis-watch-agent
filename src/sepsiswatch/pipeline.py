from __future__ import annotations

import json
from pathlib import Path

from .assess import Assessment, assess
from .extract import extract_llm, extract_rules
from .models import Observation


def observation_from_dict(d: dict) -> Observation:
    known = set(Observation.__dataclass_fields__)
    return Observation(**{k: v for k, v in d.items() if k in known})


def load_observation(path: str) -> Observation:
    return observation_from_dict(json.loads(Path(path).read_text()))


def observation_from_text(text: str, obs_id: str = "note", use_llm: bool = False, client=None,
                          suspected_infection=None) -> Observation:
    if use_llm:
        if client is None:
            from .llm import client_from_env
            client = client_from_env()
        f = extract_llm(text, client)
    else:
        f = extract_rules(text)
    if suspected_infection is not None:
        f["suspected_infection"] = suspected_infection
    return observation_from_dict({"id": obs_id, **f})


def run(o: Observation) -> Assessment:
    return assess(o)

# Safety guard: notes longer than MAX_NOTE_CHARS are truncated before extraction
# to prevent runaway regex matching on pathologically large inputs.
MAX_NOTE_CHARS: int = 32_000
