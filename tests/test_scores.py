import pytest

from sepsiswatch import Observation, news2, qsofa, sirs, sofa
from sepsiswatch.scores import news2_response, pf_ratio


@pytest.mark.parametrize("rr,pts", [(8, 3), (9, 1), (11, 1), (12, 0), (20, 0), (21, 2), (24, 2), (25, 3)])
def test_news2_resp_rate(rr, pts):
    assert news2(Observation(resp_rate=rr)).components["resp_rate"] == pts


@pytest.mark.parametrize("hr,pts", [(40, 3), (41, 1), (50, 1), (51, 0), (90, 0), (91, 1), (110, 1), (111, 2),
                                    (130, 2), (131, 3)])
def test_news2_heart_rate(hr, pts):
    assert news2(Observation(heart_rate=hr)).components["heart_rate"] == pts


@pytest.mark.parametrize("t,pts", [(35.0, 3), (35.1, 1), (36.0, 1), (36.1, 0), (38.0, 0), (38.1, 1), (39.0, 1),
                                   (39.1, 2)])
def test_news2_temperature(t, pts):
    assert news2(Observation(temp_c=t)).components["temperature"] == pts


@pytest.mark.parametrize("sbp,pts", [(90, 3), (91, 2), (100, 2), (101, 1), (110, 1), (111, 0), (219, 0), (220, 3)])
def test_news2_sbp(sbp, pts):
    assert news2(Observation(sbp=sbp)).components["sbp"] == pts


def test_news2_single_three_triggers_low_medium():
    s = news2(Observation(resp_rate=16, spo2=97, on_oxygen=False, sbp=120, heart_rate=80, consciousness="C",
                          temp_c=37))
    assert s.total == 3 and news2_response(s).startswith("low-medium")


def test_sirs_uses_strict_thresholds():
    o = Observation(temp_c=38.0, heart_rate=90, resp_rate=20, wbc=12)
    assert sirs(o).total == 0
    assert sirs(Observation(paco2=31, bands_pct=11)).total == 2


def test_qsofa_mentation_from_acvpu_or_gcs():
    assert qsofa(Observation(consciousness="C")).components["altered_mentation"] == 1
    assert qsofa(Observation(gcs=14)).components["altered_mentation"] == 1
    assert qsofa(Observation(gcs=15)).components["altered_mentation"] == 0


@pytest.mark.parametrize("plt,pts", [(150, 0), (149, 1), (100, 1), (99, 2), (50, 2), (49, 3), (20, 3), (19, 4)])
def test_sofa_coagulation(plt, pts):
    assert sofa(Observation(platelets=plt)).components["coagulation"] == pts


def test_sofa_respiration_needs_support_for_3_and_4():
    assert sofa(Observation(pao2=60, fio2=1.0)).components["respiration"] == 2
    assert sofa(Observation(pao2=60, fio2=1.0, respiratory_support=True)).components["respiration"] == 4


def test_sf_ratio_only_when_spo2_at_most_97():
    assert pf_ratio(Observation(spo2=98, on_oxygen=False)) == (None, False)
    pf, est = pf_ratio(Observation(spo2=94, fio2=0.21))
    assert est and round(pf) == round((94 / 0.21 - 64) / 0.84)


def test_sofa_vasopressor_tiers():
    assert sofa(Observation(vasopressors={"dobutamine": 2})).components["cardiovascular"] == 2
    assert sofa(Observation(vasopressors={"dopamine": 5})).components["cardiovascular"] == 2
    assert sofa(Observation(vasopressors={"norepinephrine": 0.1})).components["cardiovascular"] == 3
    assert sofa(Observation(vasopressors={"norepinephrine": 0.11})).components["cardiovascular"] == 4


def test_missing_inputs_are_reported():
    s = sofa(Observation(gcs=15))
    assert s.total == 0 and len(s.missing) == 5
