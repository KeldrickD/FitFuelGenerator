import logging
from typing import List, Dict
from datetime import datetime, timedelta

def analyze_client_preferences(progress_logs: List[Dict], goals: List[Dict]) -> Dict:
    """
    Analyze client's workout preferences and patterns
    """
    try:
        if not progress_logs:
            return {
                'preferred_types': ['strength'],  # Default to strength training
                'best_performance': [],
                'areas_of_improvement': [],
                'consistency_score': 0
            }

        # Analyze exercise types and performance
        exercise_performance = {}
        workout_days = set()
        
        for log in progress_logs:
            if log.get('workout_completed'):
                workout_days.add(log.get('log_date').strftime('%Y-%m-%d'))
                
                for exercise in log.get('exercise_data', []):
                    exercise_name = exercise.get('name')
                    exercise_type = exercise.get('type', 'strength')
                    
                    if exercise_name not in exercise_performance:
                        exercise_performance[exercise_name] = {
                            'type': exercise_type,
                            'total_volume': 0,
                            'completion_rate': 0,
                            'performance_score': 0,
                            'count': 0
                        }
                    
                    perf = exercise_performance[exercise_name]
                    perf['count'] += 1
                    perf['total_volume'] += (
                        exercise.get('sets', 0) * 
                        exercise.get('reps', 0) * 
                        exercise.get('weight', 1)
                    )
                    perf['completion_rate'] += 1
                    perf['performance_score'] += exercise.get('form_rating', 7)

        # Calculate averages and identify preferences
        for exercise, stats in exercise_performance.items():
            stats['completion_rate'] = (stats['completion_rate'] / stats['count']) * 100
            stats['performance_score'] = stats['performance_score'] / stats['count']

        # Sort exercises by performance
        sorted_exercises = sorted(
            exercise_performance.items(),
            key=lambda x: (x[1]['completion_rate'], x[1]['performance_score']),
            reverse=True
        )

        # Identify preferred exercise types
        preferred_types = list(set(stats['type'] for _, stats in sorted_exercises[:3]))
        
        # Calculate consistency score (0-100)
        days_tracked = len(workout_days)
        days_total = (max(workout_days) - min(workout_days)).days + 1 if workout_days else 30
        consistency_score = min((days_tracked / days_total) * 100, 100)

        return {
            'preferred_types': preferred_types,
            'best_performance': [
                {'name': name, 'stats': stats}
                for name, stats in sorted_exercises[:3]
            ],
            'areas_of_improvement': [
                {'name': name, 'stats': stats}
                for name, stats in sorted_exercises[-3:]
            ],
            'consistency_score': consistency_score
        }

    except Exception as e:
        logging.error(f"Error analyzing client preferences: {str(e)}")
        return {
            'preferred_types': ['strength'],
            'best_performance': [],
            'areas_of_improvement': [],
            'consistency_score': 0
        }

def generate_workout_recommendations(
    client_data: Dict,
    progress_logs: List[Dict],
    goals: List[Dict]
) -> Dict:
    """
    Generate personalized workout recommendations based on client data and goals
    """
    try:
        # Analyze client preferences and patterns
        preferences = analyze_client_preferences(progress_logs, goals)
        
        # Define exercise focus based on goals
        goal_focus = {
            'weight_loss': {
                'primary': ['cardio', 'hiit'],
                'secondary': ['strength'],
                'intensity': 'moderate-high',
                'rest': '30-45 seconds'
            },
            'muscle_gain': {
                'primary': ['strength'],
                'secondary': ['hypertrophy'],
                'intensity': 'high',
                'rest': '60-90 seconds'
            },
            'endurance': {
                'primary': ['cardio', 'circuit'],
                'secondary': ['strength'],
                'intensity': 'moderate',
                'rest': '15-30 seconds'
            },
            'strength': {
                'primary': ['strength', 'power'],
                'secondary': ['hypertrophy'],
                'intensity': 'high',
                'rest': '90-120 seconds'
            }
        }

        # Get focus areas based on primary goal
        primary_goal = client_data.get('goal', 'strength')
        focus = goal_focus.get(primary_goal, goal_focus['strength'])

        # Generate recommendations
        recommendations = {
            'workout_focus': {
                'primary_types': focus['primary'],
                'secondary_types': focus['secondary'],
                'intensity_range': focus['intensity'],
                'rest_periods': focus['rest']
            },
            'suggested_exercises': [],
            'schedule_adjustments': [],
            'progression_path': []
        }

        # Add exercise recommendations based on preferences and goals
        if preferences['best_performance']:
            # Include successful exercises
            recommendations['suggested_exercises'].extend([
                {
                    'name': perf['name'],
                    'type': perf['stats']['type'],
                    'reason': 'Strong performance history'
                }
                for perf in preferences['best_performance']
                if perf['stats']['type'] in focus['primary'] + focus['secondary']
            ])

        # Add schedule recommendations based on consistency
        if preferences['consistency_score'] < 60:
            recommendations['schedule_adjustments'].append({
                'type': 'frequency',
                'suggestion': 'Start with 3 workouts per week to build consistency',
                'priority': 'high'
            })
        elif preferences['consistency_score'] > 80:
            recommendations['schedule_adjustments'].append({
                'type': 'intensity',
                'suggestion': 'Consider increasing workout frequency or intensity',
                'priority': 'medium'
            })

        # Generate progression path
        current_level = client_data.get('fitness_level', 'beginner')
        recommendations['progression_path'] = generate_progression_path(
            current_level,
            primary_goal,
            preferences['consistency_score']
        )

        return recommendations

    except Exception as e:
        logging.error(f"Error generating workout recommendations: {str(e)}")
        return {
            'workout_focus': {},
            'suggested_exercises': [],
            'schedule_adjustments': [],
            'progression_path': []
        }

def generate_progression_path(
    current_level: str,
    goal: str,
    consistency_score: float
) -> List[Dict]:
    """
    Generate a progression path based on current level and goals
    """
    levels = ['beginner', 'intermediate', 'advanced']
    current_index = levels.index(current_level) if current_level in levels else 0
    
    progression_path = []
    timeframes = ['2 weeks', '1 month', '2 months']
    
    for i, timeframe in enumerate(timeframes):
        milestone = {
            'timeframe': timeframe,
            'focus_areas': [],
            'target_metrics': {}
        }
        
        if goal == 'weight_loss':
            milestone['focus_areas'] = ['Increase cardio intensity', 'Add resistance training']
            milestone['target_metrics'] = {
                'cardio_duration': f"{20 + (i * 10)} minutes",
                'intensity': f"{65 + (i * 5)}% max heart rate"
            }
        elif goal == 'muscle_gain':
            milestone['focus_areas'] = ['Progressive overload', 'Form refinement']
            milestone['target_metrics'] = {
                'weight_increase': f"{5 + (i * 2.5)}%",
                'sets_per_muscle': f"{9 + (i * 3)} sets/week"
            }
        elif goal == 'strength':
            milestone['focus_areas'] = ['Compound movements', 'Progressive overload']
            milestone['target_metrics'] = {
                'strength_increase': f"{10 + (i * 5)}%",
                'working_sets': f"{3 + i} sets"
            }
        
        progression_path.append(milestone)
    
    return progression_path
