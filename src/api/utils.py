from typing import List, Dict, Any

def generate_review_summary(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        "total_reviews": 0,
        "average_rating": 0.0,
        "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    }
    return summary