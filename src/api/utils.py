import re
from typing import List, Dict, Any

def generate_review_summary(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates a comprehensive summary from a list of reviews."""
    summary = {
        "total_reviews": 0,
        "average_rating": 0.0,
        "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    }
    
    if not reviews:
        return summary
        
    total_score = 0
    for review in reviews:
        rating = review.get("rating", 0)
        total_score += rating
        if 1 <= rating <= 5:
            summary["distribution"][rating] += 1
            
    summary["total_reviews"] = len(reviews)
    summary["average_rating"] = round(total_score / summary["total_reviews"], 2)
    
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
    r'\b('
    r'f+[u\*v]+c+k+\w*|'         # fuck, f*ck, fuuuck, fucking
    r's+h+[i1!]+t+\w*|'          # shit, sh1t, shittier
    r'b+[i1!]+t+c+h+\w*|'        # bitch, b1tch, bitches
    r'a+s+s+h+[o0]+l+e+\w*|'     # asshole, assH0le
    r'd+[i1!]+c+k+\w*|'          # dick, d1ck, dickhead
    r'c+u+n+t+\w*|'              # cunt, cuuunt
    r'w+h+[o0]+r+e+\w*|'         # whore, wh0re
    r's+l+[u\*]+t+\w*|'          # slut, sl*t
    r'i+d+i+o+t+\w*|'            # idiot, idiooot
    r'r+e+t+a+r+d+\w*'           # retard
    r')\b', 
    re.IGNORECASE
)

    URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)

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
