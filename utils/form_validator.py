"""
Form validation utilities for the fitness management platform
"""
from typing import Dict, Any, List, Tuple
import re
from datetime import datetime

def validate_client_registration(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate client registration form data
    Returns: (is_valid: bool, errors: List[str])
    """
    errors = []
    
    # Required fields
    required_fields = ['name', 'email', 'fitness_level', 'goal']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Email validation
    if data.get('email'):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            errors.append("Please enter a valid email address")
    
    # Fitness level validation
    valid_levels = ['beginner', 'intermediate', 'advanced']
    if data.get('fitness_level') and data['fitness_level'] not in valid_levels:
        errors.append("Invalid fitness level selected")
    
    # Goal validation
    valid_goals = ['weight_loss', 'muscle_gain', 'endurance', 'flexibility', 'general_fitness']
    if data.get('goal') and data['goal'] not in valid_goals:
        errors.append("Invalid goal selected")
    
    return len(errors) == 0, errors

def validate_meal_plan_request(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate meal plan generation request data
    """
    errors = []
    
    # Required fields
    required_fields = ['diet_type', 'meal_count_per_day', 'calorie_target']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Numeric validation
    if data.get('meal_count_per_day'):
        try:
            meal_count = int(data['meal_count_per_day'])
            if not 2 <= meal_count <= 6:
                errors.append("Meal count must be between 2 and 6")
        except ValueError:
            errors.append("Meal count must be a number")
    
    if data.get('calorie_target'):
        try:
            calories = int(data['calorie_target'])
            if not 1200 <= calories <= 4000:
                errors.append("Calorie target must be between 1200 and 4000")
        except ValueError:
            errors.append("Calorie target must be a number")
    
    # Diet type validation
    valid_diet_types = ['balanced', 'high_protein', 'low_carb', 'vegan', 'vegetarian', 'keto']
    if data.get('diet_type') and data['diet_type'] not in valid_diet_types:
        errors.append("Invalid diet type selected")
    
    return len(errors) == 0, errors

def validate_workout_log(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate workout log submission
    """
    errors = []
    
    # Required fields
    if not data.get('exercise_data'):
        errors.append("Exercise data is required")
    
    # Validate exercise data structure
    if data.get('exercise_data'):
        for exercise in data['exercise_data']:
            if not isinstance(exercise, dict):
                errors.append("Invalid exercise data format")
                break
            
            required_exercise_fields = ['name', 'sets', 'reps']
            for field in required_exercise_fields:
                if field not in exercise:
                    errors.append(f"Exercise {field} is required")
            
            # Validate numeric fields
            try:
                if 'sets' in exercise and not 1 <= int(exercise['sets']) <= 10:
                    errors.append("Sets must be between 1 and 10")
                if 'reps' in exercise and not 1 <= int(exercise['reps']) <= 100:
                    errors.append("Reps must be between 1 and 100")
            except ValueError:
                errors.append("Sets and reps must be numbers")
    
    # Validate metrics if provided
    if data.get('metrics'):
        metrics = data['metrics']
        if 'weight' in metrics:
            try:
                weight = float(metrics['weight'])
                if not 30 <= weight <= 300:
                    errors.append("Weight must be between 30 and 300 kg")
            except ValueError:
                errors.append("Weight must be a number")
    
    return len(errors) == 0, errors

def validate_challenge_creation(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate challenge creation data
    """
    errors = []
    
    # Required fields
    required_fields = ['name', 'description', 'challenge_type', 'target_value', 'start_date', 'end_date']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Validate dates
    if data.get('start_date') and data.get('end_date'):
        try:
            start = datetime.strptime(data['start_date'], '%Y-%m-%d')
            end = datetime.strptime(data['end_date'], '%Y-%m-%d')
            if start >= end:
                errors.append("End date must be after start date")
            if (end - start).days > 90:
                errors.append("Challenge duration cannot exceed 90 days")
        except ValueError:
            errors.append("Invalid date format. Use YYYY-MM-DD")
    
    # Validate challenge type
    valid_types = ['workout', 'steps', 'weight_loss', 'distance', 'strength']
    if data.get('challenge_type') and data['challenge_type'] not in valid_types:
        errors.append("Invalid challenge type")
    
    # Validate target value
    if data.get('target_value'):
        try:
            target = float(data['target_value'])
            if target <= 0:
                errors.append("Target value must be greater than 0")
        except ValueError:
            errors.append("Target value must be a number")
    
    return len(errors) == 0, errors
