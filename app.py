import os
import logging
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, send_file
from extensions import db
from models import (
    Trainer, Client, Plan, ProgressLog, ExerciseProgression,
    MealIngredient, SubstitutionRule, DietaryPreference, MealPlan,
    ActivityFeed, Goal, GoalMilestone, Achievement, ClientAchievement,
    FitnessResource, GoalProgress, Challenge, ChallengeParticipant,
    LeaderboardEntry
)
from utils import (
    progression_tracker, workout_recommender, meal_generator,
    workout_generator, meal_substitution, pdf_generator
)
from utils.ai_meal_planner import generate_ai_meal_plan
from utils.form_validator import (
    validate_client_registration,
    validate_meal_plan_request,
    validate_workout_log,
    validate_challenge_creation
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure the database 
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

def create_sample_resources():
    """Create initial sample resources if none exist"""
    try:
        # Check if we already have resources
        if FitnessResource.query.first():
            return

        # Sample resources
        resources = [
            {
                'title': 'Beginner Full Body Workout',
                'description': 'A comprehensive workout routine perfect for beginners, covering all major muscle groups.',
                'resource_type': 'video',
                'content_url': 'https://www.youtube.com/embed/UoC_O3HzsH0',
                'difficulty_level': 'beginner',
                'categories': ['full body', 'strength', 'beginner'],
                'thumbnail_url': '/static/img/workouts/full-body.svg'
            },
            {
                'title': 'Nutrition Guide for Muscle Gain',
                'description': 'Learn about proper nutrition timing, macronutrient ratios, and meal planning for muscle growth.',
                'resource_type': 'guide',
                'content': '''
                    <h3>Key Principles of Muscle Gain Nutrition</h3>
                    <ul>
                        <li>Maintain a caloric surplus</li>
                        <li>Consume adequate protein (1.6-2.2g/kg body weight)</li>
                        <li>Time your meals around workouts</li>
                        <li>Include all macronutrients in your diet</li>
                    </ul>
                    <h3>Sample Meal Plan</h3>
                    <p>Here's a basic template for your daily meals...</p>
                ''',
                'difficulty_level': 'intermediate',
                'categories': ['nutrition', 'muscle gain', 'meal planning']
            },
            {
                'title': 'HIIT Cardio Workout',
                'description': 'High-intensity interval training for maximum fat burn and cardiovascular fitness.',
                'resource_type': 'video',
                'content_url': 'https://www.youtube.com/embed/ml6cT4AZdqI',
                'difficulty_level': 'advanced',
                'categories': ['cardio', 'fat loss', 'hiit'],
                'thumbnail_url': '/static/img/workouts/hiit.svg'
            }
        ]

        # Add resources to database
        for resource_data in resources:
            resource = FitnessResource(**resource_data)
            db.session.add(resource)

        db.session.commit()
        logging.info("Sample resources created successfully")

    except Exception as e:
        logging.error(f"Error creating sample resources: {str(e)}")
        db.session.rollback()



def create_sample_achievements():
    """Create initial sample achievements if none exist"""
    try:
        # Check if we already have achievements
        if Achievement.query.first():
            return

        # Sample achievements
        achievements = [
            {
                'name': 'Workout Warrior',
                'description': 'Complete 10 workouts in a month',
                'type': 'workout',
                'criteria': {'workout_count': 10},
                'icon': 'activity',
                'level': 'bronze',
                'points': 100,
                'difficulty': 1
            },
            {
                'name': 'Nutrition Master',
                'description': 'Log all meals for 30 consecutive days',
                'type': 'nutrition',
                'criteria': {'meal_streak': 30},
                'icon': 'coffee',
                'level': 'gold',
                'points': 300,
                'difficulty': 3
            },
            {
                'name': 'Goal Getter',
                'description': 'Achieve your first fitness goal',
                'type': 'goals',
                'criteria': {'goals_completed': 1},
                'icon': 'target',
                'level': 'silver',
                'points': 200,
                'difficulty': 2
            }
        ]

        # Add achievements to database
        for achievement_data in achievements:
            achievement = Achievement(**achievement_data)
            db.session.add(achievement)

        db.session.commit()
        logging.info("Sample achievements created successfully")

    except Exception as e:
        logging.error(f"Error creating sample achievements: {str(e)}")
        db.session.rollback()

def create_sample_client_achievements(client_id):
    """Create sample client achievements for testing"""
    try:
        # Check if client already has achievements
        if ClientAchievement.query.filter_by(client_id=client_id).first():
            return

        # Get all achievements
        achievements = Achievement.query.all()

        # Create progress data for each achievement
        for achievement in achievements:
            # Different progress states for testing animations
            if achievement.type == 'workout':
                progress = 75  # In progress
                completed = False
                earned_at = None
            elif achievement.type == 'nutrition':
                progress = 100  # Completed
                completed = True
                earned_at = datetime.utcnow()
            else:
                progress = 30  # Just started
                completed = False
                earned_at = None

            client_achievement = ClientAchievement(
                client_id=client_id,
                achievement_id=achievement.id,
                progress=progress,
                completed=completed,
                earned_at=earned_at
            )
            db.session.add(client_achievement)

        db.session.commit()
        logging.info(f"Sample client achievements created for client {client_id}")

    except Exception as e:
        logging.error(f"Error creating sample client achievements: {str(e)}")
        db.session.rollback()

# Add this to the create_sample_resources function
def create_sample_client():
    """Create a sample client with workout history if none exists"""
    try:
        # Check if we already have clients
        if Client.query.first():
            return

        # Create sample client
        client = Client(
            name="John Smith",
            fitness_level="intermediate",
            goal="muscle_gain",
            diet_preference="balanced",
            trainer_id=1  # Default trainer ID
        )
        db.session.add(client)
        db.session.flush()  # Get client.id

        # Create sample workout history
        for i in range(5):  # Last 5 days of workouts
            log = ProgressLog(
                client_id=client.id,
                log_date=datetime.utcnow() - timedelta(days=i),
                workout_completed=True,
                exercise_data=[
                    {
                        'name': 'Barbell Squats',
                        'sets': 4,
                        'reps': 10,
                        'weight': 95,
                        'type': 'strength'
                    },
                    {
                        'name': 'Push-ups',
                        'sets': 3,
                        'reps': 15,
                        'type': 'strength'
                    }
                ],
                metrics={
                    'intensity': 8,
                    'volume': 120,
                    'consistency': 1
                }
            )
            db.session.add(log)

        db.session.commit()
        logging.info(f"Created sample client with ID: {client.id}")

    except Exception as e:
        logging.error(f"Error creating sample client: {str(e)}")
        db.session.rollback()


# Add after the existing sample data functions

def create_sample_data():
    """Create comprehensive sample data for testing and demonstration"""
    try:
        # Only create sample data if no existing data
        if Trainer.query.first() or Client.query.first():
            return

        logging.info("Creating sample data for new deployment")

        # Create sample trainer
        trainer = Trainer(
            username="coach_mike",
            email="mike@fitcoach.com",
            business_name="Elite Fitness Training",
            password_hash="dummy_hash"  # In production, use proper password hashing
        )
        db.session.add(trainer)
        db.session.flush()

        # Create diverse client profiles
        client_profiles = [
            {
                'name': 'Sarah Johnson',
                'fitness_level': 'beginner',
                'goal': 'weight_loss',
                'diet_preference': 'balanced',
                'allergies': ['nuts']
            },
            {
                'name': 'James Smith',
                'fitness_level': 'intermediate',
                'goal': 'muscle_gain',
                'diet_preference': 'high_protein',
                'allergies': []
            },
            {
                'name': 'Emily Chen',
                'fitness_level': 'advanced',
                'goal': 'endurance',
                'diet_preference': 'vegan',
                'allergies': ['dairy']
            }
        ]

        for profile in client_profiles:
            client = Client(
                name=profile['name'],
                trainer_id=trainer.id,
                fitness_level=profile['fitness_level'],
                goal=profile['goal'],
                diet_preference=profile['diet_preference'],
                allergies=profile['allergies']
            )
            db.session.add(client)
            db.session.flush()

            # Create dietary preferences
            diet_pref = DietaryPreference(
                client_id=client.id,
                diet_type=profile['diet_preference'],
                meal_count_per_day=3,
                excluded_ingredients=profile['allergies'],
                preferred_ingredients=[],
                meal_size_preference='medium',
                calorie_target=2000
            )
            db.session.add(diet_pref)

            # Create initial goal
            goal = Goal(
                client_id=client.id,
                goal_type=profile['goal'],
                target_value=profile['goal'] == 'weight_loss' and 65.0 or 75.0,
                current_value=profile['goal'] == 'weight_loss' and 70.0 or 70.0,
                start_date=datetime.now().date(),
                target_date=(datetime.now() + timedelta(days=90)).date(),
                description=f"Initial {profile['goal'].replace('_', ' ')} goal"
            )
            db.session.add(goal)

            # Add progress logs
            for i in range(5):
                log = ProgressLog(
                    client_id=client.id,
                    log_date=datetime.now() - timedelta(days=i),
                    workout_completed=True,
                    exercise_data=[
                        {
                            'name': 'Push-ups',
                            'sets': 3,
                            'reps': 10,
                            'type': 'strength'
                        },
                        {
                            'name': 'Squats',
                            'sets': 3,
                            'reps': 15,
                            'type': 'strength'
                        }
                    ],
                    metrics={
                        'weight': profile['goal'] == 'weight_loss' and 70.0 - (i * 0.2) or 70.0 + (i * 0.2),
                        'energy_level': random.randint(7, 9),
                        'mood': random.choice(['great', 'good', 'tired'])
                    }
                )
                db.session.add(log)

            # Create activity feed entries
            activity = ActivityFeed(
                client_id=client.id,
                activity_type='goal_created',
                description=f"Started new {profile['goal'].replace('_', ' ')} journey",
                icon='target',
                priority='high',
                is_milestone=True
            )
            db.session.add(activity)

        # Create sample challenge
        challenge = Challenge(
            name="30-Day Fitness Challenge",
            description="Complete 30 workouts in 30 days",
            challenge_type="workout",
            target_value=30,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            created_by=1,
            reward_points=300,
            rules={
                'minimum_duration': 30,
                'rest_days_allowed': 5
            }
        )
        db.session.add(challenge)

        db.session.commit()
        logging.info("Successfully created sample data")

    except Exception as e:
        logging.error(f"Error creating sample data: {str(e)}")
        db.session.rollback()

with app.app_context():
    db.create_all()
    create_sample_resources()
    create_sample_achievements()
    create_sample_client()
    create_sample_data()

    # Create sample client achievements for existing clients
    clients = Client.query.all()
    for client in clients:
        create_sample_client_achievements(client.id)

# Add utility function
def log_activity(client_id, activity_type, description, icon=None, priority='normal', is_milestone=False, extra_data=None):
    """
    Log a new activity in the activity feed.
    """
    try:
        activity = ActivityFeed(
            client_id=client_id,
            activity_type=activity_type,
            description=description,
            icon=icon or activity_type,
            priority=priority,
            is_milestone=is_milestone,
            extra_data=extra_data or {}
        )
        db.session.add(activity)
        db.session.commit()
        logging.info(f"Activity logged for client {client_id}: {description}")
    except Exception as e:
        logging.error(f"Error logging activity: {str(e)}")
        db.session.rollback()

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
            # Get form data
            client_data = {
                'diet_type': request.form['diet_preference'],
                'meal_count_per_day': int(request.form.get('meals_per_day', 3)),
                'calorie_target': int(request.form.get('calorie_target', 2000)),
                'goal': request.form['goal'],
                'fitness_level': request.form['fitness_level'],
                'weekly_budget': float(request.form['weekly_budget']),
                'training_days': int(request.form['training_days'])
            }

            # Validate meal plan request
            is_valid, errors = validate_meal_plan_request(client_data)
            if not is_valid:
                for error in errors:
                    flash(error, 'danger')
                return render_template('create_plan.html')

            # Get client's performance data if available
            client_performance = None
            if 'client_id' in session:
                progress_logs = ProgressLog.query.filter_by(client_id=session['client_id'])\
                    .order_by(ProgressLog.log_date.desc())\
                    .limit(10)\
                    .all()

                if progress_logs:
                    client_performance = []
                    for log in progress_logs:
                        if log.exercise_data:
                            client_performance.extend(log.exercise_data)

            # Generate workout and meal plans
            try:
                workout_plan = workout_recommender.generate_workout_recommendations(
                    {
                        'fitness_level': client_data['fitness_level'],
                        'goal': client_data['goal'],
                        'training_days': client_data['training_days']
                    },
                    client_performance or [],
                    []  # goals data, can be added later
                )
            except Exception as e:
                logging.error(f"Error generating workout plan: {str(e)}")
                flash('Error generating workout plan. Please try again.', 'danger')
                return render_template('create_plan.html')

            # Create dietary preferences for AI meal planner
            diet_pref = DietaryPreference(
                diet_type=client_data['diet_type'],
                meal_count_per_day=client_data['meal_count_per_day'],
                excluded_ingredients=[],  # Can be updated later
                preferred_ingredients=[],  # Can be updated later
                meal_size_preference='medium',  # Default value
                calorie_target=client_data['calorie_target']
            )

            # Generate AI meal plan with error handling
            try:
                meal_plan = generate_ai_meal_plan(diet_pref)
                logging.info("Successfully generated AI meal plan")
            except Exception as e:
                logging.error(f"Error with AI meal plan, falling back to basic plan: {str(e)}")
                # Fallback to basic meal generator
                meal_plan = meal_generator.create_meal_plan(
                    client_data['diet_type'],
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
    """Preview the most recently created plan"""
    try:
        client_id = session.get('client_id')
        if not client_id:
            flash('No active session found. Please start the quiz again.', 'warning')
            return redirect(url_for('fitness_quiz'))

        # Get the most recent plan for this client
        plan = Plan.query.filter_by(client_id=client_id)\
            .order_by(Plan.created_at.desc())\
            .first()

        if not plan:
            flash('No plan found. Please complete the fitness quiz.', 'warning')
            return redirect(url_for('fitness_quiz'))

        return render_template('preview_plan.html', 
                            client_data=plan.client,
                            workout_plan=plan.workout_plan,
                            meal_plan=plan.meal_plan)
    except Exception as e:
        logging.error(f"Error previewing plan: {str(e)}")
        flash('Error loading plan preview. Please try again.', 'danger')
        return redirect(url_for('fitness_quiz'))



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
        logging.debug(f"Viewing progress for client_id: {client_id}")
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
                'next_milestone': {
                    'description': prog.next_milestone.get('description', 'Next level') if prog.next_milestone else 'Keep progressing'
                } if hasattr(prog, 'next_milestone') else {'description': 'Keep progressing'}
            }
            for prog in exercise_progressions
        ]

        # Get active goals for the client
        active_goals = Goal.query.filter_by(client_id=client_id).all()
        goals_data = [
            {
                'type': goal.goal_type,
                'target_value': goal.target_value,
                'description': goal.description,
                'target_date': goal.target_date.isoformat() if goal.target_date else None
            }
            for goal in active_goals
        ]

        # Generate AI insights including workout recommendations
        insights = progression_tracker.analyze_client_progress(
            client_id,
            logs_data,
            progression_data
        )

        # Add workout recommendations
        try:
            workout_recs = workout_recommender.generate_workout_recommendations(
                {
                    'id': client.id,
                    'fitness_level': client.fitness_level,
                    'goal': client.goal
                },
                logs_data,
                goals_data
            )
            insights['workout_recommendations'] = workout_recs
            logging.info(f"Generated workout recommendations for client {client_id}")
        except Exception as e:
            logging.error(f"Error generating workout recommendations: {str(e)}")
            insights['workout_recommendations'] = {
                'workout_focus': {'primary_types': [], 'intensity_range': 'moderate'},
                'suggested_exercises': [],
                'progression_path': []
            }

        # Convert ExerciseProgression objects to serializable format
        serializable_progressions = []
        for prog in exercise_progressions:
            serializable_prog = {
                'exercise_name': prog.exercise_name,
                'current_level': prog.current_level,
                'next_milestone': {
                    'description': prog.next_milestone.get('description', 'Next level') if prog.next_milestone else 'Keep progressing'
                } if hasattr(prog, 'next_milestone') else {'description': 'Keep progressing'}
            }
            serializable_progressions.append(serializable_prog)

        return render_template(
            'progress.html',
            client=client,
            progress_logs=progress_logs,
            exercise_progressions=serializable_progressions,
            insights=insights
        )

    except Exception as e:
        logging.error(f"Error viewing progress: {str(e)}")
        flash('Error loading progress data. Please try again.', 'danger')
        return redirect(url_for('clients_list'))

