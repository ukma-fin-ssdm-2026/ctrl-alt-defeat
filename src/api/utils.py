import re
from typing import List, Dict, Any


def generate_review_summary(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summary of reviews on the 1-10 scale. Entries without a valid rating (None, text, bool, out of range)
    are skipped instead of failing the whole summary (scavenger hunt, finding 6).
    """
    summary = {"total_reviews": 0, "average_rating": 0.0, "distribution": {i: 0 for i in range(1, 11)}}

    if not reviews:
        return summary

    total_score = 0
    valid_ratings_count = 0
    for review in reviews:
        if not isinstance(review, dict):
            continue
        rating = review.get("rating")
        # Guard clause: a number from 1 to 10 (bool is a subclass of int in Python, so True is not a rating)
        if isinstance(rating, (int, float)) and not isinstance(rating, bool) and 1 <= rating <= 10:
            total_score += rating
            summary["distribution"][int(rating)] += 1
            valid_ratings_count += 1

    # Counted ratings only: the number matches the distribution and the average
    summary["total_reviews"] = valid_ratings_count
    summary["average_rating"] = round(total_score / valid_ratings_count, 2) if valid_ratings_count else 0.0

    return summary


def check_review_policy_violations(text: str) -> list[str]:
    """
    Analyzes the review text for policy violations.
    Returns a list of violation codes (e.g., 'profanity', 'spam_links', 'shouting').
    Returns an empty list if the text is clean.
    """
    # Matches word boundaries (\b), allows repeated characters (e.g., 'f+'),
    # and common substitutions (e.g., 'u' can be 'u', '*', or 'v').
    PROFANITY_PATTERN = re.compile(
        r"\b("
        r"f+[u\*v]+c+k+\w*|"  # fuck, f*ck, fuuuck, fucking
        r"s+h+[i1!]+t+\w*|"  # shit, sh1t, shittier
        r"b+[i1!]+t+c+h+\w*|"  # bitch, b1tch, bitches
        r"a+s+s+h+[o0]+l+e+\w*|"  # asshole, assH0le
        r"d+[i1!]+c+k+\w*|"  # dick, d1ck, dickhead
        r"c+u+n+t+\w*|"  # cunt, cuuunt
        r"w+h+[o0]+r+e+\w*|"  # whore, wh0re
        r"s+l+[u\*]+t+\w*|"  # slut, sl*t
        r"i+d+i+o+t+\w*|"  # idiot, idiooot
        r"r+e+t+a+r+d+\w*"  # retard
        r")\b",
        re.IGNORECASE,
    )

    URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

    violations = []

    if not text:
        return violations

    if URL_PATTERN.search(text):
        violations.append("spam_links")

    if PROFANITY_PATTERN.search(text):
        violations.append("profanity")

    if len(text) > 20:
        alpha_chars = [char for char in text if char.isalpha()]
        if alpha_chars:
            upper_ratio = sum(1 for char in alpha_chars if char.isupper()) / len(alpha_chars)
            if upper_ratio > 0.8:
                violations.append("shouting")

    return violations


# Start of any HTML tag or comment (<script, <img, </b, <!--) or a javascript: URL (SEC-002, T-032).
# Linear-time pattern: no nested or adjacent optional quantifiers (no catastrophic backtracking).
HTML_MARKUP_PATTERN = re.compile(r"</?[a-zA-Z!]|javascript\s*:", re.IGNORECASE)


def check_comment_policy_violations(text: str) -> list[str]:
    """
    Policy check for comments (FR-011): the review rules plus a ban on HTML markup.
    Returns a list of violation codes, empty if the text is clean.
    """
    violations = check_review_policy_violations(text)
    if text and HTML_MARKUP_PATTERN.search(text):
        violations.append("html_markup")
    return violations
