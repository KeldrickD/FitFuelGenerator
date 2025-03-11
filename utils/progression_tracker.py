import logging
from datetime import datetime, timedelta
from typing import Dict, List
import json

def analyze_client_progress(client_id: int, progress_logs: List[Dict], exercise_progressions: List[Dict]) -> Dict:
    """
    Analyze client's progress data and generate AI-powered insights
    """
    try:
        # Analyze completion rate
        completion_rate = calculate_completion_rate(progress_logs)

        # Analyze exercise progression
        exercise_insights = {}
        for progression in exercise_progressions:
            exercise_name = progression['exercise_name']
            exercise_insights[exercise_name] = analyze_exercise_progression(progression)

        # Generate performance trends
        performance_trends = calculate_performance_trends(progress_logs)

        # Generate adaptive recommendations
        recommendations = generate_adaptive_recommendations(
            completion_rate,
            exercise_insights,
            performance_trends
        )

        return {
            'completion_rate': completion_rate,
            'exercise_insights': exercise_insights,
            'performance_trends': performance_trends,
            'recommendations': recommendations,
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logging.error(f"Error analyzing client progress: {str(e)}")
        raise

def calculate_completion_rate(progress_logs: List[Dict]) -> Dict:
    """Calculate workout completion rate and trends"""
    total_workouts = len(progress_logs)
    if total_workouts == 0:
        return {'rate': 0, 'trend': 'neutral', 'recent_rate': 0}

    completed = sum(1 for log in progress_logs if log.get('workout_completed', False))
    completion_rate = (completed / total_workouts) * 100

    # Calculate trend over last 4 weeks
    recent_logs = [log for log in progress_logs 
                  if datetime.fromisoformat(log['log_date']) > datetime.utcnow() - timedelta(weeks=4)]
    recent_rate = 0
    if recent_logs:
        recent_completed = sum(1 for log in recent_logs if log.get('workout_completed', False))
        recent_rate = (recent_completed / len(recent_logs)) * 100

    trend = 'improving' if recent_rate > completion_rate else 'declining' if recent_rate < completion_rate else 'stable'

    return {
        'rate': round(completion_rate, 1),
        'trend': trend,
        'recent_rate': round(recent_rate, 1)
    }

def analyze_exercise_progression(progression: Dict) -> Dict:
    """Analyze progression patterns for a single exercise"""
    history = progression.get('progression_data', [])
    current_level = progression.get('current_level', 'beginner')
    next_milestone = progression.get('next_milestone', {})

    if not history:
        return {
            'improvement_rate': 0,
            'current_level': current_level,
            'next_milestone': next_milestone,
            'trend': 'neutral'
        }

    # Calculate improvement rate
    initial_performance = history[0].get('performance', 0)
    current_performance = history[-1].get('performance', 0)

    if initial_performance > 0:
        improvement = ((current_performance - initial_performance) / initial_performance) * 100
    else:
        improvement = 0

    return {
        'improvement_rate': round(improvement, 1),
        'current_level': current_level,
        'next_milestone': next_milestone,
        'trend': analyze_trend(history)
    }

def calculate_performance_trends(progress_logs: List[Dict]) -> Dict:
    """Calculate overall performance trends from progress logs"""
    if not progress_logs:
        return {
            'trend': 'neutral',
            'indicators': {
                'intensity': 'neutral',
                'volume': 'neutral',
                'consistency': 'neutral'
            }
        }

    # Group logs by week
    weekly_metrics = {}
    for log in progress_logs:
        log_date = datetime.fromisoformat(log['log_date'])
        week_key = log_date.strftime('%Y-%W')

        metrics = log.get('metrics', {})
        if week_key not in weekly_metrics:
            weekly_metrics[week_key] = []
        weekly_metrics[week_key].append(metrics)

    # Calculate trends for each metric
    trends = {
        'intensity': analyze_metric_trend([sum(m.get('intensity', 0) for m in metrics) / len(metrics)
                                        for metrics in weekly_metrics.values()]),
        'volume': analyze_metric_trend([sum(m.get('volume', 0) for m in metrics) / len(metrics)
                                      for metrics in weekly_metrics.values()]),
        'consistency': analyze_metric_trend([sum(m.get('consistency', 0) for m in metrics) / len(metrics)
                                          for metrics in weekly_metrics.values()])
    }

    # Overall trend is improving if majority of indicators are improving
    improving_count = sum(1 for t in trends.values() if t == 'improving')
    overall_trend = 'improving' if improving_count > 1 else 'neutral'

    return {
        'trend': overall_trend,
        'indicators': trends
    }

def generate_adaptive_recommendations(completion_rate: Dict, exercise_insights: Dict, performance_trends: Dict) -> List[Dict]:
    """Generate personalized recommendations based on progress analysis"""
    recommendations = []

    # Completion rate based recommendations
    if completion_rate['rate'] < 70:
        recommendations.append({
            'type': 'motivation',
            'priority': 'high',
            'message': 'Focus on consistency. Try setting specific workout times in your calendar.'
        })

    # Exercise-specific recommendations
    for exercise, insight in exercise_insights.items():
        if insight['improvement_rate'] < 5:
            recommendations.append({
                'type': 'technique',
                'priority': 'medium',
                'message': f"Consider reviewing {exercise} technique or adjusting weight/resistance."
            })

    # Performance trend recommendations
    if performance_trends['trend'] == 'improving':
        recommendations.append({
            'type': 'progression',
            'priority': 'medium',
            'message': "Great progress! Consider increasing intensity on key exercises."
        })

    return recommendations

def analyze_trend(history: List[Dict]) -> str:
    """Analyze trend from historical data"""
    if len(history) < 2:
        return 'neutral'

    recent_values = [entry.get('performance', 0) for entry in history[-3:]]
    if all(recent_values[i] < recent_values[i+1] for i in range(len(recent_values)-1)):
        return 'improving'
    elif all(recent_values[i] > recent_values[i+1] for i in range(len(recent_values)-1)):
        return 'declining'
    return 'fluctuating'

def analyze_metric_trend(values: List[float]) -> str:
    """Analyze trend from metric values"""
    if len(values) < 2:
        return 'neutral'

    recent_values = values[-3:]
    if all(recent_values[i] < recent_values[i+1] for i in range(len(recent_values)-1)):
        return 'improving'
    elif all(recent_values[i] > recent_values[i+1] for i in range(len(recent_values)-1)):
        return 'declining'
    return 'neutral'