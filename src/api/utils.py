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