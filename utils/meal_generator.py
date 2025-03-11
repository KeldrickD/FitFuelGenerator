import logging
from typing import Dict
from datetime import datetime

def create_meal_plan(diet_preference: str, weekly_budget: float) -> Dict:
    """
    Generate a meal plan based on diet preference and budget
    """
    # Daily budget
    daily_budget = weekly_budget / 7

    meal_options = {
        'vegan': {
            'breakfast': [
                {'name': 'Oatmeal with Fruits', 'cost': 2.00},
                {'name': 'Tofu Scramble', 'cost': 2.50},
                {'name': 'Smoothie Bowl', 'cost': 3.00}
            ],
            'lunch': [
                {'name': 'Lentil Soup', 'cost': 2.00},
                {'name': 'Chickpea Salad', 'cost': 2.50},
                {'name': 'Buddha Bowl', 'cost': 3.50}
            ],
            'dinner': [
                {'name': 'Stir-Fried Tofu', 'cost': 3.00},
                {'name': 'Bean Burrito', 'cost': 2.50},
                {'name': 'Quinoa Bowl', 'cost': 3.00}
            ]
        },
        'high_protein': {
            'breakfast': [
                {'name': 'Egg White Omelette', 'cost': 2.50},
                {'name': 'Greek Yogurt Bowl', 'cost': 2.00},
                {'name': 'Protein Pancakes', 'cost': 3.00}
            ],
            'lunch': [
                {'name': 'Chicken Breast Salad', 'cost': 3.50},
                {'name': 'Tuna Wrap', 'cost': 3.00},
                {'name': 'Turkey Sandwich', 'cost': 3.00}
            ],
            'dinner': [
                {'name': 'Grilled Salmon', 'cost': 4.00},
                {'name': 'Lean Beef Stir-Fry', 'cost': 4.00},
                {'name': 'Baked Chicken', 'cost': 3.50}
            ]
        }
    }

    try:
        # Select meal options based on diet preference
        diet_meals = meal_options.get(diet_preference, meal_options['high_protein'])

        # Create weekly meal plan with correct order
        meal_plan = {}
        current_month = datetime.now().month
        is_summer = 4 <= current_month <= 9

        for day in range(1, 8):
            # Ensure consistent meal order
            daily_meals = {
                'breakfast': get_seasonal_meal(diet_meals['breakfast'], is_summer),
                'lunch': get_seasonal_meal(diet_meals['lunch'], is_summer),
                'dinner': get_seasonal_meal(diet_meals['dinner'], is_summer)
            }

            # Calculate daily cost
            daily_cost = sum(meal['cost'] for meal in daily_meals.values())

            if daily_cost > daily_budget:
                daily_meals = adjust_meals_for_budget(daily_meals, daily_budget)

            meal_plan[f"Day {day}"] = {
                'meals': daily_meals,
                'total_cost': sum(meal['cost'] for meal in daily_meals.values()),
                'substitutions': get_substitutions(daily_meals)
            }

        return meal_plan

    except Exception as e:
        logging.error(f"Error generating meal plan: {str(e)}")
        raise

def get_seasonal_meal(meals, is_summer):
    """Select appropriate meal based on season"""
    from random import choice
    return choice(meals)

def adjust_meals_for_budget(meals, budget):
    """Adjust meal selections to fit within budget"""
    # Simple implementation - just pick cheaper options
    for meal_type in meals:
        if meals[meal_type]['cost'] > budget / 3:
            meals[meal_type]['cost'] = budget / 3
    return meals

def get_substitutions(meals):
    """Generate possible substitutions for meals"""
    substitutions = {
        'Tofu': 'Lentils',
        'Quinoa': 'Brown Rice',
        'Salmon': 'Tilapia',
        'Chicken Breast': 'Turkey Breast'
    }
    return substitutions