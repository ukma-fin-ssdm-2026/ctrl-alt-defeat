from src.api.utils import generate_review_summary, check_review_policy_violations


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

def test_policy_clean_text():
    text = "This is a wonderful movie. I highly recommend it to everyone!"
    assert check_review_policy_violations(text) == []

def test_policy_profanity():
    # Assuming "idiot" are part of our basic blacklist
    text = "This movie is terrible and the director is an idiot."
    violations = check_review_policy_violations(text)
    assert "profanity" in violations

def test_policy_spam_links():
    # Leaving links (http:// or https://) is prohibited on the platform
    text = "Watch this movie for free at http://spam-site.com/watch!"
    violations = check_review_policy_violations(text)
    assert "spam_links" in violations

def test_policy_shouting():
    # If the text contains more than 80% uppercase letters with a length > 20 characters, it is regarded as shouting
    text = "THIS IS THE BEST MOVIE EVER I CANNOT BELIEVE IT!!!"
    violations = check_review_policy_violations(text)
    assert "shouting" in violations

def test_policy_multiple_violations():
    text = "CLICK HERE HTTP://SCAM.COM TO WATCH THIS IDIOTIC MOVIE"
    violations = check_review_policy_violations(text)
    assert "spam_links" in violations
    assert "profanity" in violations
    assert "shouting" in violations

def test_policy_obfuscated_profanity():
    # Check that the user is trying to bypass the filter
    text = "This movie is absolute sh1t and the director is a f*ckin genius."
    violations = check_review_policy_violations(text)
    assert "profanity" in violations

def test_policy_false_positives():
    # Check that normal words containing parts of bad words are not blocked
    # "classic" has "ass", "shift" has "shit"
    text = "This is a classic movie about a night shift."
    violations = check_review_policy_violations(text)
    assert "profanity" not in violations
