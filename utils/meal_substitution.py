"""
Meal Substitution System for FitFuel
Handles ingredient substitutions based on dietary preferences, allergies, and nutritional requirements
"""

import logging
from typing import List, Dict, Optional
from models import MealIngredient, SubstitutionRule

def find_substitutes(
    ingredient_name: str,
    client_preferences: Dict,
    allergies: List[str] = None,
    budget_constraint: Optional[float] = None
) -> List[Dict]:
    """
    Find suitable substitutes for an ingredient based on client preferences and constraints
    """
    try:
        # Get the original ingredient
        original = MealIngredient.query.filter_by(name=ingredient_name).first()
        if not original:
            logging.warning(f"Ingredient not found: {ingredient_name}")
            return []

        # Get all possible substitutes
        substitution_rules = SubstitutionRule.query.filter_by(ingredient_id=original.id).all()
        
        suitable_substitutes = []
        for rule in substitution_rules:
            substitute = MealIngredient.query.get(rule.substitute_id)
            
            # Check for allergens
            if allergies and any(allergen in substitute.common_allergens for allergen in allergies):
                continue
                
            # Check budget constraint
            if budget_constraint and substitute.estimated_cost > budget_constraint:
                continue
                
            # Calculate match score based on preferences
            preference_score = calculate_preference_match(
                substitute,
                rule,
                client_preferences
            )
            
            if preference_score > 0:
                suitable_substitutes.append({
                    'ingredient': substitute.name,
                    'conversion_ratio': rule.conversion_ratio,
                    'nutrition_difference': rule.nutrition_difference,
                    'cost_difference': rule.cost_difference,
                    'suitability_score': preference_score,
                    'preference_tags': rule.preference_tags
                })
        
        # Sort by suitability score
        return sorted(suitable_substitutes, key=lambda x: x['suitability_score'], reverse=True)
        
    except Exception as e:
        logging.error(f"Error finding substitutes: {str(e)}")
        return []

def calculate_preference_match(
    substitute: MealIngredient,
    rule: SubstitutionRule,
    preferences: Dict
) -> float:
    """
    Calculate how well a substitute matches client preferences
    Returns a score between 0 and 1
    """
    score = rule.suitability_score
    
    # Adjust score based on dietary preferences
    if preferences.get('diet_type'):
        if preferences['diet_type'] in rule.preference_tags:
            score *= 1.2
        elif f"not_{preferences['diet_type']}" in rule.preference_tags:
            score *= 0.5
            
    # Adjust for cost sensitivity
    if preferences.get('budget_conscious') and rule.cost_difference > 0:
        score *= (1 - min(rule.cost_difference / substitute.estimated_cost, 0.5))
        
    # Adjust for nutrition goals
    if preferences.get('nutrition_focus'):
        nutrition_impact = sum(
            abs(diff) for diff in rule.nutrition_difference.values()
        ) / len(rule.nutrition_difference)
        score *= (1 - min(nutrition_impact, 0.5))
    
    return max(min(score, 1.0), 0.0)

def validate_substitution(
    original: str,
    substitute: str,
    amount: float
) -> Dict:
    """
    Validate if a substitution is nutritionally appropriate
    Returns validation result with any warnings
    """
    try:
        orig = MealIngredient.query.filter_by(name=original).first()
        sub = MealIngredient.query.filter_by(name=substitute).first()
        
        if not orig or not sub:
            return {
                'valid': False,
                'message': 'One or both ingredients not found'
            }
            
        rule = SubstitutionRule.query.filter_by(
            ingredient_id=orig.id,
            substitute_id=sub.id
        ).first()
        
        if not rule:
            return {
                'valid': False,
                'message': 'No substitution rule found for these ingredients'
            }
            
        warnings = []
        
        # Check nutritional impact
        for nutrient, difference in rule.nutrition_difference.items():
            if abs(difference) > 0.3:  # 30% difference threshold
                warnings.append(f"Significant {nutrient} content difference")
                
        # Check cost impact
        if rule.cost_difference > orig.estimated_cost * 0.5:  # 50% cost increase threshold
            warnings.append("Significant cost increase with this substitution")
            
        return {
            'valid': True,
            'conversion_amount': amount * rule.conversion_ratio,
            'warnings': warnings,
            'nutrition_impact': rule.nutrition_difference,
            'cost_impact': rule.cost_difference
        }
        
    except Exception as e:
        logging.error(f"Error validating substitution: {str(e)}")
        return {
            'valid': False,
            'message': 'Error validating substitution'
        }
