from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import current_app
from models import Trainer, Client, Goal, ProgressLog
from utils.email_service import send_subscription_reminder
from utils.notifications import notify_goal_achievement
import logging

scheduler = BackgroundScheduler()

def check_subscription_renewals():
    """Check for upcoming subscription renewals and send reminders"""
    try:
        # Find trainers whose subscriptions expire in the next 7 days
        expiry_threshold = datetime.utcnow() + timedelta(days=7)
        trainers = Trainer.query.filter(
            Trainer.subscription_end_date <= expiry_threshold,
            Trainer.subscription_end_date > datetime.utcnow(),
            Trainer.subscription_status == 'premium'
        ).all()

        for trainer in trainers:
            send_subscription_reminder(trainer)
            logging.info(f"Sent subscription reminder to trainer {trainer.id}")

    except Exception as e:
        logging.error(f"Error in subscription renewal check: {str(e)}")

def check_goal_progress():
    """Check client goal progress and send notifications"""
    try:
        # Find active goals
        active_goals = Goal.query.filter_by(status='in_progress').all()

        for goal in active_goals:
            client = Client.query.get(goal.client_id)
            if not client:
                continue

            # Check if goal is achieved
            if goal.current_value >= goal.target_value:
                goal.status = 'completed'
                goal.completion_date = datetime.utcnow()
                
                # Award points
                client.points += 100  # Base points for goal completion
                
                # Notify trainer
                notify_goal_achievement(client.id, goal.id)
                
                logging.info(f"Goal {goal.id} completed for client {client.id}")

    except Exception as e:
        logging.error(f"Error in goal progress check: {str(e)}")

def clean_old_logs():
    """Clean up old activity logs and temporary data"""
    try:
        # Delete logs older than 1 year
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        ProgressLog.query.filter(ProgressLog.log_date < cutoff_date).delete()
        
        logging.info("Cleaned up old progress logs")

    except Exception as e:
        logging.error(f"Error in log cleanup: {str(e)}")

def init_scheduler(app):
    """Initialize the scheduler with all jobs"""
    with app.app_context():
        # Check subscriptions daily at 9 AM
        scheduler.add_job(
            check_subscription_renewals,
            CronTrigger(hour=9),
            id='subscription_check',
            replace_existing=True
        )

        # Check goals every 6 hours
        scheduler.add_job(
            check_goal_progress,
            CronTrigger(hour='*/6'),
            id='goal_check',
            replace_existing=True
        )

        # Clean logs weekly on Sunday at 3 AM
        scheduler.add_job(
            clean_old_logs,
            CronTrigger(day_of_week='sun', hour=3),
            id='log_cleanup',
            replace_existing=True
        )

        # Start the scheduler
        scheduler.start()
        logging.info("Scheduler initialized with all jobs") 