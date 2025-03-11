import os
import logging
from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///fitfuel.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Import route handlers
from utils import workout_generator, meal_generator, pdf_generator
from models import Trainer, Client, Plan

@app.route('/')
def index():
    return render_template('index.html')

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

with app.app_context():
    db.create_all()