@app.route('/client/<int:client_id>/log-progress', methods=['POST'])
def log_progress():
    try:
        data = request.get_json()
        logging.debug(f"Logging progress for client_id: {data['client_id']} with data: {data}") #Added logging

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

# Add new route for onboarding
@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    """Handle user onboarding process"""
    if request.method == 'POST':
        try:
            # Validate form data
            form_data = {
                'name': request.form['name'],
                'email': request.form['email'],
                'fitness_level': request.form['fitness_level'],
                'goal': request.form['goal'],
                'training_days': request.form['training_days'],
                'diet_type': request.form['diet_type']
            }
            
            is_valid, errors = validate_client_registration(form_data)
            if not is_valid:
                for error in errors:
                    flash(error, 'danger')
                return render_template('onboarding.html', current_step=1, progress=25)

            # Create client profile
            client = Client(
                name=form_data['name'],
                email=form_data['email'],
                fitness_level=form_data['fitness_level'],
                goal=form_data['goal'],
                diet_preference=form_data['diet_type'],
                allergies=request.form.get('allergies', '').split(',') if request.form.get('allergies') else []
            )
            db.session.add(client)
            db.session.flush()  # Get client.id

            # Create dietary preferences
            diet_pref = DietaryPreference(
                client_id=client.id,
                diet_type=form_data['diet_type'],
                meal_count_per_day=3,  # Default value
                excluded_ingredients=client.allergies,
                meal_size_preference='medium',  # Default value
                calorie_target=2000  # Default value, can be updated later
            )
            db.session.add(diet_pref)

            # Create initial goal
            goal = Goal(
                client_id=client.id,
                goal_type=form_data['goal'],
                target_value=0,  # Will be set based on specific metrics later
                start_date=datetime.now().date(),
                target_date=(datetime.now() + timedelta(days=90)).date(),
                description=f"Initial {form_data['goal'].replace('_', ' ')} goal"
            )
            db.session.add(goal)

            # Log first activity 
            activity = ActivityFeed(
                client_id=client.id,
                activity_type='onboarding_completed',
                description="Started fitness journey!",
                icon='star',
                priority='high',
                is_milestone=True
            )
            db.session.add(activity)

            # Store client ID in session
            session['client_id'] = client.id

            db.session.commit()
            flash('Welcome to your fitness journey!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            logging.error(f"Error during onboarding: {str(e)}")
            db.session.rollback()
            flash('Error creating your profile. Please try again.', 'danger')
            return render_template('onboarding.html', current_step=1, progress=25)

    # GET request - show onboarding form
    return render_template('onboarding.html', current_step=1, progress=25)

@app.route('/dashboard')
def dashboard():
    try:
        # Get all clients
        clients = Client.query.all()

        # For testing, if no clients exist, add some sample data
        if not clients:
            logging.info("No clients found, adding sample data")
            # Add a sample client
            client = Client(
                name="Sample Client",
                trainer_id=1,
                fitness_level="intermediate",
                goal="weight_loss"
            )
            db.session.add(client)
            db.session.flush()

            # Add sample progress logs
            for i in range(7):
                log = ProgressLog(
                    client_id=client.id,
                    log_date=datetime.utcnow() - timedelta(days=i),
                    workout_completed=True,
                    exercise_data=[
                        {'type': 'strength', 'name': 'Push-ups', 'sets': 3, 'reps': 10},
                        {'type': 'cardio', 'name': 'Running', 'duration': 30}
                    ],
                    metrics={'weight': 70, 'body_fat': 20}
                )
                db.session.add(log)

            # Add sample goal
            goal = Goal(
                client_id=client.id,
                goal_type='weight_loss',
                target_value=65,
                start_date=datetime.utcnow().date(),
                target_date=(datetime.utcnow() + timedelta(days=90)).date(),
                description='Lose 5kg in 3 months'
            )
            db.session.add(goal)

            # Add sample goal progress
            progress = GoalProgress(
                goal_id=goal.id,
                recorded_value=68,
                recorded_date=datetime.utcnow()
            )
            db.session.add(progress)

            db.session.commit()
            clients = Client.query.all()  # Refresh clients list

        # Calculate dashboard statistics
        total_clients = len(clients)
        improving_clients = 0
        completion_rate = 0

        # Prepare data for visualizations
        progress_data = {
            'weekly_workouts': [0] * 7,  # Last 7 days
            'goal_progress': [],
            'client_improvements': {
                'improving': 0,
                'maintaining': 0,
                'declining': 0
            },
            'completion_by_type': {
                'strength': 0,
                'cardio': 0,
                'flexibility': 0
            }
        }

        # Calculate statistics and collect visualization data
        one_week_ago = datetime.utcnow() - timedelta(days=7)

        if total_clients > 0:
            for client in clients:
                # Get client's progress logs
                progress_logs = ProgressLog.query.filter_by(client_id=client.id)\
                    .filter(ProgressLog.log_date >= one_week_ago)\
                    .order_by(ProgressLog.log_date.desc())\
                    .all()

                # Process weekly workout data
                for log in progress_logs:
                    if log.workout_completed:
                        day_index = (datetime.utcnow() - log.log_date).days
                        if 0 <= day_index < 7:
                            progress_data['weekly_workouts'][day_index] += 1

                        # Track workout types
                        if log.exercise_data:
                            for exercise in log.exercise_data:
                                exercise_type = exercise.get('type', 'strength')
                                progress_data['completion_by_type'][exercise_type] = \
                                    progress_data['completion_by_type'].get(exercise_type, 0) + 1

                # Calculate completion rate
                if progress_logs:
                    client_completion = sum(1 for log in progress_logs if log.workout_completed) / len(progress_logs)
                    completion_rate += client_completion

                # Get client's goals and progress
                goals = Goal.query.filter_by(client_id=client.id).all()
                for goal in goals:
                    latest_progress = GoalProgress.query.filter_by(goal_id=goal.id)\
                        .order_by(GoalProgress.recorded_date.desc())\
                        .first()

                    if latest_progress:
                        progress_percentage = (latest_progress.recorded_value / goal.target_value) * 100
                        progress_data['goal_progress'].append({
                            'client_name': client.name,
                            'goal_type': goal.goal_type,
                            'progress': min(progress_percentage, 100)
                        })

                # Analyze improvement trend
                if progress_logs:
                    trend = progression_tracker.analyze_client_progress(
                        client.id,
                        progress_logs,
                        []  # Empty progression data as we only need trend
                    )['performance_trends']['trend']

                    progress_data['client_improvements'][trend] = \
                        progress_data['client_improvements'].get(trend, 0) + 1

                    if trend == 'improving':
                        improving_clients += 1

            improving_clients = (improving_clients / total_clients) * 100
            completion_rate = (completion_rate / total_clients) * 100

        # Get activity feed
        activities = ActivityFeed.query\
            .order_by(ActivityFeed.created_at.desc())\
            .limit(10)\
            .all()

        activity_feed = []
        for activity in activities:
            client = Client.query.get(activity.client_id)
            activity_feed.append({
                'client_name': client.name,
                'activity_type': activity.activity_type,
                'description': activity.description,
                'icon': activity.icon,
                'timestamp': activity.created_at.strftime('%Y-%m-%d %H:%M'),
                'priority': activity.priority,
                'is_milestone': activity.is_milestone,
                'extra_data': activity.extra_data
            })

        # Prepare summary stats
        stats = {
            'total_clients': total_clients,
            'weekly_workouts': sum(progress_data['weekly_workouts']),
            'improving_clients': round(improving_clients),
            'completion_rate': round(completion_rate)
        }

        logging.info(f"Dashboard data prepared: {progress_data}")  # Debug log

        return render_template('dashboard.html',
                            clients=clients,
                            stats=stats,
                            activity_feed=activity_feed,
                            progress_data=progress_data)

    except Exception as e:
        logging.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard data. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/fitness-quiz')
def fitness_quiz():
    """Display the fitness quiz form"""
    return render_template('fitness_quiz.html')

@app.route('/api/fitness-quiz', methods=['POST'])
def submit_fitness_quiz():
    """Handle fitness quiz submission and create initial plan"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        client_id = session.get('client_id')
        if not client_id:
            # Create a new client if none exists
            client = Client(
                name=data.get('name', 'New Client'),
                trainer_id=1,  # Set a default trainer ID for now
                fitness_level=data.get('fitnessLevel'),
                goal=data.get('primaryGoal')
            )
            db.session.add(client)
            db.session.flush()  # Get the client.id
            client_id = client.id
            session['client_id'] = client_id
            logging.info(f"Created new client with ID: {client_id}")
        else:
            client = Client.query.get_or_404(client_id)
            # Update existing client
            client.fitness_level = data.get('fitnessLevel')
            client.goal = data.get('primaryGoal')

        # Create a new dietary preference record
        dietary_pref = DietaryPreference(
            client_id=client_id,
            diet_type=','.join(data.get('dietaryRestrictions', [])),
            meal_count_per_day=int(data.get('weeklyCommitment', 3))
        )
        db.session.add(dietary_pref)

        # Create an initial goal based on primary goal
        goal = Goal(
            client_id=client_id,
            goal_type=data.get('primaryGoal'),
            start_date=datetime.now().date(),
            target_date=(datetime.now() + timedelta(days=90)).date(),
            description=f"Initial {data.get('primaryGoal').replace('_', ' ')} goal"
        )
        db.session.add(goal)

        # Create initial training plan
        plan = Plan(
            client_id=client_id,
            name=f"{client.name}'s Initial Plan",
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=90)).date(),
            type='initial',
            status='active',
            workout_frequency=int(data.get('weeklyCommitment', 3)),
            workout_duration=int(data.get('workoutDuration', 45)),
            focus_areas=data.get('focusAreas', []),
            restrictions=data.get('healthConditions', ''),
            workout_plan={
                'schedule': generate_workout_schedule(
                    data.get('fitnessLevel'),
                    data.get('focusAreas', []),
                    int(data.get('weeklyCommitment', 3))
                )
            },
            meal_plan={
                'dietary_restrictions': data.get('dietaryRestrictions', []),
                'meals_per_day': int(data.get('weeklyCommitment', 3)),
                'schedule': generate_meal_schedule(
                    data.get('dietaryRestrictions', []),
                    int(data.get('weeklyCommitment', 3))
                )
            }
        )
        db.session.add(plan)

        # Log activity
        log_activity(
            client_id=client_id,
            activity_type='onboarding_completed',
            description='Completed fitness assessment quiz and created initial plan',
            icon='clipboard',
            priority='high',
            is_milestone=True,
            extra_data={
                'quiz_data': data,
                'plan_id': plan.id
            }
        )

        db.session.commit()
        logging.info(f"Successfully created plan {plan.id} for client {client_id}")

        # Redirect to plan preview
        return jsonify({
            'success': True,
            'redirect': url_for('preview_plan')  # Removed plan_id parameter
        })

    except Exception as e:
        logging.error(f"Error processing fitness quiz: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process quiz data'}), 500

def generate_workout_schedule(fitness_level, focus_areas, weekly_frequency):
    """Generate a personalized workout schedule based on quiz responses"""
    exercises_by_level = {
        'beginner': {
            'upper_body': ['Push-ups', 'Band Rows', 'Wall Push-ups'],
            'lower_body': ['Bodyweight Squats', 'Walking Lunges', 'Glute Bridges'],
            'core': ['Planks', 'Bird Dogs', 'Dead Bugs'],
            'cardio': ['Walking', 'Stationary Bike', 'Swimming']
        },
        'intermediate': {
            'upper_body': ['Regular Push-ups', 'Inverted Rows', 'Diamond Push-ups'],
            'lower_body': ['Jump Squats', 'Reverse Lunges', 'Step-ups'],
            'core': ['Side Planks', 'Mountain Climbers', 'Russian Twists'],
            'cardio': ['Jogging', 'Jump Rope', 'Rowing']
        },
        'advanced': {
            'upper_body': ['Weighted Push-ups', 'Weighted Pull-ups', 'Ring Dips'],
            'lowerbody': ['Weighted Push-ups', 'Weighted Pull-ups', 'Ring Dips'],
            'lower_body': ['Front Squats', 'Deadlifts', 'Plyometric Lunges'],
            'core': ['Dragon Flags', 'Ab Wheel Rollouts', 'Hanging Leg Raises'],
            'cardio': ['Sprinting', 'Complex HIIT', 'CrossFit WODs']
        }
    }

    schedule = []

    # Generate workouts based on focus areas and frequency
    for week in range(4):  # Generate 4 weeks of workouts
        weekly_workouts = []
        for day in range(weekly_frequency):
            workout = {
                'day': day + 1,
                'exercises': []
            }

            # Add exercises based on focus areas
            for area in focus_areas:
                if area in exercises_by_level[fitness_level]:
                    focus_area_exercises = exercises_by_level[fitness_level][area]
                    workout['exercises'].extend([
                        {
                            'name': exercise,
                            'type': area,
                            'sets': '3-4',
                            'reps': '8-12',
                            'rest': '60 sec'
                        }
                        for exercise in focus_area_exercises[:2]  # Pick 2 exercises per area
                    ])

            weekly_workouts.append(workout)

        schedule.append({
            'week': week + 1,
            'workouts': weekly_workouts
        })

    return schedule

def generate_meal_schedule(dietary_restrictions, meals_per_day):
    """Generate a basic meal schedule based on dietary preferences"""
    meal_templates = {
        'standard': {
            'breakfast': ['Oatmeal with fruits', 'Eggs and toast', 'Greek yogurt parfait'],
            'lunch': ['Grilled chicken salad', 'Turkey sandwich', 'Quinoa bowl'],
            'dinner': ['Salmon with vegetables', 'Lean beef stir-fry', 'Chicken breast with sweet potato']
        },
        'vegetarian': {
            'breakfast': ['Smoothie bowl', 'Avocado toast', 'Overnight oats'],
            'lunch': ['Chickpea curry', 'Lentil soup', 'Buddha bowl'],
            'dinner': ['Black bean burrito', 'Tofu stir-fry', 'Veggie pasta']
        },
        'vegan': {
            'breakfast': ['Chia pudding', 'Tofu scramble', 'Green smoothie'],
            'lunch': ['Tempeh wrap', 'Quinoa salad', 'Vegetable soup'],
            'dinner': ['Lentil shepherd\'s pie', 'Mushroom curry', 'Bean chili']
        }
    }

    diet_type = 'standard'
    if 'vegan' in dietary_restrictions:
        diet_type = 'vegan'
    elif 'vegetarian' in dietary_restrictions:
        diet_type = 'vegetarian'

    schedule = []
    for week in range(4):
        weekly_meals = []
        for day in range(7):
            meals = []
            for meal in range(meals_per_day):
                meal_template = meal_templates[diet_type].get('breakfast', [])
                meals.append({
                    'name': random.choice(meal_template),
                    'macros': calculate_macros(meal_template[0], diet_type)
                })
            weekly_meals.append({
                'day': day + 1,
                'meals': meals
            })
        schedule.append({
            'week': week + 1,
            'meals': weekly_meals
        })
    return schedule

def calculate_macros(meal, diet_type):
    """Calculate approximate macros for a meal"""
    # Simplified macro calculations
    base_macros = {
        'standard': {'protein': 30, 'carbs': 40, 'fats': 30},
        'vegetarian': {'protein': 25, 'carbs': 45, 'fats': 30},
        'vegan': {'protein': 20, 'carbs': 50, 'fats': 30}
    }

    return base_macros[diet_type]

@app.route('/client/<int:client_id>/goals/new')
def goal_wizard(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        goal_descriptions = {
            'weight_loss': 'Set target weight and create a schedule for healthy weight loss',
            'muscle_gain': 'Build muscle mass with specific target areas and measurements',
            'endurance': 'Improve cardiovascular fitness and endurance metrics',
            'strength': 'Increase strength with specific lifting and resistance goals',
            'flexibility': 'Enhance flexibility and mobility measurements'
        }
        return render_template('goal_wizard.html', client=client, goal_descriptions=goal_descriptions)
    except Exception as e:
        logging.error(f"Error loading goal wizard: {str(e)}")
        flash('Error loading goal wizard. Please try again.', 'danger')
        return redirect(url_for('clients_list'))

@app.route('/api/goals', methods=['POST'])
def create_goal():
    try:
        data = request.get_json()
        client_id = data.get('client_id')  # Get client_id from request data

        if not client_id:
            return jsonify({'error': 'Client ID is required'}), 400

        # Create the main goal
        goal = Goal(
            client_id=client_id,
            goal_type=data['goalType'],
            target_value=float(data['targetValue']),
            current_value=None,  # Will be set when first progress is logged
            start_date=datetime.now().date(),
            target_date=datetime.strptime(data['targetDate'], '%Y-%m-%d').date(),
            description=data['description']
        )
        db.session.add(goal)

        # Create milestones
        for milestone_data in data['milestones']:
            milestone = GoalMilestone(
                goal=goal,
                milestone_value=float(milestone_data['value']),
                description=milestone_data['description'],
                target_date=datetime.strptime(milestone_data['date'], '%Y-%m-%d').date()
            )
            db.session.add(milestone)

        db.session.commit()

        # Log activity
        log_activity(
            client_id=client_id,
            activity_type='goal_created',
            description=f"New {data['goalType'].replace('_', ' ')} goal created",
            icon='target',
            priority='high',
            is_milestone=True,
            extra_data={
                'goal_type': data['goalType'],
                'target_value': data['targetValue'],
                'target_date': data['targetDate']
            }
        )

        return jsonify({'success': True, 'client_id': client_id})

    except Exception as e:
        logging.error(f"Error creating goal: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create goal'}), 500

@app.route('/client/<int:client_id>/goals')
def view_goals(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        goals = Goal.query.filter_by(client_id=client_id).order_by(Goal.created_at.desc()).all()
        return render_template('goals.html', client=client, goals=goals)
    except Exception as e:
        logging.error(f"Error viewing goals: {str(e)}")
        flash('Error loading goals. Please try again.', 'danger')
        return redirect(url_for('clients_list'))

@app.route('/meal-planner')
def meal_planner_wizard():
    diet_descriptions = {
        'Standard': 'A balanced diet with all food groups',
        'Vegetarian': 'Plant-based diet that includes dairy and eggs',
        'Vegan': 'Entirely plant-based diet',
        'Keto': 'High-fat, low-carb diet',
        'Paleo': 'Based on whole foods and lean proteins',
        'Mediterranean': 'Rich in vegetables, olive oil, and lean proteins'
    }
    return render_template('meal_planner_wizard.html', diet_descriptions=diet_descriptions)

@app.route('/api/meal-planner/preferences', methods=['POST'])
def save_meal_preferences():
    try:
        data = request.get_json()

        # Create new dietary preference
        preference = DietaryPreference(
            client_id=session.get('client_id'),  # You'll need to implement client session management
            diet_type=data.get('dietType'),
            excluded_ingredients=data.get('excludedIngredients', '').split(','),
            preferred_ingredients=data.get('preferredIngredients', '').split(','),
            meal_size_preference=data.get('mealSize'),
            meal_count_per_day=int(data.get('mealCount')),
            calorie_target=int(data.get('calorieTarget')),
            macro_targets={},  # You can add macro calculations based on diet type
            meal_timing={}  # You can format meal timing data
            #            # You can format meal timing data here
        )

        db.session.add(preference)

        # Create meal plan
        start_date = datetime.strptime(data.get('startDate'), '%Y-%m-%d').date()
        duration_weeks = int(data.get('duration'))
        end_date = start_date + timedelta(weeks=duration_weeks)

        meal_plan = MealPlan(
            client_id=session.get('client_id'),
            start_date=start_date,
            end_date=end_date,
            daily_plans={},  # This will be populated by the meal planning algorithm
            shopping_list={},
            status='pending'
        )

        db.session.add(meal_plan)
        db.session.commit()

        return jsonify({'success': True, 'meal_plan_id': meal_plan.id})

    except Exception as e:
        logging.error(f"Error saving meal preferences: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save preferences'}), 500

@app.route('/meal-plan')
def view_meal_plan():
    try:
        # Get the latest meal plan for the client
        meal_plan = MealPlan.query.filter_by(
            client_id=session.get('client_id'),
            status='active'
        ).order_by(MealPlan.created_at.desc()).first()

        if not meal_plan:
            flash('No active meal plan found.', 'warning')
            return redirect(url_for('meal_planner_wizard'))

        return render_template('meal_plan.html', meal_plan=meal_plan)

    except Exception as e:
        logging.error(f"Error viewing meal plan: {str(e)}")
        flash('Error loading meal plan. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/meal-substitutions')
def meal_substitutions():
    try:
        clients = Client.query.all()
        return render_template('meal_substitutions.html', clients=clients)
    except Exception as e:
        logging.error(f"Error loading meal substitutions page: {str(e)}")
        flash('Error loading meal substitutions. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/api/ingredients/substitutes', methods=['GET'])
def find_ingredient_substitutes():
    try:
        ingredient_name = request.args.get('ingredient')
        client_id = request.args.get('client_id', type=int)
        budget_limit = request.args.get('budget_limit', type=float)

        if not ingredient_name:
            return jsonify({'error': 'Ingredient name is required'}), 400

        # Get client preferences and allergies
        client = Client.query.getor_404(client_id) if client_id else None
        preferences = {
            'diet_type': client.diet_preference if client else None,
            'budget_conscious': bool(budget_limit),
            'nutrition_focus': True  # Default to considering nutrition
        }
        allergies = client.allergies if client else []

        # Find suitable substitutes
        substitutes = meal_substitution.find_substitutes(
            ingredient_name,
            preferences,
            allergies,
            budget_limit
        )

        return jsonify({'substitutes': substitutes})

    except Exception as e:
        logging.error(f"Error finding substitutes: {str(e)}")
        return jsonify({'error': 'Failed to find substitutes'}), 500

@app.route('/api/ingredients/validate-substitution', methods=['POST'])
def validate_ingredient_substitution():
    try:
        data = request.get_json()
        if not all(k in data for k in ['original', 'substitute', 'amount']):
            return jsonify({'error': 'Missing required fields'}), 400

        validation = meal_substitution.validate_substitution(data['original'],
                                                             data['substitute'],
                                                             float(data['amount'])
                                                             )

        return jsonify(validation)

    except Exception as e:
        logging.error(f"Error validating substitution: {str(e)}")
        return jsonify({'error': 'Failed to validate substitution'}), 500

@app.route('/api/ingredients', methods=['GET'])
def list_ingredients():
    try:
        # Get optional filters
        category = request.args.get('category')
        query = MealIngredient.query

        if category:
            query = query.filter_by(category=category)

        ingredients = query.all()
        return jsonify({
            'ingredients': [
                {
                    'id': ing.id,
                    'name': ing.name,
                    'category': ing.category,
                    'nutrition_per_100g': ing.nutrition_per_100g,
                    'common_allergens': ing.common_allergens,
                    'estimated_cost': ing.estimated_cost
                }
                for ing in ingredients
            ]
        })

    except Exception as e:
        logging.error(f"Error listing ingredients: {str(e)}")
        return jsonify({'error': 'Failed to list ingredients'}), 500


@app.route('/api/achievements/check', methods=['POST'])
def check_achievements():
    """Check and award new achievements for a client"""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        activity_type = data.get('activity_type')

        if not client_id:
            return jsonify({'error': 'Client ID is required'}), 400

        client = Client.query.get_or_404(client_id)

        # Get all achievements for this activity type
        achievements = Achievement.query.filter_by(type=activity_type).all()
        earned_achievements = []

        for achievement in achievements:
            # Check if client already has this achievement
            existing = ClientAchievement.query.filter_by(
                client_id=client_id,
                achievement_id=achievement.id,
                completed=True
            ).first()

            if not existing:
                # Calculate progress based on achievement criteria
                progress = calculate_achievement_progress(client, achievement)

                if progress >= 100:  # Achievement earned
                    client_achievement = ClientAchievement(
                        client_id=client_id,
                        achievement_id=achievement.id,
                        progress=100,
                        completed=True
                    )
                    db.session.add(client_achievement)

                    # Update client's total points
                    client.points += achievement.points

                    earned_achievements.append({
                        'name': achievement.name,
                        'description': achievement.description,
                        'icon': achievement.icon,
                        'level': achievement.level,
                        'points': achievement.points
                    })

                    # Log activity
                    log_activity(
                        client_id=client_id,
                        activity_type='achievement_earned',
                        description=f"Earned the {achievement.name} badge!",
                        icon='award',
                        priority='high',
                        is_milestone=True,
                        extra_data={
                            'achievement_name': achievement.name,
                            'achievement_level': achievement.level,
                            'points_earned': achievement.points
                        }
                    )
                else:
                    # Update progress
                    client_achievement = ClientAchievement.query.filter_by(
                        client_id=client_id,
                        achievement_id=achievement.id
                    ).first()

                    if client_achievement:
                        client_achievement.progress = progress
                    else:
                        client_achievement = ClientAchievement(
                            client_id=client_id,
                            achievement_id=achievement.id,
                            progress=progress
                        )
                        db.session.add(client_achievement)

        db.session.commit()
        return jsonify({
            'earned_achievements': earned_achievements,
            'total_points': client.points
        })

    except Exception as e:
        logging.error(f"Error checking achievements: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to check achievements'}), 500

@app.route('/client/<int:client_id>/achievements')
def view_achievements(client_id):
    """Display client achievements and badges"""
    try:
        client = Client.query.get_or_404(client_id)

        # Get all achievements and client's earned achievements
        achievements = Achievement.query.all()
        client_achievements = ClientAchievement.query.filter_by(client_id=client_id).all()

        # Create a progress map for each achievement
        progress_map = {
            achievement.achievement_id: {
                'progress': achievement.progress,
                'completed': achievement.completed,
                'earned_at': achievement.earned_at
            }
            for achievement in client_achievements
        }

        # Get recommended achievements
        recommended_achievements = Achievement.get_recommendations(client_id)

        return render_template(
            'achievements.html',
            client=client,
            achievements=achievements,
            progress_map=progress_map,
            recommended_achievements=recommended_achievements
        )

    except Exception as e:
        logging.error(f"Error viewing achievements: {str(e)}")
        flash('Error loading achievements. Please try again.', 'danger')
        return redirect(url_for('clients_list'))

def calculate_achievement_progress(client, achievement):
    """Calculate progress towards an achievement based on its criteria"""
    try:
        criteria = achievement.criteria
        achievement_type = achievement.type

        if achievement_type == 'workout_streak':
            # Calculate workout streak
            logs = ProgressLog.query.filter_by(
                client_id=client.id,
                workout_completed=True
            ).order_by(ProgressLog.log_date.desc()).all()

            streak = 0
            last_date = None

            for log in logs:
                if not last_date:
                    streak = 1
                    last_date = log.log_date.date()
                else:
                    if (last_date - log.log_date.date()).days == 1:
                        streak += 1
                        last_date = log.log_date.date()
                    else:
                        break

            target_streak = criteria.get('streak_days', 7)
            return min((streak / target_streak) * 100, 100)

        elif achievement_type == 'goal_completion':
            # Calculate goal completion rate
            completed_goals = Goal.query.filter_by(
                client_id=client.id,
                status='completed'
            ).count()

            target_goals = criteria.get('completed_goals', 1)
            return min((completed_goals / target_goals) * 100, 100)

        # Add more achievement types as needed

        return 0

    except Exception as e:
        logging.error(f"Error calculating achievement progress: {str(e)}")
        return 0

@app.route('/client/<int:client_id>/generate-report')
def generate_client_report(client_id):
    try:
        logging.info(f"Starting report generation for client {client_id}")
        client = Client.query.get_or_404(client_id)
        logging.debug(f"Client found: {client.name}, created_at: {client.created_at}")

        # Get client's achievements
        achievements = ClientAchievement.query.filter_by(client_id=client_id).all()
        logging.debug(f"Found {len(achievements)} achievements")

        # Get progress logs
        progress_logs = ProgressLog.query.filter_by(client_id=client_id)\
            .order_by(ProgressLog.log_date.desc()).all()
        logging.debug(f"Found {len(progress_logs)} progress logs")

        # Get goals
        goals = Goal.query.filter_by(client_id=client_id).all()
        logging.debug(f"Found {len(goals)} goals")

        # Generate PDF report
        from utils.report_generator import generate_client_report
        pdf_buffer = generate_client_report(client, achievements, progress_logs, goals)
        logging.info("PDF report generated successfully")

        # Create the response
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{client.name}_progress_report.pdf'
        )

    except Exception as e:
        logging.error(f"Error generating client report: {str(e)}")
        flash('Error generating report. Pleasetry again.', 'danger')
        return redirect(url_for('view_progress', client_id=client_id))

@app.route('/resources')
def resource_library():
    """Display the fitness resource library with search functionality"""
    try:
        query = request.args.get('query', '')
        resource_type = request.args.get('type')
        difficulty = request.args.get('difficulty')

        # Search resources with filters
        resources = FitnessResource.search(
            query=query,
            resource_type=resource_type,
            difficulty=difficulty
        )

        return render_template('resource_library.html', resources=resources)
    except Exception as e:
        logging.error(f"Error accessing resource library: {str(e)}")
        flash('Error loading resources. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/resource/<int:resource_id>')
def view_resource(resource_id):
    """Display a single fitness resource"""
    try:
        resource = FitnessResource.query.get_or_404(resource_id)

        # Increment view count
        resource.views += 1
        db.session.commit()

        return render_template('view_resource.html', resource=resource)
    except Exception as e:
        logging.error(f"Error viewing resource: {str(e)}")
        flash('Error loading resource. Please try again.', 'danger')
        return redirect(url_for('resource_library'))

# Add this route after your existing routes
@app.route('/client/<int:client_id>/adjust-workout', methods=['POST'])
def adjust_workout(client_id):
    """Adjust workout difficulty based on client's performance data"""
    try:
        client = Client.query.get_or_404(client_id)

        # Get recent progress logs
        progress_logs = ProgressLog.query.filter_by(client_id=client_id)\
            .order_by(ProgressLog.log_date.desc())\
            .limit(10)\
            .all()

        # Extract exercise data from logs
        exercise_data = []
        for log in progress_logs:
            if log.exercise_data:
                for exercise in log.exercise_data:
                    # Add completion status based on metrics
                    exercise['completed'] = log.workout_completed
                    # Add form rating based on intensity metric
                    exercise['form_rating'] = log.metrics.get('intensity', 7) if log.metrics else 7
                    exercise_data.append(exercise)

        # Default workout if no logs exist
        base_exercises = [
            {
                'name': 'Push-ups',
                'sets': 3,
                'reps': 10,
                'type': 'strength'
            },
            {
                'name': 'Bodyweight Squats',
                'sets': 3,
                'reps': 12,
                'type': 'strength'
            },
            {
                'name': 'Plank',
                'sets': 3,
                'reps': '30 seconds',
                'type': 'core'
            }
        ]

        # Generate new workout plan with difficulty adjustment
        if exercise_data:
            adjusted_exercises = []
            for exercise in exercise_data:
                # Group exercise data by name
                exercise_history = [e for e in exercise_data if e['name'] == exercise['name']]
                if exercise_history:
                    adjusted = workout_generator.adjust_exercise_difficulty(
                        exercise.copy(),
                        exercise_history,
                        client.fitness_level
                    )
                    if adjusted not in adjusted_exercises:  # Avoid duplicates
                        adjusted_exercises.append(adjusted)
        else:
            # If no exercise data, create a beginner-friendly plan
            adjusted_exercises = base_exercises

        # Create the response workout plan
        workout_plan = {
            'exercises': adjusted_exercises,
            'last_adjusted': datetime.utcnow().isoformat()
        }

        # Log the adjustment
        log_activity(
            client_id=client_id,
            activity_type='workout_adjusted',
            description='Workout difficulty automatically adjusted based on performance',
            icon='sliders',
            priority='normal',
            extra_data={'adjusted_plan': workout_plan}
        )

        return jsonify({
            'success': True,
            'workout_plan': workout_plan
        })

    except Exception as e:
        logging.error(f"Error adjusting workout: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to adjust workout plan'
        }), 500

