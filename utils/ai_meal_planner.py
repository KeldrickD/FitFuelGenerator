"""
AI-powered meal plan generator using OpenAI API
"""
import os
import json
import logging
from typing import Dict, List
from datetime import datetime, timedelta
import openai
from models import DietaryPreference, MealPlan

openai.api_key = os.environ.get('OPENAI_API_KEY')

def generate_ai_meal_plan(
    client_preferences: DietaryPreference,
    duration_weeks: int = 1
) -> Dict:
    """
    Generate a personalized meal plan using OpenAI
    """
    try:
        # Construct the prompt based on client preferences
        prompt = _construct_meal_plan_prompt(client_preferences, duration_weeks)
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional nutritionist helping to create personalized meal plans."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        # Parse and structure the response
        meal_plan = _parse_meal_plan_response(response.choices[0].message.content)
        
        # Validate the meal plan structure
        if not _validate_meal_plan(meal_plan):
            raise ValueError("Generated meal plan has invalid structure")
            
        return meal_plan

    except Exception as e:
        logging.error(f"Error generating AI meal plan: {str(e)}")
        raise

def _construct_meal_plan_prompt(preferences: DietaryPreference, duration_weeks: int) -> str:
    """
    Construct a detailed prompt for the AI based on client preferences
    """
    prompt = f"""
Create a {duration_weeks}-week meal plan with the following requirements:

Diet Type: {preferences.diet_type}
Daily Calories: {preferences.calorie_target}
Meals per Day: {preferences.meal_count_per_day}
Meal Size: {preferences.meal_size_preference}

Dietary Restrictions:
- Excluded ingredients: {', '.join(preferences.excluded_ingredients)}
- Preferred ingredients: {', '.join(preferences.preferred_ingredients)}

Please provide a structured meal plan with:
1. Daily meal schedules
2. Recipes with ingredients and portions
3. Nutritional information per meal
4. Shopping list for each week
5. Meal prep suggestions

Format the response as a JSON structure with the following keys:
- weekly_plans (array of week objects)
- shopping_lists (array of weekly lists)
- meal_prep_tips (array of strings)
"""
    return prompt

def _parse_meal_plan_response(response_text: str) -> Dict:
    """
    Parse and structure the AI response into a usable meal plan format
    """
    try:
        # Extract JSON from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON found in response")
            
        plan_data = json.loads(response_text[json_start:json_end])
        
        # Structure the meal plan
        structured_plan = {
            'weekly_plans': plan_data.get('weekly_plans', []),
            'shopping_lists': plan_data.get('shopping_lists', []),
            'meal_prep_tips': plan_data.get('meal_prep_tips', [])
        }
        
        return structured_plan

    except json.JSONDecodeError as e:
        logging.error(f"Error parsing AI response: {str(e)}")
        # Attempt to structure non-JSON response
        return _structure_non_json_response(response_text)

def _structure_non_json_response(response_text: str) -> Dict:
    """
    Create a structured format from non-JSON response
    """
    # Split response into sections
    sections = response_text.split('\n\n')
    weekly_plans = []
    shopping_lists = []
    meal_prep_tips = []
    
    current_section = None
    for section in sections:
        if 'Week' in section:
            current_section = {'week': len(weekly_plans) + 1, 'meals': []}
            weekly_plans.append(current_section)
        elif 'Shopping List' in section:
            shopping_lists.append({'week': len(shopping_lists) + 1, 'items': section.split('\n')[1:]})
        elif 'Meal Prep Tips' in section:
            meal_prep_tips.extend(section.split('\n')[1:])
            
    return {
        'weekly_plans': weekly_plans,
        'shopping_lists': shopping_lists,
        'meal_prep_tips': meal_prep_tips
    }

def _validate_meal_plan(meal_plan: Dict) -> bool:
    """
    Validate the structure and content of the generated meal plan
    """
    required_keys = ['weekly_plans', 'shopping_lists', 'meal_prep_tips']
    if not all(key in meal_plan for key in required_keys):
        return False
        
    # Check if weekly plans exist and have required structure
    if not meal_plan['weekly_plans'] or not isinstance(meal_plan['weekly_plans'], list):
        return False
        
    # Validate shopping lists
    if not isinstance(meal_plan['shopping_lists'], list):
        return False
        
    return True
