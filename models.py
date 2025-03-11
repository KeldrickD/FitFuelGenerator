from datetime import datetime
from sqlalchemy import or_
from app import db

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
    dietary_preferences = db.relationship('DietaryPreference', backref='client', lazy=True)
    meal_plans = db.relationship('MealPlan', backref='client', lazy=True)
    activities = db.relationship('ActivityFeed', backref='client', lazy=True)
    goals = db.relationship('Goal', backref='client', lazy=True)  # Added goals relationship
    points = db.Column(db.Integer, default=0)  # Total achievement points

class ActivityFeed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # workout, meal, goal, etc.
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    extra_data = db.Column(db.JSON)  # Store additional activity-specific data
    priority = db.Column(db.String(20), default='normal')  # priority level: high, normal, low
    icon = db.Column(db.String(50))  # Feather icon name for the activity
    is_milestone = db.Column(db.Boolean, default=False)  # Mark important achievements

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

class DietaryPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    diet_type = db.Column(db.String(50))  # e.g., vegan, keto, paleo
    excluded_ingredients = db.Column(db.JSON, default=list)
    preferred_ingredients = db.Column(db.JSON, default=list)
    meal_size_preference = db.Column(db.String(20))  # small, medium, large
    meal_count_per_day = db.Column(db.Integer)
    calorie_target = db.Column(db.Integer)
    macro_targets = db.Column(db.JSON)  # Store macronutrient targets
    meal_timing = db.Column(db.JSON)  # Store preferred meal times

class MealPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    daily_plans = db.Column(db.JSON)  # Store daily meal plans
    shopping_list = db.Column(db.JSON)  # Store required ingredients
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    goal_type = db.Column(db.String(50), nullable=False)  # weight_loss, strength, endurance, etc.
    target_value = db.Column(db.Float)  # The target number (e.g., target weight)
    current_value = db.Column(db.Float)  # Current progress
    start_date = db.Column(db.Date, nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, missed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    milestones = db.relationship('GoalMilestone', backref='goal', lazy=True)
    progress_updates = db.relationship('GoalProgress', backref='goal', lazy=True)

class GoalMilestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)
    milestone_value = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    target_date = db.Column(db.Date)
    achieved = db.Column(db.Boolean, default=False)
    achieved_date = db.Column(db.Date)

class GoalProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)
    recorded_value = db.Column(db.Float, nullable=False)
    recorded_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    metrics = db.Column(db.JSON)  # Additional progress metrics

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50), nullable=False)  # workout, nutrition, goals, etc.
    criteria = db.Column(db.JSON)  # Requirements to earn the achievement
    icon = db.Column(db.String(50))  # Feather icon name
    level = db.Column(db.String(20))  # bronze, silver, gold
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ClientAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Float, default=0)  # Progress towards achievement (0-100)
    completed = db.Column(db.Boolean, default=False)

    # Add relationships
    client = db.relationship('Client', backref=db.backref('achievements', lazy=True))
    achievement = db.relationship('Achievement')