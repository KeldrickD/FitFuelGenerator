from flask import current_app, render_template_string
from flask_mail import Mail, Message
from threading import Thread

mail = Mail()

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipient, template, **kwargs):
    """Send an email using a template"""
    msg = Message(
        subject,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[recipient]
    )
    msg.html = render_template_string(template, **kwargs)
    
    # Send email asynchronously
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()

def send_welcome_email(trainer):
    """Send welcome email to new trainer"""
    template = """
    <h1>Welcome to FitFuel!</h1>
    <p>Hi {{ trainer.username }},</p>
    <p>Welcome to FitFuel - your new fitness management platform. We're excited to help you grow your business and achieve success with your clients.</p>
    <p>Here are some quick links to get started:</p>
    <ul>
        <li><a href="{{ url_for('dashboard', _external=True) }}">Your Dashboard</a></li>
        <li><a href="{{ url_for('add_client', _external=True) }}">Add Your First Client</a></li>
        <li><a href="{{ url_for('resource_library', _external=True) }}">Resource Library</a></li>
    </ul>
    <p>If you need any help, don't hesitate to reach out to our support team.</p>
    <p>Best regards,<br>The FitFuel Team</p>
    """
    send_email(
        'Welcome to FitFuel!',
        trainer.email,
        template,
        trainer=trainer
    )

def send_client_progress_notification(trainer, client, progress_log):
    """Send email notification about client progress"""
    template = """
    <h2>New Progress Update from {{ client.name }}</h2>
    <p>Hi {{ trainer.username }},</p>
    <p>{{ client.name }} has logged new progress:</p>
    <ul>
        <li>Date: {{ progress_log.log_date.strftime('%Y-%m-%d') }}</li>
        {% if progress_log.workout_completed %}
        <li>Workout Completed ✅</li>
        {% endif %}
        {% if progress_log.metrics %}
        <li>Metrics Updated:
            <ul>
                {% for key, value in progress_log.metrics.items() %}
                <li>{{ key }}: {{ value }}</li>
                {% endfor %}
            </ul>
        </li>
        {% endif %}
    </ul>
    <p><a href="{{ url_for('view_client', client_id=client.id, _external=True) }}">View Full Details</a></p>
    """
    send_email(
        f'New Progress Update - {client.name}',
        trainer.email,
        template,
        trainer=trainer,
        client=client,
        progress_log=progress_log
    )

def send_goal_achievement_notification(trainer, client, goal):
    """Send email notification about goal achievement"""
    template = """
    <h2>🎉 Goal Achievement Alert!</h2>
    <p>Hi {{ trainer.username }},</p>
    <p>Great news! {{ client.name }} has achieved their goal:</p>
    <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px;">
        <h3>{{ goal.goal_type|title }} Goal</h3>
        <p>{{ goal.description }}</p>
        <p>Target: {{ goal.target_value }}</p>
        <p>Achieved on: {{ goal.target_date.strftime('%Y-%m-%d') }}</p>
    </div>
    <p><a href="{{ url_for('view_client', client_id=client.id, _external=True) }}">View Client Profile</a></p>
    """
    send_email(
        f'Goal Achieved! - {client.name}',
        trainer.email,
        template,
        trainer=trainer,
        client=client,
        goal=goal
    )

def send_subscription_reminder(trainer):
    """Send subscription renewal reminder"""
    template = """
    <h2>Subscription Reminder</h2>
    <p>Hi {{ trainer.username }},</p>
    <p>Your FitFuel subscription will expire on {{ trainer.subscription_end_date.strftime('%Y-%m-%d') }}.</p>
    <p>To ensure uninterrupted access to all features, please renew your subscription.</p>
    <p><a href="{{ url_for('subscription', _external=True) }}">Manage Subscription</a></p>
    """
    send_email(
        'Subscription Renewal Reminder',
        trainer.email,
        template,
        trainer=trainer
    ) 