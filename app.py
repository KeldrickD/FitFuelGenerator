import os
import logging
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils import workout_generator, meal_generator, pdf_generator, progression_tracker
from models import db, Trainer, Client, Plan, ProgressLog, ExerciseProgression
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///fitfuel.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clients')
def clients_list():
    try:
        # For now, we'll show all clients since we haven't implemented authentication yet
        clients = Client.query.all()
        return render_template('clients.html', clients=clients)
    except Exception as e:
        logging.error(f"Error loading clients: {str(e)}")
        flash('Error loading client list. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/create_plan', methods=['GET', 'POST'])
def create_plan():
    if request.method == 'POST':
        try:
            client_data = {
                'name': request.form['client_name'],
                'goal': request.form['goal'],
                'fitness_level': request.form['fitness_level'],
                'diet_preference': request.form['diet_preference'],
                'weekly_budget': float(request.form['weekly_budget']),
                'training_days': int(request.form['training_days'])
            }

            # Generate workout and meal plans
            workout_plan = workout_generator.create_workout_plan(
                client_data['fitness_level'],
                client_data['training_days'],
                client_data['goal']
            )

            meal_plan = meal_generator.create_meal_plan(
                client_data['diet_preference'],
                client_data['weekly_budget']
            )

            # Store in session for preview
            session['current_plan'] = {
                'client_data': client_data,
                'workout_plan': workout_plan,
                'meal_plan': meal_plan
            }

            return redirect(url_for('preview_plan'))

        except Exception as e:
            logging.error(f"Error creating plan: {str(e)}")
            flash('Error creating plan. Please try again.', 'danger')
            return render_template('create_plan.html')

    return render_template('create_plan.html')

@app.route('/preview_plan')
def preview_plan():
    plan_data = session.get('current_plan')
    if not plan_data:
        flash('No plan data found. Please create a new plan.', 'warning')
        return redirect(url_for('create_plan'))

    return render_template('preview_plan.html', 
                         client_data=plan_data['client_data'],
                         workout_plan=plan_data['workout_plan'],
                         meal_plan=plan_data['meal_plan'])

@app.route('/generate_pdf')
def generate_pdf():
    plan_data = session.get('current_plan')
    if not plan_data:
        flash('No plan data found. Please create a new plan.', 'warning')
        return redirect(url_for('create_plan'))

    try:
        pdf_file = pdf_generator.generate_pdf(
            plan_data['client_data'],
            plan_data['workout_plan'],
            plan_data['meal_plan']
        )
        return pdf_file
    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        flash('Error generating PDF. Please try again.', 'danger')
        return redirect(url_for('preview_plan'))

@app.route('/client/<int:client_id>/progress')
def view_progress(client_id):
    try:
        client = Client.query.get_or_404(client_id)

        # Fetch progress logs and exercise progressions
        progress_logs = ProgressLog.query.filter_by(client_id=client_id).order_by(ProgressLog.log_date.desc()).all()
        exercise_progressions = ExerciseProgression.query.filter_by(client_id=client_id).all()

        # Convert to dictionary format for analysis
        logs_data = [
            {
                'log_date': log.log_date.isoformat(),
                'workout_completed': log.workout_completed,
                'exercise_data': log.exercise_data,
                'metrics': log.metrics
            }
            for log in progress_logs
        ]

        progression_data = [
            {
                'exercise_name': prog.exercise_name,
                'progression_data': prog.progression_data,
                'current_level': prog.current_level,
                'next_milestone': prog.next_milestone
            }
            for prog in exercise_progressions
        ]

        # Generate AI insights
        insights = progression_tracker.analyze_client_progress(
            client_id,
            logs_data,
            progression_data
        )

        return render_template(
            'progress.html',
            client=client,
            progress_logs=progress_logs,
            exercise_progressions=exercise_progressions,
            insights=insights
        )

    except Exception as e:
        logging.error(f"Error viewing progress: {str(e)}")
        flash('Error loading progress data. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/client/<int:client_id>/log-progress', methods=['POST'])
def log_progress():
    try:
        data = request.get_json()

        # Create new progress log
        progress_log = ProgressLog(
            client_id=data['client_id'],
            workout_completed=data['workout_completed'],
            exercise_data=data['exercise_data'],
            notes=data.get('notes', ''),
            metrics=data['metrics']
        )

        db.session.add(progress_log)

        # Update exercise progression
        for exercise in data['exercise_data']:
            progression = ExerciseProgression.query.filter_by(
                client_id=data['client_id'],
                exercise_name=exercise['name']
            ).first()

            if not progression:
                progression = ExerciseProgression(
                    client_id=data['client_id'],
                    exercise_name=exercise['name'],
                    progression_data=[],
                    current_level='beginner'
                )
                db.session.add(progression)

            # Update progression data
            progression.progression_data.append({
                'date': datetime.utcnow().isoformat(),
                'performance': exercise['performance'],
                'sets': exercise['sets'],
                'reps': exercise['reps']
            })

            progression.last_updated = datetime.utcnow()

        db.session.commit()

        return jsonify({'message': 'Progress logged successfully'}), 200

    except Exception as e:
        logging.error(f"Error logging progress: {str(e)}")
        return jsonify({'error': 'Failed to log progress'}), 500

