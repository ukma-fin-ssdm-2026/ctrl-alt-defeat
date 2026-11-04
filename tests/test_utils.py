import pytest
from src.api.utils import generate_review_summary, check_review_policy_violations


def test_empty_reviews_summary():
    # Trace: T-005
    expected = {"total_reviews": 0, "average_rating": 0.0, "distribution": {i: 0 for i in range(1, 11)}}
    assert generate_review_summary([]) == expected


def test_reviews_total_and_average():
    # Trace: T-005
    reviews = [{"rating": 4}, {"rating": 5}]
    result = generate_review_summary(reviews)
    assert result["total_reviews"] == 2
    assert result["average_rating"] == 4.5


def test_reviews_distribution():
    # Trace: T-005
    reviews = [{"rating": 5}, {"rating": 5}, {"rating": 3}]
    result = generate_review_summary(reviews)
    assert result["distribution"][5] == 2
    assert result["distribution"][3] == 1
    assert result["distribution"][1] == 0


def test_reviews_distribution_scale_1_to_10():
    # Trace: T-005
    """
    Regression test for the 1-10 rating scale distribution bug.
    Ensures ratings above 5 (6, 7, 8, 9, 10) are correctly counted in the distribution dictionary.
    """
    reviews = [
        {"rating": 1},
        {"rating": 6},
        {"rating": 7},
        {"rating": 8},
        {"rating": 8},
        {"rating": 9},
        {"rating": 10},
        {"rating": 10},
        {"rating": 10},
    ]
    result = generate_review_summary(reviews)
    assert result["total_reviews"] == 9
    assert result["average_rating"] == round((1 + 6 + 7 + 8 + 8 + 9 + 10 + 10 + 10) / 9, 2)
    assert result["distribution"][1] == 1
    assert result["distribution"][6] == 1
    assert result["distribution"][7] == 1
    assert result["distribution"][8] == 2
    assert result["distribution"][9] == 1
    assert result["distribution"][10] == 3
    # Check that keys from 1 to 10 all exist
    for i in range(1, 11):
        assert i in result["distribution"]


@pytest.mark.parametrize(
    "reviews, expected_total, expected_avg",
    [
        ([{"rating": 10}], 1, 10.0),
        ([{"rating": 1}, {"rating": 10}], 2, 5.5),
        ([{"rating": 7}, {"rating": 8}, {"rating": 9}], 3, 8.0),
        ([{"rating": 6}, {"rating": 6}], 2, 6.0),
    ],
)
def test_parameterized_summary_averages(reviews, expected_total, expected_avg):
    # Trace: T-005
    result = generate_review_summary(reviews)
    assert result["total_reviews"] == expected_total
    assert result["average_rating"] == expected_avg


def test_policy_clean_text():
    # Trace: T-007
    text = "This is a wonderful movie. I highly recommend it to everyone!"
    assert check_review_policy_violations(text) == []


def test_policy_empty_text():
    # Trace: T-007
    assert check_review_policy_violations("") == []


@pytest.mark.parametrize(
    "bad_text, expected_violation",
    [
        ("This movie is terrible and the director is an idiot.", "profanity"),
        ("Watch this movie for free at http://spam-site.com/watch!", "spam_links"),
        ("THIS IS THE BEST MOVIE EVER I CANNOT BELIEVE IT!!!", "shouting"),
        ("This movie is absolute sh1t and the director is a f*ckin genius.", "profanity"),
    ],
)
def test_parameterized_policy_violations(bad_text, expected_violation):
    # Trace: T-007
    violations = check_review_policy_violations(bad_text)
    assert expected_violation in violations


def test_policy_multiple_violations():
    # Trace: T-007
    text = "CLICK HERE HTTP://SCAM.COM TO WATCH THIS IDIOTIC MOVIE"
    violations = check_review_policy_violations(text)
    assert "spam_links" in violations
    assert "profanity" in violations
    assert "shouting" in violations


def test_policy_false_positives():
    # Trace: T-007
    text = "This is a classic movie about a night shift."
    violations = check_review_policy_violations(text)
    assert "profanity" not in violations
