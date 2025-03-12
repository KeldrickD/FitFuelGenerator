from datetime import datetime, timedelta
from sqlalchemy import or_, func, desc
from flask_login import UserMixin
import logging
from extensions import db

class Trainer(db.Model):
    __tablename__ = 'trainer'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    business_name = db.Column(db.String(120))
    clients = db.relationship('Client', backref='trainer', lazy=True)
    plans = db.relationship('Plan', backref='trainer', lazy=True)

class Client(db.Model):
    __tablename__ = 'client'
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Added created_at field

    # Add new relationships for challenges and leaderboards
    participated_challenges = db.relationship('Challenge', 
                                           secondary='challenge_participant',
                                           backref='participants_list',
                                           lazy='dynamic')

    def get_active_challenges(self):
        """Get all active challenges for the client"""
        return ChallengeParticipant.query\
            .filter_by(client_id=self.id)\
            .filter(ChallengeParticipant.completed == False)\
            .all()

    def get_global_rank(self):
        """Get client's global ranking"""
        entry = LeaderboardEntry.query\
            .filter_by(client_id=self.id, category='global')\
            .first()
        return entry.rank if entry else None

class ActivityFeed(db.Model):
    __tablename__ = 'activity_feed'
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
    __tablename__ = 'plan'
    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainer.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    workout_plan = db.Column(db.JSON)
    meal_plan = db.Column(db.JSON)
    weekly_budget = db.Column(db.Float)
    training_days = db.Column(db.Integer)

class ProgressLog(db.Model):
    __tablename__ = 'progress_log'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    log_date = db.Column(db.DateTime, default=datetime.utcnow)
    workout_completed = db.Column(db.Boolean, default=False)
    exercise_data = db.Column(db.JSON)  # Stores exercise performance details
    notes = db.Column(db.Text)
    metrics = db.Column(db.JSON)  # Stores key performance metrics
    ai_insights = db.Column(db.JSON)  # Stores AI-generated insights

class ExerciseProgression(db.Model):
    __tablename__ = 'exercise_progression'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    progression_data = db.Column(db.JSON)  # Stores historical progression data
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    current_level = db.Column(db.String(20))  # Current difficulty level
    next_milestone = db.Column(db.JSON)  # Next progression target

class MealIngredient(db.Model):
    __tablename__ = 'meal_ingredient'
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
    __tablename__ = 'substitution_rule'
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('meal_ingredient.id'), nullable=False)
    substitute_id = db.Column(db.Integer, db.ForeignKey('meal_ingredient.id'), nullable=False)
    conversion_ratio = db.Column(db.Float, default=1.0)  # How much substitute to use
    preference_tags = db.Column(db.JSON, default=list)  # e.g., ['vegan', 'gluten-free']
    nutrition_difference = db.Column(db.JSON)  # Difference in key nutrients
    cost_difference = db.Column(db.Float)  # Price difference per serving
    suitability_score = db.Column(db.Float)  # AI-calculated score for substitution

class DietaryPreference(db.Model):
    __tablename__ = 'dietary_preference'
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
    __tablename__ = 'meal_plan'
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
    __tablename__ = 'goal'
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
    __tablename__ = 'goal_milestone'
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)
    milestone_value = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    target_date = db.Column(db.Date)
    achieved = db.Column(db.Boolean, default=False)
    achieved_date = db.Column(db.Date)

class GoalProgress(db.Model):
    __tablename__ = 'goal_progress'
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)
    recorded_value = db.Column(db.Float, nullable=False)
    recorded_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    metrics = db.Column(db.JSON)  # Additional progress metrics

class Achievement(db.Model):
    __tablename__ = 'achievement'
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
    __tablename__ = 'client_achievement'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Float, default=0)  # Progress towards achievement (0-100)
    completed = db.Column(db.Boolean, default=False)

    # Add relationships
    client = db.relationship('Client', backref=db.backref('achievements', lazy=True))
    achievement = db.relationship('Achievement')

class FitnessResource(db.Model):
    __tablename__ = 'fitness_resource'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50), nullable=False)  # 'video' or 'guide'
    content_url = db.Column(db.String(500))
    content = db.Column(db.Text)  # For guides or embedded video content
    difficulty_level = db.Column(db.String(20))  # beginner, intermediate, advanced
    categories = db.Column(db.JSON, default=list)  # Store categories/tags as a list
    thumbnail_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)

    @classmethod
    def search(cls, query, resource_type=None, difficulty=None, category=None):
        """Search fitness resources with filters"""
        base_query = cls.query

        if query:
            search_filter = or_(
                cls.title.ilike(f'%{query}%'),
                cls.description.ilike(f'%{query}%')
            )
            base_query = base_query.filter(search_filter)

        if resource_type:
            base_query = base_query.filter(cls.resource_type == resource_type)

        if difficulty:
            base_query = base_query.filter(cls.difficulty_level == difficulty)

        if category:
            base_query = base_query.filter(cls.categories.contains([category]))

        return base_query.order_by(cls.created_at.desc()).all()

class Challenge(db.Model):
    __tablename__ = 'challenge'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    challenge_type = db.Column(db.String(50), nullable=False)  # workout, steps, nutrition
    target_value = db.Column(db.Float, nullable=False)  # Target number to achieve
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    visibility = db.Column(db.String(20), default='public')  # public, private, friends
    rules = db.Column(db.JSON)  # Store any additional rules or criteria
    reward_points = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    creator = db.relationship('Client', backref='created_challenges', foreign_keys=[created_by])
    participants = db.relationship('ChallengeParticipant', backref='challenge', lazy=True)

    def get_leaderboard(self):
        """Get current leaderboard for this challenge"""
        return ChallengeParticipant.query\
            .filter_by(challenge_id=self.id)\
            .order_by(ChallengeParticipant.current_value.desc())\
            .all()

class ChallengeParticipant(db.Model):
    __tablename__ = 'challenge_participant'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    current_value = db.Column(db.Float, default=0)  # Current progress towards target
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    completion_date = db.Column(db.DateTime)

    # Relationship to access client details
    client = db.relationship('Client', backref='challenge_participations')

    def update_progress(self, new_value):
        """Update participant's progress in the challenge"""
        self.current_value = new_value
        self.last_updated = datetime.utcnow()

        # Check if challenge is completed
        challenge = Challenge.query.get(self.challenge_id)
        if challenge and new_value >= challenge.target_value and not self.completed:
            self.completed = True
            self.completion_date = datetime.utcnow()

            # Award points to client
            self.client.points += challenge.reward_points


class LeaderboardEntry(db.Model):
    __tablename__ = 'leaderboard_entry'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # global, monthly, challenge
    points = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    entry_metadata = db.Column(db.JSON)  # Store additional ranking information

    # Relationship
    client = db.relationship('Client', backref='leaderboard_entries')

    @classmethod
    def update_rankings(cls, category):
        """Update rankings for a specific leaderboard category"""
        entries = cls.query\
            .filter_by(category=category)\
            .order_by(cls.points.desc())\
            .all()

        for index, entry in enumerate(entries, 1):
            entry.rank = index
            entry.last_updated = datetime.utcnow()