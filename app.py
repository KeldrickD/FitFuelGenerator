import os
import logging
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from flask_smorest import Api, Blueprint, abort
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
from flask_mail import Mail
from extensions import db, socketio
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
from utils.email_service import mail
from utils.scheduler import init_scheduler
import time
from routes.client_portal import client_portal

def configure_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("Starting Fitness Management Platform")

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    socketio.init_app(app)
    CORS(app)
    
    # Initialize API documentation
    api = Api(app)
    
    # Initialize Prometheus metrics
    metrics = PrometheusMetrics(app)
    
    # Initialize rate limiter
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Initialize scheduler
    with app.app_context():
        init_scheduler(app)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.clients import clients_bp
    from routes.dashboard import dashboard_bp
    from routes.api import api_bp
    app.register_blueprint(client_portal)
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    
    return app

# Create the app
app = create_app()

# Configure logging
configure_logging()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Rate Limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Initialize Caching
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Initialize Prometheus metrics
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Application info', version='1.0.0')

# Request latency metrics
@metrics.histogram('request_latency_seconds', 'Request latency in seconds',
                  labels={'path': lambda: request.path})
@app.before_request
def before_request():
    request._prometheus_start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(request, '_prometheus_start_time'):
        latency = time.time() - request._prometheus_start_time
        metrics.histogram('request_latency_seconds').observe(latency)
    return response

# Initialize API documentation
api = Api(app)

# Define API schemas
@api.schema('Trainer')
class TrainerSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    business_name = fields.Str()

@api.schema('Client')
class ClientSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    fitness_level = fields.Str(required=True)
    goal = fields.Str(required=True)
    diet_preference = fields.Str()

# Create API blueprints
api_bp = Blueprint('api', 'api', url_prefix='/api/v1')

@api_bp.route('/clients')
@api_bp.response(200, ClientSchema(many=True))
@login_required
def get_clients():
    """Get all clients for the current trainer"""
    clients = Client.query.filter_by(trainer_id=current_user.id).all()
    return clients

@api_bp.route('/clients/<int:client_id>')
@api_bp.response(200, ClientSchema)
@login_required
def get_client(client_id):
    """Get a specific client by ID"""
    client = Client.query.filter_by(id=client_id, trainer_id=current_user.id).first_or_404()
    return client

# Register blueprint with API
api.register_blueprint(api_bp)

@login_manager.user_loader
def load_user(user_id):
    return Trainer.query.get(int(user_id))

