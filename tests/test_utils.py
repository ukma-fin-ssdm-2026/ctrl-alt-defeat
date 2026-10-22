from src.api.utils import generate_review_summary


def test_empty_reviews_summary():
    expected = {"total_reviews": 0, "average_rating": 0.0, "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}
    assert generate_review_summary([]) == expected

def test_reviews_total_and_average():
    reviews = [{"rating": 4}, {"rating": 5}]
    result = generate_review_summary(reviews)
    assert result["total_reviews"] == 2
    assert result["average_rating"] == 4.5

def test_reviews_distribution():
    reviews = [{"rating": 5}, {"rating": 5}, {"rating": 3}]
    result = generate_review_summary(reviews)
    assert result["distribution"][5] == 2
    assert result["distribution"][3] == 1
    assert result["distribution"][1] == 0    