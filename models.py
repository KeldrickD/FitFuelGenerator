from datetime import datetime, timedelta
from sqlalchemy import or_, func, desc
from app import db
import logging

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
    difficulty = db.Column(db.Integer, default=1)  # 1-5 scale

    @classmethod
    def get_recommendations(cls, client_id, limit=3):
        """Get personalized achievement recommendations for a client"""
        try:
            # Get client info
            client = Client.query.get(client_id)
            if not client:
                return []

            # Get client's current achievements
            completed_achievements = {
                ca.achievement_id: ca.progress 
                for ca in ClientAchievement.query.filter_by(client_id=client_id).all()
            }

            # Get all available achievements
            all_achievements = cls.query.all()
            recommendations = []

            for achievement in all_achievements:
                if achievement.id not in completed_achievements:
                    # Calculate recommendation score
                    score = achievement.calculate_compatibility_score(client)
                    if score > 0:
                        recommendations.append({
                            'achievement': achievement,
                            'score': score,
                            'reason': achievement.get_recommendation_reason(client)
                        })

            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:limit]

        except Exception as e:
            logging.error(f"Error getting achievement recommendations: {str(e)}")
            return []

    def calculate_compatibility_score(self, client):
        """Calculate how compatible this achievement is for the client"""
        try:
            base_score = 100
            logging.debug(f"Starting compatibility calculation for achievement {self.name} and client {client.id}")

            # Adjust score based on client's fitness level
            level_mapping = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            client_level = level_mapping.get(client.fitness_level, 1)
            level_diff = abs(client_level - self.difficulty)
            level_adjustment = level_diff * 15  # Increased impact of level difference
            base_score -= level_adjustment

            logging.debug(f"After level adjustment ({level_diff} levels diff): {base_score}")

            # Check if achievement type matches client's goal
            goal_bonus = 0
            if (self.type == 'workout' and client.goal == 'consistency') or \
               (self.type == 'strength' and client.goal == 'muscle_gain') or \
               (self.type == 'nutrition' and client.goal == 'weight_loss') or \
               (self.type == 'endurance' and client.goal == 'endurance'):
                goal_bonus = 25  # Increased bonus for matching goals
                base_score += goal_bonus
                logging.debug(f"Added goal bonus: +{goal_bonus}")

            # Analyze recent activity patterns
            recent_logs = ProgressLog.query.filter_by(client_id=client.id)\
                .filter(ProgressLog.log_date >= datetime.utcnow() - timedelta(days=30))\
                .order_by(desc(ProgressLog.log_date)).all()

            activity_bonus = 0
            if recent_logs:
                # Calculate activity frequency
                activity_days = len(recent_logs)
                if activity_days >= 12:  # Active in last month
                    activity_bonus = 20
                elif activity_days >= 8:
                    activity_bonus = 15
                elif activity_days >= 4:
                    activity_bonus = 10

                base_score += activity_bonus
                logging.debug(f"Added activity bonus: +{activity_bonus}")

                # Check workout completion rate
                completion_rate = sum(1 for log in recent_logs if log.workout_completed) / len(recent_logs)
                completion_bonus = int(completion_rate * 15)  # Adjusted completion impact
                base_score += completion_bonus
                logging.debug(f"Added completion bonus: +{completion_bonus}")

            final_score = max(0, min(base_score, 100))  # Keep score between 0-100
            logging.debug(f"Final compatibility score: {final_score}")
            return final_score

        except Exception as e:
            logging.error(f"Error calculating compatibility score: {str(e)}")
            return 0

    def get_recommendation_reason(self, client):
        """Get a personalized reason why this achievement is recommended"""
        try:
            recent_logs = ProgressLog.query.filter_by(client_id=client.id)\
                .filter(ProgressLog.log_date >= datetime.utcnow() - timedelta(days=30))\
                .all()

            activity_count = len(recent_logs)
            completion_rate = sum(1 for log in recent_logs if log.workout_completed) / max(1, activity_count)

            # Dynamic reason based on multiple factors
            reasons = []

            # Match with client's goal
            if self.type == client.goal:
                reasons.append("Perfectly aligned with your fitness goals")

            # Activity level based reason
            if activity_count >= 12:
                reasons.append("You're consistently active")
            elif activity_count >= 8:
                reasons.append("You're building a good workout routine")
            elif activity_count >= 4:
                reasons.append("Great for maintaining your progress")

            # Completion rate based reason
            if completion_rate >= 0.8:
                reasons.append("You're excellent at completing workouts")
            elif completion_rate >= 0.6:
                reasons.append("You're committed to your training")

            # Difficulty level based reason
            level_mapping = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            client_level = level_mapping.get(client.fitness_level, 1)

            if self.difficulty == client_level:
                reasons.append("Matches your current fitness level")
            elif self.difficulty == client_level + 1:
                reasons.append("A good challenge for your next step")
            elif self.difficulty < client_level:
                reasons.append("A quick win to boost your momentum")

            # Select the most relevant reason
            if reasons:
                return reasons[0]

            return "Recommended based on your profile"

        except Exception as e:
            logging.error(f"Error getting recommendation reason: {str(e)}")
            return "Recommended based on your profile"

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