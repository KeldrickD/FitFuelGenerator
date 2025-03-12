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

def configure_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("Starting Fitness Management Platform")

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure logging
configure_logging()

# Log configuration status (without exposing secrets)
logging.info("Checking configuration...")
for key in ['DATABASE_URL', 'SESSION_SECRET', 'OPENAI_API_KEY']:
    logging.info(f"Environment variable {key} is {'set' if os.environ.get(key) else 'not set'}")

# Configure the database 
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

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
def dashboard():
    """Dashboard page"""
    try:
        logging.info("Rendering dashboard page")
        return render_template('dashboard.html')
    except Exception as e:
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

@app.route('/clients-list')
def clients_list():
    """Clients list page"""
    try:
        logging.info("Rendering clients list page")
        return render_template('clients.html')
    except Exception as e:
        logging.error(f"Error serving clients list page: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Initialize database tables only
try:
    with app.app_context():
        logging.info("Starting database initialization...")

        # First, just create the tables
        try:
            logging.info("Creating database tables...")
            db.create_all()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Failed to create database tables: {str(e)}")
            raise

        logging.info("Basic application initialization completed successfully")
except Exception as e:
    logging.error(f"Critical error during application initialization: {str(e)}")
    raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)