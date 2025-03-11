import logging
from typing import List, Dict

def create_workout_plan(fitness_level: str, training_days: int, goal: str) -> Dict:
    """
    Generate a workout plan based on client parameters
    """
    exercises = {
        'beginner': {
            'weight_loss': [
                {'name': 'Bodyweight Squats', 'sets': 2, 'reps': '10-12'},
                {'name': 'Push-ups (Modified)', 'sets': 2, 'reps': '5-10'},
                {'name': 'Walking Lunges', 'sets': 2, 'reps': '10 each leg'},
                {'name': 'Plank', 'sets': 2, 'reps': '20-30 seconds'}
            ],
            'muscle_gain': [
                {'name': 'Dumbbell Squats', 'sets': 3, 'reps': '8-10'},
                {'name': 'Assisted Pull-ups', 'sets': 2, 'reps': '5-8'},
                {'name': 'Dumbbell Bench Press', 'sets': 3, 'reps': '8-10'},
                {'name': 'Dumbbell Rows', 'sets': 3, 'reps': '8-10'}
            ]
        },
        'intermediate': {
            'weight_loss': [
                {'name': 'Jump Squats', 'sets': 3, 'reps': '15-20'},
                {'name': 'Push-ups', 'sets': 3, 'reps': '12-15'},
                {'name': 'Burpees', 'sets': 3, 'reps': '10-12'},
                {'name': 'Mountain Climbers', 'sets': 3, 'reps': '30 seconds'}
            ],
            'muscle_gain': [
                {'name': 'Barbell Squats', 'sets': 4, 'reps': '8-10'},
                {'name': 'Pull-ups', 'sets': 3, 'reps': '8-10'},
                {'name': 'Barbell Bench Press', 'sets': 4, 'reps': '8-10'},
                {'name': 'Barbell Rows', 'sets': 4, 'reps': '8-10'}
            ]
        }
    }

    try:
        # Select appropriate exercise set
        base_exercises = exercises.get(fitness_level, exercises['beginner']).get(goal, exercises['beginner']['weight_loss'])
        
        # Create workout schedule
        workout_schedule = {}
        rest_days = 7 - training_days
        current_day = 1
        
        for i in range(training_days):
            workout_schedule[f"Day {current_day}"] = {
                'exercises': base_exercises,
                'progression': f"Week 2: Increase sets by 1\nWeek 3: Increase reps by 2",
                'motivation': get_motivation_message()
            }
            current_day += 1
            
            # Add rest day if needed
            if rest_days > 0:
                workout_schedule[f"Day {current_day}"] = {
                    'exercises': 'Rest Day',
                    'motivation': 'Recovery is key to progress!'
                }
                current_day += 1
                rest_days -= 1
        
        return workout_schedule
        
    except Exception as e:
        logging.error(f"Error generating workout plan: {str(e)}")
        raise

def get_motivation_message() -> str:
    """Return a random motivation message"""
    messages = [
        "You're crushing it! Keep pushing!",
        "Every rep brings you closer to your goals!",
        "Stay strong, stay focused!",
        "You've got this! Make it count!"
    ]
    from random import choice
    return choice(messages)
