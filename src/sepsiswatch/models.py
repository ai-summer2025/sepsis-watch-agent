from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Optional


@dataclass
class Observation:
    """One set of vitals/labs. Any field may be missing (None). Units in comments."""

    id: str = "obs"
    resp_rate: Optional[float] = None  # breaths/min
    spo2: Optional[float] = None  # %
    on_oxygen: Optional[bool] = None  # any supplemental oxygen
    fio2: Optional[float] = None  # fraction, 0.21-1.0
    pao2: Optional[float] = None  # mmHg
    paco2: Optional[float] = None  # mmHg
    respiratory_support: bool = False  # invasive or non-invasive ventilation (for SOFA resp 3-4)
    sbp: Optional[float] = None  # mmHg
    map: Optional[float] = None  # mmHg
    heart_rate: Optional[float] = None  # beats/min
    temp_c: Optional[float] = None
    consciousness: Optional[str] = None  # ACVPU: A, C (new confusion), V, P, U
    gcs: Optional[int] = None
    wbc: Optional[float] = None  # x10^9/L
    bands_pct: Optional[float] = None
    lactate: Optional[float] = None  # mmol/L
    platelets: Optional[float] = None  # x10^9/L
    bilirubin: Optional[float] = None  # mg/dL
    creatinine: Optional[float] = None  # mg/dL
    urine_output_ml_24h: Optional[float] = None
    # Vasopressors in mcg/kg/min (dobutamine: any dose counts)
    vasopressors: Dict[str, float] = field(default_factory=dict)
    suspected_infection: bool = False
    baseline_sofa: Optional[int] = None  # assumed 0 when unknown (Sepsis-3 convention)

    @property
    def altered_mentation(self) -> Optional[bool]:
        if self.gcs is not None:
            return self.gcs < 15
        if self.consciousness is not None:
            return self.consciousness.upper() != "A"
        return None

    def to_dict(self) -> dict:
        return asdict(self)
