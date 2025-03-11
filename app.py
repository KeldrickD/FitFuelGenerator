import os
import logging
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from utils import progression_tracker  # Added import

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    from models import (
        Trainer, Client, Plan, ProgressLog, ExerciseProgression,
        MealIngredient, SubstitutionRule, DietaryPreference, MealPlan,
        ActivityFeed, Goal, GoalMilestone, Achievement, ClientAchievement # Added Achievement and ClientAchievement
    )
    db.create_all()

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
        logging.debug(f"Viewing progress for client_id: {client_id}") #Added logging
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

        # Get activity feed with enhanced details
        activities = ActivityFeed.query\
            .order_by(ActivityFeed.created_at.desc())\
            .limit(20)\
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
                'extra_data': activity.extra_data # Changed metadata to extra_data
            })

        # Add last activity to clients
        for client in clients:
            latest_activity = ActivityFeed.query\
                .filter_by(client_id=client.id)\
                .order_by(ActivityFeed.created_at.desc())\
                .first()

            client.last_activity = latest_activity.created_at.strftime('%Y-%m-%d %H:%M') if latest_activity else None

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
                           activity_feed=activity_feed)

    except Exception as e:
        logging.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard data. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/api/client/<int:client_id>')
def get_client(client_id):
    try:
        logging.debug(f"Fetching client data for client_id: {client_id}") #Added logging
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

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        logging.debug(f"Updating client {client_id} with data: {data}")

        # Update client fields
        client.name = data.get('name', client.name)
        client.goal = data.get('goal', client.goal)
        client.fitness_level = data.get('fitness_level', client.fitness_level)

        try:
            db.session.commit()
            logging.debug(f"Successfully updated client {client_id}")
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            logging.error(f"Database error while updating client: {str(e)}")
            return jsonify({'error': 'Database error occurred'}), 500

    except Exception as e:
        logging.error(f"Error updating client: {str(e)}")
        return jsonify({'error': 'Failed to update client'}), 500

# Add these new routes after the existing routes

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
    schedule = []

    # Define exercise templates based on fitness level
    exercise_templates = {
        'beginner': {
            'upper_body': ['Push-ups (Modified)', 'Dumbbell Rows', 'Wall Push-ups'],
            'lower_body': ['Bodyweight Squats', 'Lunges', 'Calf Raises'],
            'core': ['Plank Hold', 'Bird Dogs', 'Dead Bugs'],
            'cardio': ['Walking', 'Stationary Bike', 'Swimming']
        },
        'intermediate': {
            'upper_body': ['Push-ups', 'Pull-ups', 'Dips'],
            'lower_body': ['Barbell Squats', 'Romanian Deadlifts', 'Box Jumps'],
            'core': ['Planks', 'Russian Twists', 'Mountain Climbers'],
            'cardio': ['Running', 'HIIT Intervals', 'Rowing']
        },
        'advanced': {
            'upper_body': ['Weighted Push-ups', 'Weighted Pull-ups', 'Ring Dips'],
            'lower_body': ['Front Squats', 'Deadlifts', 'Plyometric Lunges'],
            'core': ['Dragon Flags', 'Ab Wheel Rollouts', 'Hanging Leg Raises'],
            'cardio': ['Sprinting', 'Complex HIIT', 'CrossFit WODs']
        }
    }

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
                if area in exercise_templates[fitness_level]:
                    exercises = exercise_templates[fitness_level][area]
                    workout['exercises'].extend([
                        {
                            'name': exercise,
                            'sets': 3,
                            'reps': '8-12',
                            'rest': '60 sec'
                        }
                        for exercise in exercises[:2]  # Pick 2 exercises per area
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

    # Determine diet type based on restrictions
    diet_type = 'standard'
    if 'vegan' in dietary_restrictions:
        diet_type = 'vegan'
    elif 'vegetarian' in dietary_restrictions:
        diet_type = 'vegetarian'

    schedule = []
    meal_times = ['breakfast', 'lunch', 'dinner'][:meals_per_day]

    # Generate 7 days of meals
    for day in range(7):
        daily_meals = {}
        for meal_time in meal_times:
            daily_meals[meal_time] = {
                'suggestion': meal_templates[diet_type][meal_time][day % 3],
                'macros': calculate_macros(meal_templates[diet_type][meal_time][day % 3], diet_type)
            }
        schedule.append({
            'day': day + 1,
            'meals': daily_meals
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
            meal_timing={}  # You can format meal timing data here
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
        client= Client.query.get_or_404(client_id) if client_id else None
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
    try:
        client = Client.query.get_or_404(client_id)

        # Get all achievements and client's progress
        achievements = Achievement.query.all()
        client_achievements = ClientAchievement.query.filter_by(client_id=client_id).all()

        # Get personalized recommendations
        recommended_achievements = Achievement.get_recommendations(client_id)

        # Create achievement progress map
        progress_map = {
            ca.achievement_id: {
                'progress': ca.progress,
                'completed': ca.completed,
                'earned_at': ca.earned_at
            }
            for ca in client_achievements
        }

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
        return redirect(url_for('dashboard'))

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

if __name__ == '__main__':
    app.run(debug=True)