from extensions import socketio
from flask_login import current_user
from datetime import datetime

def send_notification(user_id, notification_type, message, data=None):
    """Send a real-time notification to a specific user"""
    notification = {
        'type': notification_type,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data or {}
    }
    socketio.emit(f'notification_{user_id}', notification, room=str(user_id))

def notify_client_update(client_id, update_type, message):
    """Send notification for client updates"""
    from models import Client
    client = Client.query.get(client_id)
    if client and client.trainer_id:
        send_notification(
            client.trainer_id,
            'client_update',
            message,
            {
                'client_id': client_id,
                'update_type': update_type,
                'client_name': client.name
            }
        )

def notify_goal_achievement(client_id, goal_id):
    """Send notification for goal achievements"""
    from models import Client, Goal
    client = Client.query.get(client_id)
    goal = Goal.query.get(goal_id)
    if client and client.trainer_id and goal:
        send_notification(
            client.trainer_id,
            'goal_achievement',
            f'{client.name} has achieved their goal: {goal.description}',
            {
                'client_id': client_id,
                'goal_id': goal_id,
                'goal_type': goal.goal_type
            }
        )

def notify_new_progress_log(client_id, log_id):
    """Send notification for new progress logs"""
    from models import Client, ProgressLog
    client = Client.query.get(client_id)
    log = ProgressLog.query.get(log_id)
    if client and client.trainer_id and log:
        send_notification(
            client.trainer_id,
            'progress_update',
            f'New progress log from {client.name}',
            {
                'client_id': client_id,
                'log_id': log_id,
                'log_date': log.log_date.isoformat()
            }
        ) 