# Configure the database 
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///fitfuel.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        business_name = request.form.get('business_name')

        if not all([username, email, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('register'))

        if Trainer.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))

        if Trainer.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('register'))

        trainer = Trainer(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            business_name=business_name
        )

        try:
            db.session.add(trainer)
            db.session.commit()
            login_user(trainer)
            flash('Registration successful!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during registration: {str(e)}")
            flash('An error occurred during registration', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        if not all([email, password]):
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))

        trainer = Trainer.query.filter_by(email=email).first()

        if trainer and check_password_hash(trainer.password_hash, password):
            login_user(trainer, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Basic health check endpoint"""
    try:
        logging.info("Health check request received")
        # Test database connection with session management
        with db.session.begin():
            # Simple query that doesn't affect data
            db.session.execute('SELECT 1').scalar()

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat(),
            'app_initialized': True
        })
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Health check failed: {error_msg}")
        return jsonify({
            'status': 'unhealthy',
            'error': error_msg,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/')
def index():
    """Basic index page"""
    try:
        logging.info("Rendering index page")
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Error serving index page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/fitness-quiz')
def fitness_quiz():
    """Fitness quiz page"""
    try:
        logging.info("Rendering fitness quiz page")
        return render_template('fitness_quiz.html')
    except Exception as e:
        logging.error(f"Error serving fitness quiz page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/resource-library')
def resource_library():
    """Resource library page"""
    try:
        logging.info("Rendering resource library page")
        return render_template('resource_library.html')
    except Exception as e:
        logging.error(f"Error serving resource library page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/challenges')
def challenges():
    """Challenges page"""
    try:
        logging.info("Rendering challenges page")
        return render_template('challenges.html')
    except Exception as e:
        logging.error(f"Error serving challenges page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard')
@login_required
@cache.memoize(timeout=300)
def dashboard():
    """Dashboard page"""
    try:
        logging.info("Rendering dashboard page")
        clients = Client.query.filter_by(trainer_id=current_user.id).all()
        recent_activities = ActivityFeed.query\
            .join(Client)\
            .filter(Client.trainer_id == current_user.id)\
            .order_by(ActivityFeed.created_at.desc())\
            .limit(10)\
            .all()
        
        return render_template(
            'dashboard.html',
            clients=clients,
            recent_activities=recent_activities
        )
    except Exception as e:
        cache.delete_memoized(dashboard)
        logging.error(f"Error serving dashboard page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/meal-planner-wizard')
def meal_planner_wizard():
    """Meal planner wizard page"""
    try:
        logging.info("Rendering meal planner wizard page")
        return render_template('meal_planner_wizard.html')
    except Exception as e:
        logging.error(f"Error serving meal planner wizard page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/meal-substitutions')
def meal_substitutions():
    """Meal substitutions page"""
    try:
        logging.info("Rendering meal substitutions page")
        return render_template('meal_substitutions.html')
    except Exception as e:
        logging.error(f"Error serving meal substitutions page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/clients')
@login_required
@cache.memoize(timeout=300)
def clients_list():
    """Clients list page"""
    try:
        logging.info("Rendering clients list page")
        clients = Client.query.filter_by(trainer_id=current_user.id).all()
        return render_template('clients.html', clients=clients)
    except Exception as e:
        cache.delete_memoized(clients_list)
        logging.error(f"Error serving clients list page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    """Add new client page"""
    if request.method == 'POST':
        try:
            # Create new client
            client = Client(
                trainer_id=current_user.id,
                name=request.form['name'],
                email=request.form['email'],
                fitness_level=request.form['fitness_level'],
                goal=request.form['goal'],
                diet_preference=request.form['diet_preference'],
                allergies=request.form.get('allergies', '').split(','),
                created_at=datetime.utcnow()
            )

            # Create dietary preferences
            diet_pref = DietaryPreference(
                client=client,
                diet_type=request.form['diet_preference'],
                meal_count_per_day=3,  # Default value
                calorie_target=2000,  # Default value, should be calculated based on client's data
                macro_targets={
                    'protein': 30,
                    'carbs': 40,
                    'fats': 30
                }  # Default macros split
            )

            # Create initial goal
            goal = Goal(
                client=client,
                goal_type=request.form['goal'],
                description=f"Initial {request.form['goal'].replace('_', ' ')} goal",
                start_date=datetime.utcnow().date(),
                target_date=(datetime.utcnow() + timedelta(days=90)).date(),  # 90-day default goal
                status='in_progress'
            )

            # Add activity feed entry
            activity = ActivityFeed(
                client=client,
                activity_type='registration',
                description=f"New client registered with goal: {request.form['goal'].replace('_', ' ')}",
                priority='high',
                icon='user-plus'
            )

            db.session.add(client)
            db.session.add(diet_pref)
            db.session.add(goal)
            db.session.add(activity)
            db.session.commit()

            flash('Client added successfully!', 'success')
            return redirect(url_for('view_client', client_id=client.id))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding client: {str(e)}")
            flash('An error occurred while adding the client', 'error')
            return redirect(url_for('add_client'))

    return render_template('add_client.html')

@app.route('/clients/<int:client_id>')
@login_required
def view_client(client_id):
    """View client details page"""
    try:
        client = Client.query.filter_by(id=client_id, trainer_id=current_user.id).first_or_404()
        
        # Get recent activities
        recent_activities = ActivityFeed.query\
            .filter_by(client_id=client_id)\
            .order_by(ActivityFeed.created_at.desc())\
            .limit(5)\
            .all()

        # Get active plan
        active_plan = Plan.query\
            .filter_by(client_id=client_id, status='active')\
            .order_by(Plan.created_at.desc())\
            .first()

        # Get progress data
        progress_logs = ProgressLog.query\
            .filter_by(client_id=client_id)\
            .order_by(ProgressLog.log_date.desc())\
            .limit(10)\
            .all()

        # Get goals
        goals = Goal.query\
            .filter_by(client_id=client_id)\
            .order_by(Goal.created_at.desc())\
            .all()

        return render_template(
            'view_client.html',
            client=client,
            recent_activities=recent_activities,
            active_plan=active_plan,
            progress_logs=progress_logs,
            goals=goals
        )
    except Exception as e:
        logging.error(f"Error viewing client: {str(e)}")
        flash('An error occurred while loading client data', 'error')
        return redirect(url_for('clients_list'))

@app.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    """Edit client details page"""
    try:
        client = Client.query.filter_by(id=client_id, trainer_id=current_user.id).first_or_404()

        if request.method == 'POST':
            client.name = request.form['name']
            client.email = request.form['email']
            client.fitness_level = request.form['fitness_level']
            client.goal = request.form['goal']
            client.diet_preference = request.form['diet_preference']
            client.allergies = request.form.get('allergies', '').split(',')

            # Update dietary preferences
            diet_pref = client.dietary_preferences[0] if client.dietary_preferences else DietaryPreference(client=client)
            diet_pref.diet_type = request.form['diet_preference']
            
            if not client.dietary_preferences:
                db.session.add(diet_pref)

            # Add activity feed entry
            activity = ActivityFeed(
                client=client,
                activity_type='profile_update',
                description='Client profile updated',
                priority='normal',
                icon='edit'
            )
            db.session.add(activity)

            db.session.commit()
            flash('Client updated successfully!', 'success')
            return redirect(url_for('view_client', client_id=client.id))

        return render_template('edit_client.html', client=client)
    except Exception as e:
        logging.error(f"Error editing client: {str(e)}")
        flash('An error occurred while updating client data', 'error')
        return redirect(url_for('view_client', client_id=client_id))

@app.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    """Delete client"""
    try:
        client = Client.query.filter_by(id=client_id, trainer_id=current_user.id).first_or_404()
        db.session.delete(client)
        db.session.commit()
        flash('Client deleted successfully', 'success')
        return redirect(url_for('clients_list'))
    except Exception as e:
        logging.error(f"Error deleting client: {str(e)}")
        flash('An error occurred while deleting the client', 'error')
        return redirect(url_for('view_client', client_id=client_id))

@app.before_first_request
def initialize_database():
    """Initialize database tables"""
    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Failed to create database tables: {str(e)}")
        raise

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)