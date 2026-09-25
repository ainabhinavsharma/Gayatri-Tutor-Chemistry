"""Tests for Bridge Assessment Engine integration (Phase 3)."""
import json
import pytest
from app.bridge.facade import Bridge


def test_bridge_assessment_lifecycle():
    bridge = Bridge()
    
    # 1. Start assessment
    res_str = bridge.start_assessment(json.dumps(["thermo.hess_law", "chem_inorg_bonding"]), question_count=3)
    res = json.loads(res_str)
    assert res["ok"] is True
    assert "assessment_id" in res
    assert res["question_count"] > 0
    assessment_id = res["assessment_id"]
    questions = res["questions"]
    assert len(questions) > 0

    # Ensure anti-leakage in bridge
    first_q = questions[0]
    assert "correct_answer" not in first_q
    assert "explanation" not in first_q
    q_id = first_q["id"]

    # 2. Submit answer
    sub_str = bridge.submit_assessment_answer(assessment_id, q_id, "test_answer")
    sub = json.loads(sub_str)
    assert sub["ok"] is True
    assert "is_correct" in sub
    assert "score_fraction" in sub
    assert "feedback" in sub

    # 3. Complete assessment
    comp_str = bridge.complete_assessment(assessment_id)
    comp = json.loads(comp_str)
    assert comp["ok"] is True
    assert comp["status"] == "COMPLETED"
    assert "score_percentage" in comp

    # 4. Get assessment report
    rep_str = bridge.get_assessment_report(assessment_id)
    rep = json.loads(rep_str)
    assert rep["ok"] is True
    assert "score" in rep
    assert rep["score"]["score_percentage"] == comp["score_percentage"]
    assert len(rep["attempts"]) >= 1
