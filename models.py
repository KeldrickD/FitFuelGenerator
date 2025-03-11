from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import or_

# Create db instance
db = SQLAlchemy()

class Trainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    business_name = db.Column(db.String(120))
    clients = db.relationship('Client', backref='trainer', lazy=True)
    plans = db.relationship('Plan', backref='trainer', lazy=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainer.id'), nullable=False)
    fitness_level = db.Column(db.String(20), nullable=False)
    diet_preference = db.Column(db.String(50))
    goal = db.Column(db.String(50))
    plans = db.relationship('Plan', backref='client', lazy=True)
    progress_logs = db.relationship('ProgressLog', backref='client', lazy=True)
    allergies = db.Column(db.JSON, default=list)  # Store allergies as a list

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainer.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    workout_plan = db.Column(db.JSON)
    meal_plan = db.Column(db.JSON)
    weekly_budget = db.Column(db.Float)
    training_days = db.Column(db.Integer)

class ProgressLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    log_date = db.Column(db.DateTime, default=datetime.utcnow)
    workout_completed = db.Column(db.Boolean, default=False)
    exercise_data = db.Column(db.JSON)  # Stores exercise performance details
    notes = db.Column(db.Text)
    metrics = db.Column(db.JSON)  # Stores key performance metrics
    ai_insights = db.Column(db.JSON)  # Stores AI-generated insights

class ExerciseProgression(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    progression_data = db.Column(db.JSON)  # Stores historical progression data
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    current_level = db.Column(db.String(20))  # Current difficulty level
    next_milestone = db.Column(db.JSON)  # Next progression target

class MealIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., protein, carb, vegetable
    nutrition_per_100g = db.Column(db.JSON)  # Nutritional information
    common_allergens = db.Column(db.JSON, default=list)
    estimated_cost = db.Column(db.Float)  # Cost per standard serving
    substitutes = db.relationship(
        'SubstitutionRule',
        primaryjoin="or_(MealIngredient.id==SubstitutionRule.ingredient_id, MealIngredient.id==SubstitutionRule.substitute_id)",
        lazy='dynamic'
    )

class SubstitutionRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('meal_ingredient.id'), nullable=False)
    substitute_id = db.Column(db.Integer, db.ForeignKey('meal_ingredient.id'), nullable=False)
    conversion_ratio = db.Column(db.Float, default=1.0)  # How much substitute to use
    preference_tags = db.Column(db.JSON, default=list)  # e.g., ['vegan', 'gluten-free']
    nutrition_difference = db.Column(db.JSON)  # Difference in key nutrients
    cost_difference = db.Column(db.Float)  # Price difference per serving
    suitability_score = db.Column(db.Float)  # AI-calculated score for substitution