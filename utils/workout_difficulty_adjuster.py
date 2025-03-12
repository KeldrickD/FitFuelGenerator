import logging
from datetime import datetime
from typing import Dict, List, Optional

def analyze_performance_metrics(exercise_data: List[Dict]) -> Dict:
    """
    Analyze exercise performance metrics to determine if difficulty should be adjusted
    """
    try:
        if not exercise_data:
            return {'recommendation': 'maintain', 'confidence': 0}

        # Calculate performance trends
        completion_rate = sum(1 for entry in exercise_data if entry.get('completed', False)) / len(exercise_data)

        # Analyze progression in reps and weights
        progression_metrics = {
            'reps_trend': 0,
            'weight_trend': 0,
            'form_quality': 0
        }

        for i in range(1, len(exercise_data)):
            current = exercise_data[i]
            previous = exercise_data[i-1]

            # Compare reps
            if current.get('reps', 0) > previous.get('reps', 0):
                progression_metrics['reps_trend'] += 1

            # Compare weights/resistance
            if current.get('weight', 0) > previous.get('weight', 0):
                progression_metrics['weight_trend'] += 1

            # Consider form quality if available
            if current.get('form_rating', 0) > previous.get('form_rating', 0):
                progression_metrics['form_quality'] += 1

        # Calculate confidence score
        confidence = min((len(exercise_data) / 5) * 100, 100)  # More data = higher confidence

        # Determine adjustment recommendation
        if completion_rate >= 0.8 and all(metric > 0 for metric in progression_metrics.values()):
            return {
                'recommendation': 'increase',
                'confidence': confidence,
                'adjustment_factor': 1.15  # 15% increase
            }
        elif completion_rate < 0.6 or any(metric < -1 for metric in progression_metrics.values()):
            return {
                'recommendation': 'decrease',
                'confidence': confidence,
                'adjustment_factor': 0.85  # 15% decrease
            }
        else:
            return {
                'recommendation': 'maintain',
                'confidence': confidence,
                'adjustment_factor': 1.0
            }

    except Exception as e:
        logging.error(f"Error analyzing performance metrics: {str(e)}")
        return {'recommendation': 'maintain', 'confidence': 0}

def adjust_exercise_difficulty(
    exercise: Dict,
    performance_data: List[Dict],
    fitness_level: str
) -> Dict:
    """
    Adjust exercise difficulty based on performance analysis
    """
    try:
        # Analyze recent performance
        analysis = analyze_performance_metrics(performance_data)

        if analysis['confidence'] < 50:  # Not enough data for confident adjustment
            return exercise

        # Base difficulty multipliers
        difficulty_multipliers = {
            'beginner': {
                'increase': {'sets': 1, 'reps': 2, 'weight': 2.5},
                'decrease': {'sets': -1, 'reps': -2, 'weight': -2.5}
            },
            'intermediate': {
                'increase': {'sets': 1, 'reps': 3, 'weight': 5},
                'decrease': {'sets': -1, 'reps': -3, 'weight': -5}
            },
            'advanced': {
                'increase': {'sets': 2, 'reps': 4, 'weight': 7.5},
                'decrease': {'sets': -1, 'reps': -4, 'weight': -7.5}
            }
        }

        # Get appropriate multipliers based on fitness level
        multipliers = difficulty_multipliers.get(fitness_level, difficulty_multipliers['beginner'])

        if analysis['recommendation'] != 'maintain':
            direction = analysis['recommendation']

            # Adjust exercise parameters
            current_sets = int(exercise.get('sets', 3))
            current_reps = int(exercise.get('reps', 10))
            current_weight = float(exercise.get('weight', 0))

            # Apply adjustments
            if direction == 'increase':
                exercise['sets'] = min(current_sets + multipliers['increase']['sets'], 5)
                exercise['reps'] = min(current_reps + multipliers['increase']['reps'], 15)
                if current_weight > 0:
                    exercise['weight'] = current_weight + multipliers['increase']['weight']
            else:
                exercise['sets'] = max(current_sets + multipliers['decrease']['sets'], 2)
                exercise['reps'] = max(current_reps + multipliers['decrease']['reps'], 8)
                if current_weight > multipliers['decrease']['weight']:
                    exercise['weight'] = current_weight + multipliers['decrease']['weight']

            # Add adjustment metadata
            exercise['adjusted'] = True
            exercise['adjustment_type'] = direction
            exercise['adjustment_reason'] = f"Difficulty {direction}d based on performance analysis (confidence: {analysis['confidence']}%)"

        return exercise

    except Exception as e:
        logging.error(f"Error adjusting exercise difficulty: {str(e)}")
        return exercise

def get_difficulty_progression(fitness_level: str, exercise_type: str) -> Dict:
    """
    Get exercise progression guidelines based on fitness level and exercise type
    """
    progression_guidelines = {
        'beginner': {
            'strength': {
                'weight_increment': 2.5,
                'rep_increment': 1,
                'set_increment': 1,
                'rest_period': 90
            },
            'cardio': {
                'duration_increment': 2,
                'intensity_increment': 5,
                'rest_period': 60
            }
        },
        'intermediate': {
            'strength': {
                'weight_increment': 5,
                'rep_increment': 2,
                'set_increment': 1,
                'rest_period': 75
            },
            'cardio': {
                'duration_increment': 5,
                'intensity_increment': 7,
                'rest_period': 45
            }
        },
        'advanced': {
            'strength': {
                'weight_increment': 7.5,
                'rep_increment': 2,
                'set_increment': 2,
                'rest_period': 60
            },
            'cardio': {
                'duration_increment': 7,
                'intensity_increment': 10,
                'rest_period': 30
            }
        }
    }

    return progression_guidelines.get(fitness_level, {}).get(exercise_type, progression_guidelines['beginner']['strength'])