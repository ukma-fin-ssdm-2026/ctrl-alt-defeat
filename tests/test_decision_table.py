"""
Decision Table tests for Content Moderation & Policy Validation.
Bonus 2: Test Design Technique — Decision Table.

Factors:
  F1: URL in text (spam_links)
  F2: Profanity (profanity)
  F3: Shouting >80% uppercase, >20 chars (shouting)

Rules R1–R8 cover all 2^3 = 8 combinations.
"""
import pytest
from src.api.utils import check_review_policy_violations


@pytest.mark.parametrize("rule_id, text, expected_violations", [
    # R1: no URL, no profanity, no shouting → clean
    ("R1", "This is a wonderful movie with amazing acting and great plot.", []),
    # R2: URL only → spam_links
    ("R2", "Great movie, watch it at http://example.com for more info.", ["spam_links"]),
    # R3: profanity only → profanity
    ("R3", "This movie is absolute sh1t and very disappointing overall.", ["profanity"]),
    # R4: shouting only → shouting
    ("R4", "THIS IS THE WORST MOVIE EVER MADE IN CINEMA HISTORY", ["shouting"]),
    # R5: URL + profanity → spam_links, profanity
    ("R5", "Check this sh1t at http://bad-site.com for streaming now.", ["spam_links", "profanity"]),
    # R6: URL + shouting → spam_links, shouting
    ("R6", "GO TO HTTP://SCAM.COM FOR THE BEST MOVIE DEALS EVER", ["spam_links", "shouting"]),
    # R7: profanity + shouting → profanity, shouting
    ("R7", "THIS MOVIE IS ABSOLUTE SH1T AND TOTAL DISAPPOINTING", ["profanity", "shouting"]),
    # R8: URL + profanity + shouting → all three
    ("R8", "CLICK HTTP://SCAM.COM THIS MOVIE IS SH1T AND VERY BAD", ["spam_links", "profanity", "shouting"]),
])
def test_decision_table_content_moderation(rule_id, text, expected_violations):
    # Trace: T-007
    """Verifies one row of the 2^3 decision table for check_review_policy_violations."""
    violations = check_review_policy_violations(text)
    assert sorted(violations) == sorted(expected_violations), (
        f"Rule {rule_id} failed: expected {sorted(expected_violations)}, got {sorted(violations)}"
    )