@app.route('/dashboard')
def dashboard():
    try:
        # Get all clients
        clients = Client.query.all()

        # Calculate dashboard statistics
        total_clients = len(clients)

        # Calculate weekly workouts
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_workouts = ProgressLog.query.filter(
            ProgressLog.log_date >= one_week_ago,
            ProgressLog.workout_completed == True
        ).count()

        # Calculate improving clients percentage
        improving_clients = 0
        completion_rate = 0

        if total_clients > 0:
            for client in clients:
                # Get client's progress logs
                progress_logs = ProgressLog.query.filter_by(client_id=client.id).order_by(ProgressLog.log_date.desc()).all()
                logs_data = [
                    {
                        'log_date': log.log_date.isoformat(),
                        'workout_completed': log.workout_completed,
                        'exercise_data': log.exercise_data,
                        'metrics': log.metrics
                    }
                    for log in progress_logs
                ]

                if logs_data:
                    completion_rate += sum(1 for log in logs_data if log['workout_completed']) / len(logs_data)

                    # Get progression data
                    progression_data = [
                        {
                            'exercise_name': prog.exercise_name,
                            'progression_data': prog.progression_data,
                            'current_level': prog.current_level,
                            'next_milestone': prog.next_milestone
                        }
                        for prog in ExerciseProgression.query.filter_by(client_id=client.id).all()
                    ]

                    # Analyze progress
                    insights = progression_tracker.analyze_client_progress(
                        client.id,
                        logs_data,
                        progression_data
                    )

                    if insights['performance_trends']['trend'] == 'improving':
                        improving_clients += 1

            improving_clients = (improving_clients / total_clients) * 100
            completion_rate = (completion_rate / total_clients) * 100

        stats = {
            'total_clients': total_clients,
            'weekly_workouts': weekly_workouts,
            'improving_clients': round(improving_clients),
            'completion_rate': round(completion_rate)
        }

        # Get recent activities
        recent_activities = []
        recent_logs = ProgressLog.query.order_by(ProgressLog.log_date.desc()).limit(5).all()

        for log in recent_logs:
            client = Client.query.get(log.client_id)
            recent_activities.append({
                'client_name': client.name,
                'icon': 'activity',
                'description': 'Completed workout session' if log.workout_completed else 'Logged progress',
                'timestamp': log.log_date.strftime('%Y-%m-%d %H:%M')
            })

        # Add last activity to clients
        for client in clients:
            latest_log = ProgressLog.query.filter_by(client_id=client.id).order_by(ProgressLog.log_date.desc()).first()
            client.last_activity = latest_log.log_date.strftime('%Y-%m-%d %H:%M') if latest_log else None

            # Get client's trend
            progress_logs = ProgressLog.query.filter_by(client_id=client.id).order_by(ProgressLog.log_date.desc()).all()
            if progress_logs:
                logs_data = [
                    {
                        'log_date': log.log_date.isoformat(),
                        'workout_completed': log.workout_completed,
                        'exercise_data': log.exercise_data,
                        'metrics': log.metrics
                    }
                    for log in progress_logs
                ]
                insights = progression_tracker.analyze_client_progress(
                    client.id,
                    logs_data,
                    []  # Empty progression data as we only need overall trend
                )
                client.trend = insights['performance_trends']['trend']
            else:
                client.trend = 'neutral'

        return render_template('dashboard.html',
                             clients=clients,
                             stats=stats,
                             recent_activities=recent_activities)

    except Exception as e:
        logging.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard data. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/api/client/<int:client_id>')
def get_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        return jsonify({
            'id': client.id,
            'name': client.name,
            'goal': client.goal,
            'fitness_level': client.fitness_level
        })
    except Exception as e:
        logging.error(f"Error fetching client data: {str(e)}")
        return jsonify({'error': 'Failed to fetch client data'}), 500

@app.route('/api/client/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        data = request.get_json()

        client.name = data.get('name', client.name)
        client.goal = data.get('goal', client.goal)
        client.fitness_level = data.get('fitness_level', client.fitness_level)

        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error updating client: {str(e)}")
        return jsonify({'error': 'Failed to update client'}), 500

with app.app_context():
    db.create_all()