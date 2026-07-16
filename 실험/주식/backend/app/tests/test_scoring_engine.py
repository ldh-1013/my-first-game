from app.services.scoring_engine import calculate_final_score


def test_final_score_is_bounded():
    assert 0 <= calculate_final_score(100, 100, 100, 100, 100, 0) <= 100
    assert 0 <= calculate_final_score(-100, -100, -100, -100, -100, 100) <= 100


def test_risk_reduces_final_score():
    safe = calculate_final_score(40, 40, 40, risk_score=0)
    risky = calculate_final_score(40, 40, 40, risk_score=100)
    assert risky < safe

