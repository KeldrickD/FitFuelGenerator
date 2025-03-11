import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

def analyze_client_progress(client_id: int, progress_logs: List[Dict], exercise_progressions: List[Dict]) -> Dict:
    """
    Analyze client's progress data and generate AI-powered insights
    """
    try:
        # Analyze completion rate
        completion_rate = calculate_completion_rate(progress_logs)
        
        # Analyze exercise progression
        exercise_insights = analyze_exercise_progression(exercise_progressions)
        
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
        return {'rate': 0, 'trend': 'neutral'}
        
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

def analyze_exercise_progression(exercise_progressions: List[Dict]) -> Dict:
    """Analyze progression patterns for each exercise"""
    exercise_insights = {}
    
    for progression in exercise_progressions:
        exercise_name = progression['exercise_name']
        history = progression['progression_data']
        
        # Calculate improvement rate
        if history and len(history) > 1:
            initial_performance = history[0].get('performance', 0)
            current_performance = history[-1].get('performance', 0)
            improvement = ((current_performance - initial_performance) / initial_performance) * 100
            
            exercise_insights[exercise_name] = {
                'improvement_rate': round(improvement, 1),
                'current_level': progression['current_level'],
                'next_milestone': progression['next_milestone'],
                'trend': analyze_trend(history)
            }
    
    return exercise_insights

def calculate_performance_trends(progress_logs: List[Dict]) -> Dict:
    """Calculate overall performance trends from progress logs"""
    if not progress_logs:
        return {'trend': 'neutral', 'indicators': {}}
    
    # Group logs by week
    weekly_metrics = {}
    for log in progress_logs:
        log_date = datetime.fromisoformat(log['log_date'])
        week_key = log_date.strftime('%Y-%W')
        
        if week_key not in weekly_metrics:
            weekly_metrics[week_key] = []
        weekly_metrics[week_key].append(log['metrics'])
    
    # Calculate weekly averages and trends
    trends = {
        'intensity': analyze_metric_trend([metrics.get('intensity', 0) for metrics in weekly_metrics.values()]),
        'volume': analyze_metric_trend([metrics.get('volume', 0) for metrics in weekly_metrics.values()]),
        'consistency': analyze_metric_trend([metrics.get('consistency', 0) for metrics in weekly_metrics.values()])
    }
    
    return {
        'trend': 'improving' if sum(1 for t in trends.values() if t == 'improving') > 1 else 'neutral',
        'indicators': trends
    }

def generate_adaptive_recommendations(
    completion_rate: Dict,
    exercise_insights: Dict,
    performance_trends: Dict
) -> List[Dict]:
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
