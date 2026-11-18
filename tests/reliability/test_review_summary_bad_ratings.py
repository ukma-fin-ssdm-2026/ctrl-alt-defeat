"""
Reliability, finding 6 (boundary values / error handling): review summary with broken ratings.

Before the fix a review with "rating": None made generate_review_summary fail with TypeError, and a list without
valid ratings divided by zero. Chosen reaction: safe failure — entries without a valid 1-10 rating are skipped,
and the summary counts only the valid ones.
"""

from src.api.utils import generate_review_summary


def test_none_text_bool_and_out_of_range_ratings_are_skipped():
    reviews = [
        {"rating": 8},
        {"rating": None},
        {"rating": "9"},
        {"rating": True},
        {"rating": 0},
        {"rating": 11},
        {"rating": 7.5},
        {},
        "not a review",
        None,
    ]

    summary = generate_review_summary(reviews)

    # Only 8 and 7.5 are valid ratings
    assert summary["total_reviews"] == 2
    assert summary["average_rating"] == 7.75
    assert summary["distribution"][8] == 1 and summary["distribution"][7] == 1
    assert sum(summary["distribution"].values()) == summary["total_reviews"]


def test_no_valid_ratings_gives_an_empty_summary_without_division_by_zero():
    summary = generate_review_summary([{"rating": None}, {"rating": "bad"}, {"rating": False}])

    assert summary["total_reviews"] == 0
    assert summary["average_rating"] == 0.0
    assert set(summary["distribution"].values()) == {0}


def test_boundary_ratings_one_and_ten_are_counted():
    summary = generate_review_summary([{"rating": 1}, {"rating": 10}])

    assert (summary["total_reviews"], summary["average_rating"]) == (2, 5.5)
    assert summary["distribution"][1] == summary["distribution"][10] == 1