# Add these routes after your existing routes

@app.route('/challenges')
@app.route('/challenges')
def challenges():
    """Display social challenges and leaderboard"""
    try:
        # Get active challenges
        active_challenges = Challenge.query\
            .filter(Challenge.end_date > datetime.utcnow())\
            .filter_by(status='active')\
            .order_by(Challenge.created_at.desc())\
            .all()

        # Get user's joined challenges
        user_challenges = []
        if 'client_id' in session:
            client = Client.query.get(session['client_id'])
            if client:
                user_challenges = client.participated_challenges.all()

        # Get global leaderboard
        leaderboard = LeaderboardEntry.query\
            .filter_by(category='global')\
            .order_by(LeaderboardEntry.rank)\
            .limit(10)\
            .all()

        return render_template('challenges.html',
                            active_challenges=active_challenges,
                            user_challenges=user_challenges,
                            leaderboard=leaderboard,
                            current_user={'id': session.get('client_id')})

    except Exception as e:
        logging.error(f"Error loading challenges page: {str(e)}")
        flash('Error loading challenges. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/challenge/create', methods=['POST'])
def create_challenge():
    """Create a new social challenge"""
    if 'client_id' not in session:
        return jsonify({'success': False, 'error': 'Please log in first'}), 401

    try:
        data = request.get_json()

        # Validate challenge data
        is_valid, errors = validate_challenge_creation(data)
        if not is_valid:
            return jsonify({'error': errors}), 400

        # Create challenge
        challenge = Challenge(
            name=data['name'],
            description=data['description'],
            challenge_type=data['challenge_type'],
            target_value=float(data['target_value']),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d'),
            created_by=session['client_id'],
            reward_points=data.get('reward_points', 100),
            rules=data.get('rules', {})
        )
        db.session.add(challenge)

        # Add creator as first participant
        participant = ChallengeParticipant(
            challenge_id=challenge.id,
            client_id=session['client_id']
        )
        db.session.add(participant)

        # Log activity
        log_activity(
            client_id=session['client_id'],
            activity_type='challenge_created',
            description=f"Created new challenge: {data['name']}",
            icon='award'
        )

        db.session.commit()
        return jsonify({
            'success': True,
            'challenge_id': challenge.id,
            'message': 'Challenge created successfully'
        })

    except Exception as e:
        logging.error(f"Error creating challenge: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/challenge/<int:challenge_id>/join', methods=['POST'])
def join_challenge(challenge_id):
    """Join a fitness challenge"""
    try:
        if 'client_id' not in session:
            return jsonify({'error': 'Please log in first'}), 401

        client = Client.query.get_or_404(session['client_id'])
        challenge = Challenge.query.get_or_404(challenge_id)

        # Check if already joined
        existing_participation = ChallengeParticipant.query.filter_by(
            challenge_id=challenge_id,
            client_id=client.id
        ).first()

        if existing_participation:
            return jsonify({'error': 'Already joined this challenge'}), 400

        # Create new participant entry
        participant = ChallengeParticipant(
            challenge_id=challenge_id,
            client_id=client.id
        )
        db.session.add(participant)

        # Log activity
        log_activity(
            client_id=client.id,
            activity_type='challenge_joined',
            description=f"Joined challenge: {challenge.name}",
            icon='award'
        )

        db.session.commit()
        return jsonify({'success': True, 'message': 'Successfully joined challenge'})

    except Exception as e:
        logging.error(f"Error joining challenge: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/challenge/<int:challenge_id>/leaderboard')
def challenge_leaderboard(challenge_id):
    """Get leaderboard for a specific challenge"""
    try:
        challenge = Challenge.query.get_or_404(challenge_id)
        leaderboard = challenge.get_leaderboard()

        return jsonify({
            'success': True,
            'leaderboard': [
                {
                    'rank': index + 1,
                    'client_name': entry.client.name,
                    'current_value': entry.current_value,
                    'completed': entry.completed
                }
                for index, entry in enumerate(leaderboard)
            ]
        })

    except Exception as e:
        logging.error(f"Error getting challenge leaderboard: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/achievement/<int:achievement_id>/share-preview')
def achievement_share_preview(achievement_id):
    """Generate a preview for sharing an achievement"""
    try:
        # Get achievement and client progress details
        achievement = Achievement.query.get_or_404(achievement_id)
        client_achievement = ClientAchievement.query.filter_by(
            achievement_id=achievement_id
        ).first_or_404()
        client = Client.query.get_or_404(client_achievement.client_id)

        # Generate preview HTML
        preview_html = render_template('_achievement_share_preview.html',
                                        achievement=achievement,
                                        client=client,
                                        earned_date=client_achievement.earned_at.strftime('%B %d, %Y')
                                        )

        # Generate share text
        share_text = f"I just earned the {achievement.name} achievement on FitTracker! 🏆"
        if achievement.level:
                        share_text += f" ({achievement.level.title()} level)"

        return jsonify({
            'success': True,
            'preview_html': preview_html,
            'share_text': share_text,
            'achievement_url': url_for('achievement_share_preview',
                                         achievement_id=achievement_id,
                                         _external=True)
        })

    except Exception as e:
        logging.error(f"Error generating achievement share preview: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate achievement preview'
        }), 500

# Add new route for AI meal planning
@app.route('/generate-meal-plan', methods=['POST'])
def generate_meal_plan():
    """Generate an AI-powered meal plan based on client preferences"""
    try:
        if 'client_id' not in session:
            return jsonify({'error': 'Please log in first'}), 401

        data = request.get_json()
        client = Client.query.get_or_404(session['client_id'])
        logging.info(f"Generating meal plan for client {client.id}")

        # Get client's dietary preferences
        preferences = DietaryPreference.query.filter_by(client_id=client.id).first()
        if not preferences:
            return jsonify({'error': 'Please set your dietary preferences first'}), 400

        logging.info(f"Using dietary preferences: {preferences.diet_type}, meals per day: {preferences.meal_count_per_day}")

        # Generate AI meal plan
        try:
            logging.info("Calling OpenAI API for meal plan generation")
            meal_plan = generate_ai_meal_plan(preferences, duration_weeks=int(data.get('duration_weeks', 1)))
            logging.info("Successfully generated AI meal plan")

            # Create new meal plan record
            new_plan = MealPlan(
                client_id=client.id,
                start_date=datetime.now().date(),
                end_date=(datetime.now() + timedelta(weeks=int(data.get('duration_weeks', 1)))).date(),
                daily_plans=meal_plan['weekly_plans'],
                shopping_list=meal_plan['shopping_lists'],
                notes='\n'.join(meal_plan['meal_prep_tips']),
                status='active'
            )
            db.session.add(new_plan)

            # Log activity
            log_activity(
                client_id=client.id,
                activity_type='meal_plan_generated',
                description='Generated new AI meal plan',
                icon='coffee',
                extra_data={'plan_id': new_plan.id}
            )

            db.session.commit()
            logging.info(f"Created new meal plan with ID: {new_plan.id}")

            return jsonify({
                'success': True,
                'meal_plan': meal_plan,
                'plan_id': new_plan.id
            })

        except Exception as e:
            logging.error(f"Error generating AI meal plan: {str(e)}")
            # Fallback to basic meal generator
            logging.info("Falling back to basic meal generator")
            fallback_plan = meal_generator.create_meal_plan(
                preferences.diet_type,
                float(data.get('weekly_budget', 100))  # Default budget if not specified
            )

            return jsonify({
                'success': True,
                'meal_plan': fallback_plan,
                'is_fallback': True
            })

    except Exception as e:
        logging.error(f"Error in generate_meal_plan route: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/log-workout', methods=['POST'])
def log_workout():
    """Log a completed workout with validation"""
    try:
        data = request.get_json()

        # Validate workout log
        is_valid, errors = validate_workout_log(data)
        if not is_valid:
            return jsonify({'error': errors}), 400

        # Create progress log
        progress_log = ProgressLog(
            client_id=session['client_id'],
            workout_completed=True,
            exercise_data=data['exercise_data'],
            notes=data.get('notes', ''),
            metrics=data.get('metrics', {})
        )
        db.session.add(progress_log)

        # Update client's progress and points
        client = Client.query.get(session['client_id'])
        client.points += 10  # Award points for logging workout

        # Log activity
        log_activity(
            client_id=session['client_id'],
            activity_type='workout_completed',
            description='Completed a workout session',
            icon='activity'
        )

        db.session.commit()
        return jsonify({'success': True, 'message': 'Workout logged successfully'})

    except Exception as e:
        logging.error(f"Error logging workout: {str(e)}")
        return jsonify({'error': 'Failed to log workout'}), 500



@app.route('/client/<int:client_id>/adjust-workout', methods=['POST'])
def adjust_workout(client_id):
    """Adjust workout difficulty based on client's performance data"""
    try:
        client = Client.query.get_or_404(client_id)

        # Get recent progress logs
        progress_logs = ProgressLog.query.filter_by(client_id=client_id)\
            .order_by(ProgressLog.log_date.desc())\
            .limit(10)\
            .all()

        # Extract exercise data from logs
        exercise_data = []
        for log in progress_logs:
            if log.exercise_data:
                for exercise in log.exercise_data:
                    # Add completion status based on metrics
                    exercise['completed'] = log.workout_completed
                    # Add form rating based on intensity metric
                    exercise['form_rating'] = log.metrics.get('intensity', 7) if log.metrics else 7
                    exercise_data.append(exercise)

        # Default workout if no logs exist
        base_exercises = [
            {
                'name': 'Push-ups',
                'sets': 3,
                'reps': 10,
                'type': 'strength'
            },
            {
                'name': 'Bodyweight Squats',
                'sets': 3,
                'reps': 12,
                'type': 'strength'
            },
            {
                'name': 'Plank',
                'sets': 3,
                'reps': '30 seconds',
                'type': 'core'
            }
        ]

        # Generate new workout plan with difficulty adjustment
        if exercise_data:
            adjusted_exercises = []
            for exercise in exercise_data:
                # Group exercise data by name
                exercise_history = [e for e in exercise_data if e['name'] == exercise['name']]
                if exercise_history:
                    adjusted = workout_generator.adjust_exercise_difficulty(
                        exercise.copy(),
                        exercise_history,
                        client.fitness_level
                    )
                    if adjusted not in adjusted_exercises:  # Avoid duplicates
                        adjusted_exercises.append(adjusted)
        else:
            # If no exercise data, create a beginner-friendly plan
            adjusted_exercises = base_exercises

        # Create the response workout plan
        workout_plan = {
            'exercises': adjusted_exercises,
            'last_adjusted': datetime.utcnow().isoformat()
        }

        # Log the adjustment
        log_activity(
            client_id=client_id,
            activity_type='workout_adjusted',
            description='Workout difficulty automatically adjusted based on performance',
            icon='sliders',
            priority='normal',
            extra_data={'adjusted_plan': workout_plan}
        )

        return jsonify({
            'success': True,
            'workout_plan': workout_plan
        })

    except Exception as e:
        logging.error(f"Error adjusting workout: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to adjust workout plan'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)