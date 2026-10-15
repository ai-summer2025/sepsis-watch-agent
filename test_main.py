"""
Tests for SepsisWatch Agent.

Tests cover:
1. Clinical scoring engines (SIRS, qSOFA, SOFA, NEWS2)
2. Sepsis stage classification (Sepsis-3 definitions)
3. Care bundle generation
4. Full agent pipeline (end-to-end)
5. Edge cases and input validation
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models import Vitals, LabValues, ClinicalContext, SepsisStage, AlertLevel
from src.scoring import score_sirs, score_qsofa, score_sofa, score_news2, compute_all_scores
from src.bundles import generate_care_bundles, get_one_hour_bundle
from src.agent import SepsisWatchAgent


# --- Shared test fixtures ---

def make_healthy_patient(patient_id="TEST-HEALTHY"):
    return (
        Vitals(temperature_c=37.0, heart_rate=72, respiratory_rate=14,
               systolic_bp=120, diastolic_bp=78, oxygen_saturation=99.0, gcs_score=15),
        LabValues(wbc_count=7.5, lactate_mmol=0.8, creatinine_mg_dl=0.9, platelet_count=220),
        ClinicalContext(patient_id=patient_id, age=45, suspected_infection_source="")
    )

def make_sepsis_patient(patient_id="TEST-SEPSIS"):
    return (
        Vitals(temperature_c=39.5, heart_rate=125, respiratory_rate=26,
               systolic_bp=90, diastolic_bp=58, oxygen_saturation=92.0,
               gcs_score=13, urine_output_ml_hr=20.0),
        LabValues(wbc_count=20.1, lactate_mmol=3.0, creatinine_mg_dl=2.2,
                  platelet_count=105, bilirubin_mg_dl=2.0),
        ClinicalContext(patient_id=patient_id, age=60,
                        suspected_infection_source="pneumonia", known_infection=True, altered_mentation=True)
    )

def make_septic_shock_patient(patient_id="TEST-SHOCK"):
    return (
        Vitals(temperature_c=40.0, heart_rate=145, respiratory_rate=30,
               systolic_bp=78, diastolic_bp=44, oxygen_saturation=88.0,
               gcs_score=11, urine_output_ml_hr=8.0),
        LabValues(wbc_count=1.2, lactate_mmol=5.0, creatinine_mg_dl=3.5,
                  platelet_count=38, bilirubin_mg_dl=4.0, glucose_mg_dl=210),
        ClinicalContext(patient_id=patient_id, age=68,
                        suspected_infection_source="unknown",
                        immunocompromised=True, vasopressor_required=True, altered_mentation=True)
    )


# --- Test Group 1: SIRS Scoring ---

class TestSIRSScoring(unittest.TestCase):

    def test_healthy_patient_zero_sirs(self):
        v, l, c = make_healthy_patient()
        self.assertEqual(score_sirs(v, l), 0)

    def test_fever_alone_is_one_criterion(self):
        v, l, _ = make_healthy_patient()
        v.temperature_c = 38.5
        self.assertEqual(score_sirs(v, l), 1)

    def test_hypothermia_counts_as_criterion(self):
        v, l, _ = make_healthy_patient()
        v.temperature_c = 35.5
        self.assertGreaterEqual(score_sirs(v, l), 1)

    def test_tachycardia_plus_fever_is_two(self):
        v, l, _ = make_healthy_patient()
        v.heart_rate = 95
        v.temperature_c = 38.6
        self.assertEqual(score_sirs(v, l), 2)

    def test_full_sirs_four_criteria(self):
        v, l, _ = make_healthy_patient()
        v.temperature_c = 38.8
        v.heart_rate = 100
        v.respiratory_rate = 22
        l.wbc_count = 14.0
        self.assertEqual(score_sirs(v, l), 4)

    def test_elevated_bands_counts_without_wbc(self):
        v, l, _ = make_healthy_patient()
        l.wbc_count = None
        l.bands_percent = 15.0
        score = score_sirs(v, l)
        self.assertGreaterEqual(score, 1)

    def test_sirs_range_0_to_4(self):
        v, l, _ = make_sepsis_patient()
        score = score_sirs(v, l)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 4)


# --- Test Group 2: qSOFA Scoring ---

class TestQSOFAScoring(unittest.TestCase):

    def test_healthy_patient_zero_qsofa(self):
        v, l, c = make_healthy_patient()
        self.assertEqual(score_qsofa(v, c), 0)

    def test_low_bp_counts(self):
        v, _, c = make_healthy_patient()
        v.systolic_bp = 98
        self.assertEqual(score_qsofa(v, c), 1)

    def test_altered_mentation_counts(self):
        v, _, c = make_healthy_patient()
        v.gcs_score = 14
        self.assertEqual(score_qsofa(v, c), 1)

    def test_high_rr_counts(self):
        v, _, c = make_healthy_patient()
        v.respiratory_rate = 22
        self.assertEqual(score_qsofa(v, c), 1)

    def test_two_criteria_high_risk_threshold(self):
        v, _, c = make_healthy_patient()
        v.systolic_bp = 95
        v.respiratory_rate = 24
        score = score_qsofa(v, c)
        self.assertGreaterEqual(score, 2)

    def test_max_qsofa_is_3(self):
        v, _, c = make_healthy_patient()
        v.systolic_bp = 80
        v.respiratory_rate = 28
        v.gcs_score = 12
        score = score_qsofa(v, c)
        self.assertEqual(score, 3)

    def test_altered_mentation_flag_adds_point(self):
        v, _, c = make_healthy_patient()
        c.altered_mentation = True
        self.assertEqual(score_qsofa(v, c), 1)


# --- Test Group 3: NEWS2 Scoring ---

class TestNEWS2Scoring(unittest.TestCase):

    def test_normal_vitals_low_news2(self):
        v, _, _ = make_healthy_patient()
        score = score_news2(v)
        self.assertLessEqual(score, 2)

    def test_high_rr_increases_news2(self):
        v, _, _ = make_healthy_patient()
        v.respiratory_rate = 26
        score = score_news2(v)
        self.assertGreaterEqual(score, 3)

    def test_low_spo2_increases_news2(self):
        v, _, _ = make_healthy_patient()
        v.oxygen_saturation = 88.0
        score = score_news2(v)
        self.assertGreaterEqual(score, 3)

    def test_altered_gcs_adds_3_points(self):
        v, _, _ = make_healthy_patient()
        v.gcs_score = 12
        score = score_news2(v)
        self.assertGreaterEqual(score, 3)

    def test_news2_urgent_threshold(self):
        v, _, _ = make_sepsis_patient()
        score = score_news2(v)
        self.assertGreaterEqual(score, 7)

    def test_news2_non_negative(self):
        v, _, _ = make_healthy_patient()
        score = score_news2(v)
        self.assertGreaterEqual(score, 0)


# --- Test Group 4: SOFA Scoring ---

class TestSOFAScoring(unittest.TestCase):

    def test_healthy_patient_low_sofa(self):
        v, l, c = make_healthy_patient()
        score = score_sofa(v, l, c)
        self.assertLess(score, 4)

    def test_sepsis_patient_sofa_geq2(self):
        v, l, c = make_sepsis_patient()
        score = score_sofa(v, l, c)
        self.assertGreaterEqual(score, 2)

    def test_vasopressor_increases_cardiovascular_component(self):
        v, l, c = make_healthy_patient()
        c.vasopressor_required = True
        score_without = score_sofa(v, l, ClinicalContext("X", 50, ""))
        score_with = score_sofa(v, l, c)
        self.assertGreaterEqual(score_with, score_without)

    def test_low_platelet_increases_coagulation_score(self):
        v, l, c = make_healthy_patient()
        l.platelet_count = 40
        score = score_sofa(v, l, c)
        self.assertGreaterEqual(score, 3)

    def test_high_creatinine_increases_renal_score(self):
        v, l, c = make_healthy_patient()
        l.creatinine_mg_dl = 4.0
        score = score_sofa(v, l, c)
        self.assertGreaterEqual(score, 3)

    def test_sofa_non_negative(self):
        v, l, c = make_healthy_patient()
        self.assertGreaterEqual(score_sofa(v, l, c), 0)


# --- Test Group 5: Sepsis Stage Classification ---

class TestSepsisClassification(unittest.TestCase):

    def test_healthy_patient_no_sepsis(self):
        v, l, c = make_healthy_patient()
        scores = compute_all_scores(v, l, c)
        self.assertEqual(scores.stage, SepsisStage.NO_SEPSIS)

    def test_septic_shock_classification(self):
        v, l, c = make_septic_shock_patient()
        scores = compute_all_scores(v, l, c)
        self.assertEqual(scores.stage, SepsisStage.SEPTIC_SHOCK)

    def test_sepsis_classification_with_organ_dysfunction(self):
        v, l, c = make_sepsis_patient()
        scores = compute_all_scores(v, l, c)
        self.assertIn(scores.stage, [SepsisStage.SEPSIS, SepsisStage.SEPTIC_SHOCK])

    def test_alert_level_escalation(self):
        v_h, l_h, c_h = make_healthy_patient()
        v_s, l_s, c_s = make_septic_shock_patient()
        healthy_scores = compute_all_scores(v_h, l_h, c_h)
        shock_scores = compute_all_scores(v_s, l_s, c_s)
        alert_order = list(AlertLevel)
        self.assertGreater(
            alert_order.index(shock_scores.alert_level),
            alert_order.index(healthy_scores.alert_level)
        )

    def test_watch_stage_with_sirs_positive(self):
        v, l, c = make_healthy_patient()
        v.temperature_c = 38.6
        v.heart_rate = 95
        v.respiratory_rate = 21
        l.wbc_count = 13.0
        scores = compute_all_scores(v, l, c)
        self.assertIn(scores.stage, [SepsisStage.WATCH, SepsisStage.NO_SEPSIS])

    def test_scores_object_has_all_fields(self):
        v, l, c = make_sepsis_patient()
        scores = compute_all_scores(v, l, c)
        self.assertIsNotNone(scores.sirs_criteria_met)
        self.assertIsNotNone(scores.qsofa_score)
        self.assertIsNotNone(scores.sofa_score)
        self.assertIsNotNone(scores.news2_score)
        self.assertIsNotNone(scores.stage)
        self.assertIsNotNone(scores.alert_level)


# --- Test Group 6: Care Bundle Generation ---

class TestCareBundleGeneration(unittest.TestCase):

    def test_no_sepsis_no_bundles(self):
        v, l, c = make_healthy_patient()
        bundles = generate_care_bundles(v, l, c, SepsisStage.NO_SEPSIS)
        self.assertEqual(len(bundles), 0)

    def test_sepsis_generates_three_bundles(self):
        v, l, c = make_sepsis_patient()
        bundles = generate_care_bundles(v, l, c, SepsisStage.SEPSIS)
        self.assertEqual(len(bundles), 3)

    def test_septic_shock_generates_all_bundles(self):
        v, l, c = make_septic_shock_patient()
        bundles = generate_care_bundles(v, l, c, SepsisStage.SEPTIC_SHOCK)
        self.assertEqual(len(bundles), 3)
        time_targets = [b.time_target for b in bundles]
        self.assertIn("1-hour", time_targets)
        self.assertIn("3-hour", time_targets)
        self.assertIn("6-hour", time_targets)

    def test_one_hour_bundle_has_antibiotic_action(self):
        v, l, c = make_sepsis_patient()
        c.on_antibiotics = False
        bundle = get_one_hour_bundle(v, l, c)
        antibiotic_mentioned = any("antibiotic" in a.lower() or "ANTIBIOTIC" in a for a in bundle.actions)
        self.assertTrue(antibiotic_mentioned, f"No antibiotic action found in: {bundle.actions}")

    def test_bundle_actions_are_non_empty(self):
        v, l, c = make_sepsis_patient()
        bundles = generate_care_bundles(v, l, c, SepsisStage.SEPSIS)
        for bundle in bundles:
            self.assertGreater(len(bundle.actions), 0, f"Empty bundle: {bundle.time_target}")

    def test_watch_stage_generates_monitoring_bundle(self):
        v, l, c = make_healthy_patient()
        v.temperature_c = 38.6
        v.heart_rate = 98
        bundles = generate_care_bundles(v, l, c, SepsisStage.WATCH)
        self.assertGreaterEqual(len(bundles), 1)


# --- Test Group 7: Full Agent Pipeline ---

class TestAgentPipeline(unittest.TestCase):

    def test_agent_runs_healthy_patient(self):
        v, l, c = make_healthy_patient("PIPELINE-HEALTHY")
        agent = SepsisWatchAgent(verbose=False)
        alert = agent.run(v, l, c)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.patient_id, "PIPELINE-HEALTHY")
        self.assertEqual(alert.stage, SepsisStage.NO_SEPSIS)

    def test_agent_runs_septic_shock_patient(self):
        v, l, c = make_septic_shock_patient("PIPELINE-SHOCK")
        agent = SepsisWatchAgent(verbose=False)
        alert = agent.run(v, l, c)
        self.assertEqual(alert.stage, SepsisStage.SEPTIC_SHOCK)
        self.assertEqual(alert.alert_level, AlertLevel.CRITICAL)

    def test_agent_generates_immediate_actions(self):
        v, l, c = make_sepsis_patient("PIPELINE-SEPSIS")
        agent = SepsisWatchAgent(verbose=False)
        alert = agent.run(v, l, c)
        self.assertGreater(len(alert.immediate_actions), 0)

    def test_alert_has_escalation_path(self):
        v, l, c = make_sepsis_patient("PIPELINE-ESCALATION")
        agent = SepsisWatchAgent(verbose=False)
        alert = agent.run(v, l, c)
        self.assertTrue(alert.escalation_path)

    def test_alert_time_to_act_is_shorter_for_shock(self):
        v_h, l_h, c_h = make_healthy_patient("PIPELINE-TIME-H")
        v_s, l_s, c_s = make_septic_shock_patient("PIPELINE-TIME-S")
        agent = SepsisWatchAgent(verbose=False)
        healthy_alert = agent.run(v_h, l_h, c_h)
        shock_alert = agent.run(v_s, l_s, c_s)
        self.assertLess(shock_alert.time_to_act_minutes, healthy_alert.time_to_act_minutes)

    def test_agent_returns_sepsis_alert_object(self):
        from src.models import SepsisAlert
        v, l, c = make_sepsis_patient("PIPELINE-RETURN")
        agent = SepsisWatchAgent(verbose=False)
        alert = agent.run(v, l, c)
        self.assertIsInstance(alert, SepsisAlert)
        self.assertIsNotNone(alert.scores)
        self.assertIsNotNone(alert.reasoning)
        self.assertIsInstance(alert.care_bundles, list)
        self.assertIsInstance(alert.evidence_citations, list)

    def test_agent_with_monitoring_simulation(self):
        v, l, c = make_sepsis_patient("PIPELINE-MONITOR")
        agent = SepsisWatchAgent(verbose=False)
        alert = agent.run(v, l, c, simulate_monitoring=True)
        self.assertIsNotNone(alert)

    def test_all_four_demo_scenarios_complete(self):
        from main import SCENARIOS
        agent = SepsisWatchAgent(verbose=False)
        for key, scenario in SCENARIOS.items():
            with self.subTest(scenario=key):
                alert = agent.run(
                    vitals=scenario["vitals"],
                    labs=scenario["labs"],
                    context=scenario["context"]
                )
                self.assertIsNotNone(alert, f"Scenario {key} returned None")
                self.assertIsNotNone(alert.stage, f"Scenario {key} has no stage")


if __name__ == "__main__":
    unittest.main(verbosity=2)
