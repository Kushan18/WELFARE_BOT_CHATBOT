from typing import List, Dict, Any
from pymongo.collection import Collection
import re

def parse_income(income_str: str) -> int:
    """Parse income string like '2 Lakh' or '1-2.5 Lakh' to integer value in rupees."""
    if not income_str:
        return 0
    
    # Extract numeric values from the string
    numbers = re.findall(r'\d+\.?\d*', income_str)
    if not numbers:
        return 0
    
    # If it's a range like "1-2.5 Lakh", use the higher value
    if len(numbers) > 1:
        value = float(numbers[-1])  # Use the higher value
    else:
        value = float(numbers[0])
    
    # Convert to rupees (assuming input is in Lakhs)
    return int(value * 100000)

def calculate_scheme_confidence(user: Dict[str, Any], scheme: Dict[str, Any]) -> int:
    """Compute suitability score based on profile specificity."""
    score = 65  # Base match score
    rules = scheme.get("eligibility_rules", {})
    
    if rules.get("state") != "all" and user.get("state") == rules.get("state"):
         score += 10
    if rules.get("occupation") not in ["all", "any"] and user.get("occupation") == rules.get("occupation"):
         score += 10
    if rules.get("caste_category") != "all" and user.get("caste_category") == rules.get("caste_category"):
         score += 10
    if rules.get("gender") != "all" and user.get("gender") == rules.get("gender"):
         score += 5
         
    return min(100, score)

def match_schemes(user_profile: Dict[str, Any], schemes_collection: Collection) -> List[Dict[str, Any]]:
    """
    Takes user profile and returns matching schemes from MongoDB.
    Returns list of scheme documents that match ALL eligibility rules.
    """
    user = user_profile
    query: Dict[str, Any] = {
        "eligibility_rules.state": {"$in": [user.get("state"), "all"]},
    }

    # Add optional filters only if user has those fields
    if user.get("caste_category"):
        query["eligibility_rules.caste_category"] = {"$in": [user.get("caste_category"), "all"]}
    if user.get("occupation"):
        query["eligibility_rules.occupation"] = {"$in": [user.get("occupation"), "all", "any"]}
    if user.get("gender"):
        query["eligibility_rules.gender"] = {"$in": [user.get("gender"), "all"]}
    if user.get("income_bracket"):
        income_value = parse_income(user.get("income_bracket"))
        query["eligibility_rules.max_income"] = {"$gte": income_value}
    if user.get("age"):
        age = int(user.get("age"))
        query["eligibility_rules.min_age"] = {"$lte": age}
        query["eligibility_rules.max_age"] = {"$gte": age}

    matching = list(schemes_collection.find(query).limit(10))
    for m in matching:
        m["confidence_score"] = calculate_scheme_confidence(user, m)
        
    return matching
