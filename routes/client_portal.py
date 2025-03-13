from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import Client, ProgressLog, Goal, ActivityFeed, Plan, WorkoutLog
from extensions import db
import logging
from datetime import datetime, timedelta
from utils.notifications import send_notification

client_portal = Blueprint('client_portal', __name__, url_prefix='/client')

@client_portal.route('/login', methods=['GET', 'POST'])
def login():
    """Client login route"""
    if request.method == 'POST':
        email = request.form.get('email')
        access_code = request.form.get('access_code')

        if not all([email, access_code]):
            flash('Email and access code are required', 'error')
            return redirect(url_for('client_portal.login'))

        client = Client.query.filter_by(email=email).first()

        if client and check_password_hash(client.access_code_hash, access_code):
            login_user(client)
            return redirect(url_for('client_portal.dashboard'))
        
        flash('Invalid email or access code', 'error')
        return redirect(url_for('client_portal.login'))

    return render_template('client_portal/login.html')

@client_portal.route('/dashboard')
@login_required
def dashboard():
    """Client dashboard route"""
    try:
        # Get the last 30 days of progress logs
        thirty_days_ago = datetime.now() - timedelta(days=30)
        progress_logs = ProgressLog.query.filter(
            ProgressLog.client_id == current_user.id,
            ProgressLog.created_at >= thirty_days_ago
        ).order_by(ProgressLog.created_at.asc()).all()

        # Get workout logs for the same period to check completion
        workout_logs = WorkoutLog.query.filter(
            WorkoutLog.client_id == current_user.id,
            WorkoutLog.created_at >= thirty_days_ago
        ).all()

        # Create a set of dates with completed workouts
        completed_workout_dates = {
            log.created_at.strftime('%Y-%m-%d')
            for log in workout_logs
            if log.status == 'completed'
        }

        # Format progress logs for charts
        formatted_logs = []
        for log in progress_logs:
            log_date = log.created_at.strftime('%Y-%m-%d')
            formatted_logs.append({
                'log_date': log_date,
                'metrics': {
                    'weight': float(log.weight) if log.weight else None,
                    'body_fat': float(log.body_fat) if log.body_fat else None,
                    'energy_level': int(log.energy_level) if log.energy_level else None,
                    'sleep_quality': int(log.sleep_quality) if log.sleep_quality else None,
                    'mood': int(log.mood) if log.mood else None
                },
                'workout_completed': log_date in completed_workout_dates
            })

        # Get active goals
        active_goals = Goal.query.filter(
            Goal.client_id == current_user.id,
            Goal.status == 'active'
        ).all()

        return render_template('client_portal/dashboard.html',
                             progress_logs=formatted_logs,
                             active_goals=active_goals)

    except Exception as e:
        flash('Error loading dashboard data', 'error')
        return render_template('client_portal/dashboard.html',
                             progress_logs=[],
                             active_goals=[])

@client_portal.route('/progress/log', methods=['GET', 'POST'])
@login_required
def log_progress():
    """Log progress route"""
    if request.method == 'POST':
        try:
            # Create new progress log
            progress_log = ProgressLog(
                client_id=current_user.id,
                log_date=datetime.strptime(request.form.get('log_date'), '%Y-%m-%d'),
                workout_completed=request.form.get('workout_completed') == 'true',
                metrics={
                    'weight': float(request.form.get('weight', 0)),
                    'body_fat': float(request.form.get('body_fat', 0)),
                    'energy_level': int(request.form.get('energy_level', 0)),
                    'sleep_quality': int(request.form.get('sleep_quality', 0)),
                    'mood': int(request.form.get('mood', 0))
                },
                notes=request.form.get('notes')
            )

            # Add activity feed entry
            activity = ActivityFeed(
                client=current_user,
                activity_type='progress_log',
                description='New progress log added',
                priority='normal',
                icon='trending-up'
            )

            db.session.add(progress_log)
            db.session.add(activity)
            db.session.commit()

            flash('Progress logged successfully!', 'success')
            return redirect(url_for('client_portal.dashboard'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error logging progress: {str(e)}")
            flash('An error occurred while logging progress', 'error')
            return redirect(url_for('client_portal.log_progress'))

    return render_template(
        'client_portal/log_progress.html',
        today_date=datetime.now().strftime('%Y-%m-%d')
    )

@client_portal.route('/goals')
@login_required
def goals():
    """Goals overview route"""
    try:
        active_goals = Goal.query\
            .filter_by(client_id=current_user.id)\
            .order_by(Goal.created_at.desc())\
            .all()

        return render_template(
            'client_portal/goals.html',
            active_goals=active_goals
        )
    except Exception as e:
        logging.error(f"Error loading goals: {str(e)}")
        flash('An error occurred while loading your goals', 'error')
        return redirect(url_for('client_portal.dashboard'))

@client_portal.route('/plan')
@login_required
def view_plan():
    """View current plan route"""
    try:
        active_plan = Plan.query\
            .filter_by(
                client_id=current_user.id,
                status='active'
            ).first()

        if not active_plan:
            flash('No active plan found', 'info')
            return redirect(url_for('client_portal.dashboard'))

        return render_template(
            'client_portal/plan.html',
            plan=active_plan
        )
    except Exception as e:
        logging.error(f"Error loading plan: {str(e)}")
        flash('An error occurred while loading your plan', 'error')
        return redirect(url_for('client_portal.dashboard')) 