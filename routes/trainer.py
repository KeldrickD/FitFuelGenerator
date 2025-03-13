from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import Client, ProgressLog, Goal, ActivityFeed, Plan, WorkoutLog, SharingAnalytics
from extensions import db
from datetime import datetime, timedelta
from utils.notifications import send_notification
import logging

trainer = Blueprint('trainer', __name__)

@trainer.route('/client/<int:client_id>/update-workout-completion', methods=['POST'])
@login_required
def update_workout_completion(client_id):
    """Update workout completion status for a client"""
    try:
        client = Client.query.filter_by(id=client_id, trainer_id=current_user.id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        data = request.get_json()
        log_date = datetime.strptime(data.get('log_date'), '%Y-%m-%d')
        completed = data.get('completed', False)

        # Check if a progress log exists for this date
        progress_log = ProgressLog.query.filter_by(
            client_id=client_id,
            log_date=log_date
        ).first()

        if progress_log:
            # Update existing log
            progress_log.workout_completed = completed
        else:
            # Create new log
            progress_log = ProgressLog(
                client_id=client_id,
                log_date=log_date,
                workout_completed=completed,
                notes=f"Workout completion updated by trainer: {'Completed' if completed else 'Not completed'}"
            )
            db.session.add(progress_log)

        # Create activity feed entry
        activity = ActivityFeed(
            client_id=client_id,
            activity_type='workout_status',
            description=f"Workout {'completed' if completed else 'marked as incomplete'} by trainer",
            priority='normal',
            icon='clipboard-check'
        )
        db.session.add(activity)

        # Send notification to client
        send_notification(
            client_id=client_id,
            notification_type='workout_status',
            message=f"Your trainer has marked your workout as {'completed' if completed else 'not completed'}"
        )

        db.session.commit()
        return jsonify({
            'message': 'Workout status updated successfully',
            'status': 'success'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@trainer.route('/client/<int:client_id>')
@login_required
def view_client(client_id):
    """View client details"""
    try:
        client = Client.query.filter_by(id=client_id, trainer_id=current_user.id).first()
        if not client:
            flash('Client not found', 'error')
            return redirect(url_for('trainer.dashboard'))

        # Get recent progress logs
        thirty_days_ago = datetime.now() - timedelta(days=30)
        progress_logs = ProgressLog.query.filter(
            ProgressLog.client_id == client_id,
            ProgressLog.created_at >= thirty_days_ago
        ).order_by(ProgressLog.created_at.desc()).all()

        # Calculate completion rate
        total_logs = len(progress_logs)
        completed_workouts = sum(1 for log in progress_logs if log.workout_completed)
        completion_rate = (completed_workouts / total_logs * 100) if total_logs > 0 else 0

        # Calculate current streak
        streak = 0
        current_date = datetime.now().date()
        completed_dates = {log.log_date.date() for log in progress_logs if log.workout_completed}
        
        while (current_date - timedelta(days=streak)) in completed_dates:
            streak += 1

        # Calculate weekly stats
        week_start = current_date - timedelta(days=current_date.weekday())
        weekly_logs = [log for log in progress_logs if log.log_date.date() >= week_start]
        weekly_total = len(weekly_logs)
        weekly_completed = sum(1 for log in weekly_logs if log.workout_completed)
        weekly_completion = (weekly_completed / weekly_total * 100) if weekly_total > 0 else 0

        # Get best streak
        best_streak = 0
        temp_streak = 0
        sorted_dates = sorted(completed_dates)
        
        for i in range(len(sorted_dates)):
            if i > 0 and (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                temp_streak += 1
            else:
                temp_streak = 1
            best_streak = max(best_streak, temp_streak)

        return render_template('view_client.html',
                             client=client,
                             progress_logs=progress_logs,
                             completion_rate=round(completion_rate, 1),
                             current_streak=streak,
                             best_streak=best_streak,
                             weekly_completion=round(weekly_completion, 1),
                             weekly_completed=weekly_completed,
                             weekly_total=weekly_total,
                             today_date=datetime.now().strftime('%Y-%m-%d'))

    except Exception as e:
        logging.error(f"Error viewing client: {str(e)}")
        flash('An error occurred while loading client data', 'error')
        return redirect(url_for('trainer.dashboard'))

@trainer.route('/sharing-analytics')
@login_required
def sharing_analytics():
    """View insights about what content clients are sharing."""
    # Get authenticated trainer
    current_trainer = get_current_trainer()
    
    # Get all clients for this trainer
    client_ids = [client.id for client in Client.query.filter_by(trainer_id=current_trainer.id).all()]
    
    if not client_ids:
        return render_template('trainer/sharing_analytics.html', 
                               analytics={},
                               platform_stats=[],
                               content_stats=[],
                               recent_shares=[],
                               client_shares=[])
    
    # Get sharing analytics for these clients
    shares = SharingAnalytics.query\
        .filter(SharingAnalytics.client_id.in_(client_ids))\
        .order_by(SharingAnalytics.timestamp.desc())\
        .all()
    
    # Calculate statistics
    total_shares = len(shares)
    platform_counts = {}
    content_type_counts = {}
    client_share_counts = {}
    
    for share in shares:
        # Count by platform
        platform = share.platform
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        # Count by content type
        content_type = share.content_type
        content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
        
        # Count by client
        client_id = share.client_id
        client_share_counts[client_id] = client_share_counts.get(client_id, 0) + 1
    
    # Prepare platform stats for chart
    platform_stats = [
        {
            'platform': platform.capitalize(),
            'count': count,
            'percentage': round((count / total_shares) * 100) if total_shares > 0 else 0
        } 
        for platform, count in platform_counts.items()
    ]
    platform_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # Prepare content type stats for chart
    content_stats = [
        {
            'type': content_type.replace('_', ' ').capitalize(),
            'count': count,
            'percentage': round((count / total_shares) * 100) if total_shares > 0 else 0
        } 
        for content_type, count in content_type_counts.items()
    ]
    content_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # Get client information for share counts
    client_shares = []
    clients = {client.id: client for client in Client.query.filter(Client.id.in_(client_share_counts.keys())).all()}
    
    for client_id, share_count in client_share_counts.items():
        if client_id in clients:
            client_shares.append({
                'client_id': client_id,
                'client_name': clients[client_id].name,
                'share_count': share_count,
                'percentage': round((share_count / total_shares) * 100) if total_shares > 0 else 0
            })
    
    client_shares.sort(key=lambda x: x['share_count'], reverse=True)
    
    # Get recent shares with client information
    recent_shares = []
    for share in shares[:20]:  # Limit to 20 most recent shares
        if share.client_id in clients:
            share_item = {
                'client_name': clients[share.client_id].name,
                'platform': share.platform.capitalize(),
                'content_type': share.content_type.replace('_', ' ').capitalize(),
                'timestamp': share.timestamp.strftime('%Y-%m-%d %H:%M'),
                'time_ago': get_time_ago(share.timestamp)
            }
            recent_shares.append(share_item)
    
    # Overall analytics
    analytics = {
        'total_shares': total_shares,
        'unique_clients': len(client_share_counts),
        'most_popular_platform': platform_stats[0]['platform'] if platform_stats else "None",
        'most_shared_content': content_stats[0]['type'] if content_stats else "None",
    }
    
    return render_template('trainer/sharing_analytics.html', 
                           analytics=analytics,
                           platform_stats=platform_stats,
                           content_stats=content_stats,
                           recent_shares=recent_shares,
                           client_shares=client_shares)

def get_time_ago(timestamp):
    """Convert timestamp to a human-readable 'time ago' format."""
    now = datetime.utcnow()
    diff = now - timestamp
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)} minutes ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)} hours ago"
    elif seconds < 604800:
        return f"{int(seconds // 86400)} days ago"
    else:
        return f"{int(seconds // 604800)} weeks ago" 