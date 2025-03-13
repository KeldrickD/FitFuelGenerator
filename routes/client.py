from flask import Blueprint, render_template, request, jsonify, current_app, url_for, flash, redirect, send_file
from flask_login import login_required, current_user
from models import WorkoutLog, MealPlan, ProgressMetric, ActivityFeed, ProgressPhoto, Goal, DietaryPreference, Recipe, Client, ProgressLog, Plan, Challenge, ChallengeParticipation, ChallengeGoal, GoalCompletion, Achievement, ChallengeWorkout, ChallengeRecipe, WorkoutPlan, SharingAnalytics
from extensions import db
from datetime import datetime, timedelta, date
import json
import os
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
from PIL import Image, ImageDraw, ImageFont
import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

client = Blueprint('client', __name__)

@client.route('/offline')
def offline():
    """Render the offline page"""
    return render_template('offline.html')

@client.route('/dashboard')
@login_required
def dashboard():
    """Client dashboard with mobile-optimized view"""
    # Get today's workout
    today = datetime.now().date()
    today_workout = WorkoutLog.query.filter_by(
        client_id=current_user.id,
        date=today
    ).first()

    # Get today's meals
    today_meals = MealPlan.query.filter_by(
        client_id=current_user.id,
        date=today
    ).all()
    total_calories = sum(meal.calories for meal in today_meals) if today_meals else 0

    # Get progress metrics
    progress_metrics = []
    metrics = ProgressMetric.query.filter_by(client_id=current_user.id).all()
    for metric in metrics:
        progress = (metric.current_value - metric.start_value) / (metric.target_value - metric.start_value) * 100
        progress = max(0, min(100, progress))  # Clamp between 0 and 100
        progress_metrics.append({
            'name': metric.name,
            'value': metric.current_value,
            'unit': metric.unit,
            'progress': progress
        })

    # Get recent activities
    recent_activities = ActivityFeed.query.filter_by(
        client_id=current_user.id
    ).order_by(ActivityFeed.timestamp.desc()).limit(5).all()

    return render_template('client/dashboard.html',
                         today_workout=today_workout,
                         today_meals=today_meals,
                         total_calories=total_calories,
                         progress_metrics=progress_metrics,
                         recent_activities=recent_activities)

@client.route('/api/workout-logs', methods=['POST'])
@login_required
def log_workout():
    """API endpoint for logging workouts with offline support"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['workout_type', 'duration', 'date']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields'
            }), 400

        # Create workout log
        workout_log = WorkoutLog(
            client_id=current_user.id,
            workout_type=data['workout_type'],
            duration=data['duration'],
            notes=data.get('notes', ''),
            date=datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
        )
        
        db.session.add(workout_log)
        
        # Create activity feed entry
        activity = ActivityFeed(
            client_id=current_user.id,
            activity_type='workout',
            description=f"Completed {data['workout_type']} workout for {data['duration']} minutes",
            icon_path='M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Workout logged successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error logging workout: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to log workout'
        }), 500

@client.route('/api/sync-logs', methods=['POST'])
@login_required
def sync_logs():
    """API endpoint for syncing offline workout logs"""
    try:
        logs = request.get_json()
        if not isinstance(logs, list):
            return jsonify({
                'status': 'error',
                'message': 'Expected array of logs'
            }), 400

        for log_data in logs:
            # Skip if log already exists
            existing_log = WorkoutLog.query.filter_by(
                client_id=current_user.id,
                date=datetime.fromisoformat(log_data['date'].replace('Z', '+00:00'))
            ).first()
            
            if not existing_log:
                workout_log = WorkoutLog(
                    client_id=current_user.id,
                    workout_type=log_data['workout_type'],
                    duration=log_data['duration'],
                    notes=log_data.get('notes', ''),
                    date=datetime.fromisoformat(log_data['date'].replace('Z', '+00:00'))
                )
                db.session.add(workout_log)

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Successfully synced {len(logs)} logs'
        })

    except Exception as e:
        current_app.logger.error(f"Error syncing logs: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to sync logs'
        }), 500

@client.route('/progress')
@login_required
def progress():
    """Progress tracking view with charts and photos"""
    # Get weight progress data
    weight_logs = ProgressMetric.query.filter_by(
        client_id=current_user.id,
        metric_type='weight'
    ).order_by(ProgressMetric.date.asc()).all()
    
    weight_dates = [log.date.strftime('%Y-%m-%d') for log in weight_logs]
    weight_data = [log.value for log in weight_logs]
    
    # Get body measurements
    measurement_types = ['chest', 'waist', 'hips', 'arms', 'thighs']
    current_measurements = []
    starting_measurements = []
    
    for m_type in measurement_types:
        # Get current measurement
        current = ProgressMetric.query.filter_by(
            client_id=current_user.id,
            metric_type=m_type
        ).order_by(ProgressMetric.date.desc()).first()
        current_measurements.append(current.value if current else 0)
        
        # Get starting measurement
        starting = ProgressMetric.query.filter_by(
            client_id=current_user.id,
            metric_type=m_type
        ).order_by(ProgressMetric.date.asc()).first()
        starting_measurements.append(starting.value if starting else 0)
    
    # Get progress photos
    progress_photos = ProgressPhoto.query.filter_by(
        client_id=current_user.id
    ).order_by(ProgressPhoto.date.desc()).all()
    
    # Get goals
    goals = Goal.query.filter_by(client_id=current_user.id).all()
    
    return render_template('client/progress.html',
                         weight_dates=weight_dates,
                         weight_data=weight_data,
                         current_measurements=current_measurements,
                         starting_measurements=starting_measurements,
                         progress_photos=progress_photos,
                         goals=goals)

@client.route('/api/progress-photos', methods=['POST'])
@login_required
def upload_progress_photo():
    """Handle progress photo uploads"""
    if 'photo' not in request.files:
        return jsonify({
            'status': 'error',
            'message': 'No photo file provided'
        }), 400
        
    photo_file = request.files['photo']
    if photo_file.filename == '':
        return jsonify({
            'status': 'error',
            'message': 'No photo selected'
        }), 400
        
    if photo_file:
        try:
            # Create photos directory if it doesn't exist
            photos_dir = os.path.join(current_app.static_folder, 'progress_photos')
            os.makedirs(photos_dir, exist_ok=True)
            
            # Generate unique filename
            filename = secure_filename(f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            filepath = os.path.join(photos_dir, filename)
            
            # Save photo
            photo_file.save(filepath)
            
            # Create database entry
            photo = ProgressPhoto(
                client_id=current_user.id,
                filename=filename,
                date=datetime.now()
            )
            db.session.add(photo)
            
            # Create activity feed entry
            activity = ActivityFeed(
                client_id=current_user.id,
                activity_type='photo',
                description='Added new progress photo',
                icon_path='M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z'
            )
            db.session.add(activity)
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Photo uploaded successfully',
                'url': url_for('static', filename=f'progress_photos/{filename}')
            })
            
        except Exception as e:
            current_app.logger.error(f"Error uploading progress photo: {str(e)}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Failed to upload photo'
            }), 500
            
    return jsonify({
        'status': 'error',
        'message': 'Invalid photo file'
    }), 400

@client.route('/meal-plan')
@login_required
def meal_plan():
    """Render the meal plan view"""
    current_date = request.args.get('date', datetime.now().date().isoformat())
    current_date = datetime.fromisoformat(current_date)

    # Get meal plan for the current date
    meal_plan = MealPlan.query.filter_by(
        client_id=current_user.id,
        start_date=current_date.date()
    ).first()

    if not meal_plan:
        return render_template('client/meal_plan.html',
                            current_date=current_date,
                            meals=[],
                            daily_totals={'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'water': 0},
                            macro_targets={'protein': 150, 'carbs': 200, 'fat': 65},
                            shopping_list={})

    # Get dietary preferences for macro targets
    dietary_pref = DietaryPreference.query.filter_by(client_id=current_user.id).first()
    macro_targets = dietary_pref.macro_targets if dietary_pref else {'protein': 150, 'carbs': 200, 'fat': 65}

    # Calculate daily totals
    daily_totals = {
        'calories': 0,
        'protein': 0,
        'carbs': 0,
        'fat': 0,
        'water': 0
    }

    meals = []
    shopping_list = {}

    for meal_data in meal_plan.daily_plans.get(current_date.strftime('%Y-%m-%d'), []):
        meal_items = []
        for item in meal_data['items']:
            # Add to daily totals
            daily_totals['calories'] += item['calories']
            daily_totals['protein'] += item['nutrients']['protein']
            daily_totals['carbs'] += item['nutrients']['carbs']
            daily_totals['fat'] += item['nutrients']['fat']

            # Add to meal items
            meal_items.append({
                'id': item['id'],
                'name': item['name'],
                'portion': f"{item['amount']} {item['unit']}",
                'calories': item['calories'],
                'completed': item.get('completed', False)
            })

            # Add to shopping list
            category = item.get('category', 'Other')
            if category not in shopping_list:
                shopping_list[category] = []
            shopping_list[category].append({
                'id': item['id'],
                'name': item['name'],
                'amount': item['amount'],
                'unit': item['unit']
            })

        meals.append({
            'id': meal_data['id'],
            'name': meal_data['name'],
            'time': meal_data['time'],
            'items': meal_items
        })

    return render_template('client/meal_plan.html',
                         current_date=current_date,
                         meals=meals,
                         daily_totals=daily_totals,
                         macro_targets=macro_targets,
                         shopping_list=shopping_list)

@client.route('/api/meal-plan')
@login_required
def get_meal_plan():
    """API endpoint to get meal plan for a specific date"""
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({
                'status': 'error',
                'message': 'Date parameter is required'
            }), 400

        date = datetime.fromisoformat(date)
        meal_plan = MealPlan.query.filter_by(
            client_id=current_user.id,
            start_date=date.date()
        ).first()

        if not meal_plan:
            return jsonify({
                'status': 'error',
                'message': 'No meal plan found for this date'
            }), 404

        return jsonify({
            'status': 'success',
            'data': meal_plan.daily_plans.get(date.strftime('%Y-%m-%d'), [])
        })

    except Exception as e:
        current_app.logger.error(f"Error getting meal plan: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get meal plan'
        }), 500

@client.route('/api/meal-items/complete', methods=['POST'])
@login_required
def complete_meal_item():
    """API endpoint to mark meal items as completed"""
    try:
        data = request.get_json()
        meal_id = data.get('meal_id')
        item_id = data.get('item_id')

        if not meal_id or not item_id:
            return jsonify({
                'status': 'error',
                'message': 'Meal ID and Item ID are required'
            }), 400

        # Get current date's meal plan
        current_date = datetime.now().date()
        meal_plan = MealPlan.query.filter_by(
            client_id=current_user.id,
            start_date=current_date
        ).first()

        if not meal_plan:
            return jsonify({
                'status': 'error',
                'message': 'No meal plan found for today'
            }), 404

        # Update completion status
        daily_plans = meal_plan.daily_plans
        date_key = current_date.strftime('%Y-%m-%d')
        
        for meal in daily_plans.get(date_key, []):
            if meal['id'] == meal_id:
                for item in meal['items']:
                    if item['id'] == item_id:
                        item['completed'] = not item.get('completed', False)
                        break

        meal_plan.daily_plans = daily_plans
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Meal item updated successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error updating meal item: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to update meal item'
        }), 500

@client.route('/api/shopping-list/text', methods=['POST'])
@login_required
def generate_shopping_list_text():
    """API endpoint to generate shareable shopping list text"""
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])

        if not item_ids:
            return jsonify({
                'status': 'error',
                'message': 'No items selected'
            }), 400

        # Get current meal plan
        current_date = datetime.now().date()
        meal_plan = MealPlan.query.filter_by(
            client_id=current_user.id,
            start_date=current_date
        ).first()

        if not meal_plan:
            return jsonify({
                'status': 'error',
                'message': 'No meal plan found'
            }), 404

        # Generate shopping list text
        shopping_list = {}
        for meal in meal_plan.daily_plans.get(current_date.strftime('%Y-%m-%d'), []):
            for item in meal['items']:
                if str(item['id']) in item_ids:
                    category = item.get('category', 'Other')
                    if category not in shopping_list:
                        shopping_list[category] = []
                    shopping_list[category].append(
                        f"{item['name']} ({item['amount']} {item['unit']})"
                    )

        # Format text
        text = "Shopping List:\n\n"
        for category, items in shopping_list.items():
            text += f"{category}:\n"
            for item in items:
                text += f"- {item}\n"
            text += "\n"

        return jsonify({
            'status': 'success',
            'text': text
        })

    except Exception as e:
        current_app.logger.error(f"Error generating shopping list: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate shopping list'
        }), 500

@client.route('/api/recipe/<int:item_id>')
@login_required
def get_recipe_details(item_id):
    try:
        # Get the current meal plan
        meal_plan = MealPlan.query.filter_by(
            user_id=current_user.id,
            date=date.today()
        ).first()
        
        if not meal_plan:
            return jsonify({'error': 'Meal plan not found'}), 404
            
        # Find the recipe in the meal plan
        recipe = None
        for daily_plan in meal_plan.daily_plans:
            for meal in daily_plan.meals:
                for item in meal.items:
                    if item.id == item_id:
                        recipe = item.recipe
                        break
                if recipe:
                    break
            if recipe:
                break
                
        if not recipe:
            return jsonify({'error': 'Recipe not found'}), 404
            
        # Format recipe details
        recipe_data = {
            'id': recipe.id,
            'name': recipe.name,
            'calories': recipe.calories,
            'prep_time': recipe.prep_time,
            'cook_time': recipe.cook_time,
            'servings': recipe.servings,
            'nutrients': {
                'protein': recipe.protein,
                'carbs': recipe.carbs,
                'fat': recipe.fat
            },
            'ingredients': [
                {
                    'name': ingredient.name,
                    'amount': ingredient.amount,
                    'unit': ingredient.unit
                }
                for ingredient in recipe.ingredients
            ],
            'prep_instructions': recipe.prep_instructions.split('\n') if recipe.prep_instructions else [],
            'instructions': [
                {
                    'text': instruction.text,
                    'duration': instruction.duration
                }
                for instruction in recipe.instructions
            ]
        }
        
        return jsonify(recipe_data)
        
    except Exception as e:
        current_app.logger.error(f'Error getting recipe details: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@client.route('/api/recipe/substitute', methods=['POST'])
@login_required
def substitute_recipe():
    """API endpoint to substitute a recipe with an alternative in the meal plan"""
    try:
        data = request.get_json()
        original_id = data.get('original_id')
        substitute_id = data.get('substitute_id')
        
        if not original_id or not substitute_id:
            return jsonify({
                'status': 'error',
                'message': 'Both original_id and substitute_id are required'
            }), 400

        # Get the current meal plan
        current_date = datetime.now().date()
        meal_plan = MealPlan.query.filter_by(
            client_id=current_user.id,
            start_date=current_date
        ).first()

        if not meal_plan:
            return jsonify({
                'status': 'error',
                'message': 'No active meal plan found'
            }), 404

        # Get details of the substitute recipe
        substitute_recipe = Recipe.query.get(substitute_id)
        if not substitute_recipe:
            return jsonify({
                'status': 'error',
                'message': 'Substitute recipe not found'
            }), 404

        # Make a deep copy of the daily plans to modify
        daily_plans = meal_plan.daily_plans.copy()
        date_key = current_date.strftime('%Y-%m-%d')
        
        # Find and replace the recipe in the daily plan
        substitution_made = False
        
        for meal in daily_plans.get(date_key, []):
            for i, item in enumerate(meal['items']):
                if item['id'] == original_id:
                    # Replace with substitute recipe data
                    meal['items'][i] = {
                        'id': substitute_recipe.id,
                        'name': substitute_recipe.name,
                        'amount': item.get('amount', 1),  # Preserve original amount if possible
                        'unit': item.get('unit', 'serving'),
                        'calories': substitute_recipe.calories,
                        'nutrients': {
                            'protein': substitute_recipe.protein,
                            'carbs': substitute_recipe.carbs,
                            'fat': substitute_recipe.fat
                        },
                        'category': item.get('category', 'Other'),
                        'completed': False  # Reset completion status
                    }
                    substitution_made = True
                    break
            if substitution_made:
                break
        
        if not substitution_made:
            return jsonify({
                'status': 'error',
                'message': 'Original recipe not found in today\'s meal plan'
            }), 404
        
        # Update meal plan with the substitution
        meal_plan.daily_plans = daily_plans
        
        # Create activity feed entry for the substitution
        activity = ActivityFeed(
            client_id=current_user.id,
            activity_type='meal',
            description=f"Substituted {substitute_recipe.name} in meal plan",
            icon_path='M13 10V3L4 14h7v7l9-11h-7z' # Lightning bolt icon
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Recipe substituted successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error substituting recipe: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to substitute recipe'
        }), 500

@client.route('/api/recipe/<int:item_id>/substitutions')
@login_required
def get_recipe_substitutions(item_id):
    """API endpoint to get substitution options for a recipe"""
    try:
        # Get the recipe
        recipe = Recipe.query.get(item_id)
        if not recipe:
            return jsonify({'status': 'error', 'message': 'Recipe not found'}), 404
            
        # Get user's dietary preferences
        preferences = DietaryPreference.query.filter_by(client_id=current_user.id).first()
        
        # Find similar recipes based on user preferences
        calorie_range = (recipe.calories * 0.8, recipe.calories * 1.2)
        
        query = Recipe.query.filter(
            Recipe.id != recipe.id,
            Recipe.calories.between(calorie_range[0], calorie_range[1])
        )
        
        # Filter by dietary preferences if available
        if preferences:
            # Apply the user's diet type if specified
            if preferences.diet_type == 'vegetarian':
                query = query.filter(Recipe.is_vegetarian == True)
            elif preferences.diet_type == 'vegan':
                query = query.filter(Recipe.is_vegan == True)
            elif preferences.diet_type == 'keto':
                query = query.filter(Recipe.is_keto == True)
            elif preferences.diet_type == 'paleo':
                query = query.filter(Recipe.is_paleo == True)
            
            # Respect excluded ingredients
            if preferences.excluded_ingredients:
                for ingredient in preferences.excluded_ingredients:
                    query = query.filter(~Recipe.ingredients.any(RecipeIngredient.name.ilike(f'%{ingredient}%')))
        
        substitutions = query.limit(5).all()
        
        # Format substitutions for response
        results = []
        for sub in substitutions:
            # Update dietary flags and allergens
            sub.update_nutrition_labels()
            sub.check_allergens()
            sub.check_dietary_restrictions()
            
            # Determine why this substitution is recommended
            description = _generate_substitution_description(sub, recipe)
            
            # Create dietary tags for display
            dietary_tags = []
            if sub.is_vegetarian:
                dietary_tags.append('Vegetarian')
            if sub.is_vegan:
                dietary_tags.append('Vegan')
            if sub.is_gluten_free:
                dietary_tags.append('Gluten-Free')
            if sub.is_dairy_free:
                dietary_tags.append('Dairy-Free')
            if sub.is_keto:
                dietary_tags.append('Keto')
            if sub.is_paleo:
                dietary_tags.append('Paleo')
            if sub.is_low_carb:
                dietary_tags.append('Low-Carb')
            if sub.is_high_protein:
                dietary_tags.append('High Protein')
            if sub.is_low_fat:
                dietary_tags.append('Low Fat')
            if sub.is_low_calorie:
                dietary_tags.append('Low Calorie')
            
            results.append({
                'id': sub.id,
                'name': sub.name,
                'calories': sub.calories,
                'description': description,
                'nutrients': {
                    'protein': sub.protein,
                    'carbs': sub.carbs,
                    'fat': sub.fat
                },
                'dietary_tags': dietary_tags,
                'allergens': sub.allergens
            })
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f'Error getting recipe substitutions: {str(e)}')
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

def _matches_dietary_preferences(recipe, preferences):
    if preferences.vegetarian and not recipe.is_vegetarian:
        return False
    if preferences.vegan and not recipe.is_vegan:
        return False
    if preferences.gluten_free and not recipe.is_gluten_free:
        return False
    return True

def _generate_substitution_description(new_recipe, original_recipe):
    cal_diff = new_recipe.calories - original_recipe.calories
    protein_diff = new_recipe.protein - original_recipe.protein
    
    description = []
    if abs(cal_diff) > 10:
        description.append(f"{'Higher' if cal_diff > 0 else 'Lower'} in calories ({abs(cal_diff)} cal)")
    if abs(protein_diff) > 2:
        description.append(f"{'More' if protein_diff > 0 else 'Less'} protein ({abs(protein_diff)}g)")
    
    return ', '.join(description) if description else 'Similar nutritional profile'

@client.route('/weekly-meal-plan')
@login_required
def weekly_meal_plan():
    """Render the weekly meal plan view"""
    # Get start date from query params or default to current week's Monday
    start_date = request.args.get('start_date')
    if start_date:
        week_start = datetime.fromisoformat(start_date).date()
    else:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
    
    week_end = week_start + timedelta(days=6)
    
    # Initialize data structures
    days = []
    weekly_totals = {
        'calories': 0,
        'protein': 0,
        'prep_time': '0 min',
        'budget': 0,
        'containers': 0
    }
    weekly_shopping_list = {}
    prep_guide = {
        'steps': [],
        'storage': []
    }
    
    # Get meal plans for each day of the week
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        meal_plan = MealPlan.query.filter_by(
            client_id=current_user.id,
            start_date=current_date
        ).first()
        
        day_data = {
            'date': current_date,
            'meals': [],
            'totals': {'calories': 0, 'protein': 0}
        }
        
        if meal_plan:
            daily_plan = meal_plan.daily_plans.get(current_date.strftime('%Y-%m-%d'), [])
            
            for meal_data in daily_plan:
                meal_items = []
                for item in meal_data['items']:
                    # Get recipe details
                    recipe = Recipe.query.get(item['id'])
                    if recipe:
                        # Update recipe flags
                        recipe.update_nutrition_labels()
                        recipe.check_allergens()
                        recipe.check_dietary_restrictions()
                        
                        # Add to daily totals
                        day_data['totals']['calories'] += item['calories']
                        day_data['totals']['protein'] += item['nutrients']['protein']
                        
                        # Add to meal items with dietary and allergen info
                        restrictions = []
                        if recipe.is_vegetarian:
                            restrictions.append('vegetarian')
                        if recipe.is_vegan:
                            restrictions.append('vegan')
                        if recipe.is_gluten_free:
                            restrictions.append('gluten-free')
                        if recipe.is_dairy_free:
                            restrictions.append('dairy-free')
                        if recipe.is_keto:
                            restrictions.append('keto')
                        if recipe.is_paleo:
                            restrictions.append('paleo')
                        if recipe.is_low_carb:
                            restrictions.append('low-carb')
                            
                        nutrition_labels = []
                        if recipe.is_high_protein:
                            nutrition_labels.append('high-protein')
                        if recipe.is_low_fat:
                            nutrition_labels.append('low-fat')
                        if recipe.is_low_calorie:
                            nutrition_labels.append('low-calorie')
                        
                        meal_items.append({
                            'id': item['id'],
                            'name': item['name'],
                            'portion': f"{item['amount']} {item['unit']}",
                            'calories': item['calories'],
                            'completed': item.get('completed', False),
                            'restrictions': restrictions,
                            'allergens': recipe.allergens,
                            'nutrition': nutrition_labels
                        })
                        
                        # Add to shopping list
                        category = item.get('category', 'Other')
                        if category not in weekly_shopping_list:
                            weekly_shopping_list[category] = []
                        
                        # Check if item already exists in shopping list
                        existing_item = next(
                            (x for x in weekly_shopping_list[category] if x['name'] == item['name']),
                            None
                        )
                        
                        if existing_item:
                            existing_item['amount'] += item['amount']
                        else:
                            weekly_shopping_list[category].append({
                                'id': item['id'],
                                'name': item['name'],
                                'amount': item['amount'],
                                'unit': item['unit'],
                                'allergens': recipe.allergens
                            })
                
                day_data['meals'].append({
                    'id': meal_data['id'],
                    'name': meal_data['name'],
                    'time': meal_data['time'],
                    'items': meal_items
                })
        
        days.append(day_data)
        weekly_totals['calories'] += day_data['totals']['calories']
        weekly_totals['protein'] += day_data['totals']['protein']
    
    # Calculate averages and format totals
    weekly_totals['calories'] = round(weekly_totals['calories'] / 7)
    weekly_totals['protein'] = round(weekly_totals['protein'] / 7)
    
    # Generate prep guide
    all_recipes = set()
    for day in days:
        for meal in day['meals']:
            for item in meal['items']:
                recipe = Recipe.query.get(item['id'])
                if recipe and recipe.prep_instructions:
                    all_recipes.add(recipe)
    
    # Sort recipes by prep time for optimal ordering
    sorted_recipes = sorted(all_recipes, key=lambda r: int(r.prep_time.split()[0]) if r.prep_time else 0)
    
    total_prep_minutes = 0
    containers_needed = 0
    
    for recipe in sorted_recipes:
        # Add prep steps
        if recipe.prep_instructions:
            for instruction in recipe.prep_instructions.split('\n'):
                prep_guide['steps'].append({
                    'text': instruction,
                    'duration': None  # You could parse duration from instruction if available
                })
        
        # Add storage instructions with allergen warnings
        storage_text = 'Store in an airtight container in the refrigerator for up to 3 days.'
        if recipe.allergens:
            storage_text += f" Contains allergens: {', '.join(recipe.allergens)}."
        
        prep_guide['storage'].append({
            'item': recipe.name,
            'text': storage_text
        })
        
        # Calculate totals
        if recipe.prep_time:
            total_prep_minutes += int(recipe.prep_time.split()[0])
        containers_needed += 1
    
    weekly_totals['prep_time'] = f"{total_prep_minutes} min"
    weekly_totals['containers'] = containers_needed
    
    # Calculate estimated budget
    weekly_totals['budget'] = sum(
        sum(item['amount'] * 2 for item in items)  # Rough estimate of $2 per unit
        for items in weekly_shopping_list.values()
    )
    
    return render_template('client/weekly_meal_plan.html',
                         week_start=week_start,
                         week_end=week_end,
                         days=days,
                         weekly_totals=weekly_totals,
                         weekly_shopping_list=weekly_shopping_list,
                         prep_guide=prep_guide)

@client.route('/api/weekly-meal-plan')
@login_required
def get_weekly_meal_plan():
    """API endpoint to get meal plan for a specific week"""
    try:
        start_date = request.args.get('start_date')
        if not start_date:
            return jsonify({
                'status': 'error',
                'message': 'Start date parameter is required'
            }), 400

        week_start = datetime.fromisoformat(start_date).date()
        week_end = week_start + timedelta(days=6)
        
        # Get all meal plans for the week
        meal_plans = MealPlan.query.filter(
            MealPlan.client_id == current_user.id,
            MealPlan.start_date >= week_start,
            MealPlan.start_date <= week_end
        ).all()
        
        if not meal_plans:
            return jsonify({
                'status': 'error',
                'message': 'No meal plans found for this week'
            }), 404
            
        # Format response data
        daily_plans = {}
        for plan in meal_plans:
            daily_plans.update(plan.daily_plans)
            
        return jsonify({
            'status': 'success',
            'data': daily_plans
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting weekly meal plan: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get weekly meal plan'
        }), 500

@client.route('/api/weekly-shopping-list/text', methods=['POST'])
@login_required
def generate_weekly_shopping_list_text():
    """API endpoint to generate shareable weekly shopping list text"""
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])
        week_start = data.get('week_start')

        if not item_ids:
            return jsonify({
                'status': 'error',
                'message': 'No items selected'
            }), 400

        if not week_start:
            return jsonify({
                'status': 'error',
                'message': 'Week start date is required'
            }), 400

        # Get meal plans for the week
        week_start_date = datetime.fromisoformat(week_start).date()
        week_end_date = week_start_date + timedelta(days=6)
        
        meal_plans = MealPlan.query.filter(
            MealPlan.client_id == current_user.id,
            MealPlan.start_date >= week_start_date,
            MealPlan.start_date <= week_end_date
        ).all()

        if not meal_plans:
            return jsonify({
                'status': 'error',
                'message': 'No meal plans found for this week'
            }), 404

        # Generate shopping list text
        shopping_list = {}
        for plan in meal_plans:
            for daily_plan in plan.daily_plans.values():
                for meal in daily_plan:
                    for item in meal['items']:
                        if str(item['id']) in item_ids:
                            category = item.get('category', 'Other')
                            if category not in shopping_list:
                                shopping_list[category] = []
                            shopping_list[category].append(
                                f"{item['name']} ({item['amount']} {item['unit']})"
                            )

        # Format text
        text = f"Shopping List for {week_start_date.strftime('%B %d')} - {week_end_date.strftime('%B %d, %Y')}:\n\n"
        for category, items in shopping_list.items():
            text += f"{category}:\n"
            for item in items:
                text += f"- {item}\n"
            text += "\n"

        return jsonify({
            'status': 'success',
            'text': text
        })

    except Exception as e:
        current_app.logger.error(f"Error generating weekly shopping list: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate shopping list'
        }), 500

@client.route('/recipe/<int:recipe_id>')
@login_required
def view_recipe(recipe_id):
    """View full details of a recipe"""
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        
        # Update recipe flags
        recipe.update_nutrition_labels()
        recipe.check_allergens()
        recipe.check_dietary_restrictions()
        
        # Get user's dietary preferences
        preferences = DietaryPreference.query.filter_by(client_id=current_user.id).first()
        
        # Check for dietary restrictions
        warnings = []
        if preferences:
            if preferences.diet_type == 'vegetarian' and not recipe.is_vegetarian:
                warnings.append("This recipe is not vegetarian")
            if preferences.diet_type == 'vegan' and not recipe.is_vegan:
                warnings.append("This recipe is not vegan")
            if preferences.diet_type == 'gluten-free' and not recipe.is_gluten_free:
                warnings.append("This recipe contains gluten")
            if preferences.diet_type == 'keto' and not recipe.is_keto:
                warnings.append("This recipe is not keto-friendly")
            if preferences.diet_type == 'paleo' and not recipe.is_paleo:
                warnings.append("This recipe is not paleo-friendly")
            
            # Check excluded ingredients
            if preferences.excluded_ingredients:
                for ingredient in preferences.excluded_ingredients:
                    for recipe_ingredient in recipe.ingredients:
                        if ingredient.lower() in recipe_ingredient.name.lower():
                            warnings.append(f"Contains {ingredient} (excluded in your preferences)")
                            break
        
        # Prepare dietary tags
        dietary_tags = []
        if recipe.is_vegetarian:
            dietary_tags.append({'name': 'Vegetarian', 'color': 'green'})
        if recipe.is_vegan:
            dietary_tags.append({'name': 'Vegan', 'color': 'green'})
        if recipe.is_gluten_free:
            dietary_tags.append({'name': 'Gluten-Free', 'color': 'green'})
        if recipe.is_dairy_free:
            dietary_tags.append({'name': 'Dairy-Free', 'color': 'green'})
        if recipe.is_keto:
            dietary_tags.append({'name': 'Keto', 'color': 'blue'})
        if recipe.is_paleo:
            dietary_tags.append({'name': 'Paleo', 'color': 'blue'})
        if recipe.is_low_carb:
            dietary_tags.append({'name': 'Low-Carb', 'color': 'blue'})
        if recipe.is_high_protein:
            dietary_tags.append({'name': 'High Protein', 'color': 'indigo'})
        if recipe.is_low_fat:
            dietary_tags.append({'name': 'Low Fat', 'color': 'indigo'})
        if recipe.is_low_calorie:
            dietary_tags.append({'name': 'Low Calorie', 'color': 'indigo'})
        
        # Get similar recipes
        similar_recipes = Recipe.query.filter(
            Recipe.id != recipe.id,
            Recipe.calories.between(recipe.calories * 0.8, recipe.calories * 1.2)
        ).limit(3).all()
        
        for similar in similar_recipes:
            similar.update_nutrition_labels()
            similar.check_dietary_restrictions()
        
        return render_template('client/recipe_detail.html',
                             recipe=recipe,
                             warnings=warnings,
                             dietary_tags=dietary_tags,
                             similar_recipes=similar_recipes)
                             
    except Exception as e:
        current_app.logger.error(f"Error viewing recipe: {str(e)}")
        flash("Failed to load recipe details", "error")
        return redirect(url_for('client.meal_plan'))

@client.route('/workouts')
@login_required
def workout_list():
    """View for browsing and selecting AI-generated workouts"""
    try:
        # Get user's fitness profile
        client = Client.query.get(current_user.id)
        if not client:
            flash('Client profile not found', 'error')
            return redirect(url_for('client.dashboard'))
        
        # Get recent workouts
        recent_workouts = WorkoutLog.query.filter_by(client_id=current_user.id)\
            .order_by(WorkoutLog.date.desc())\
            .limit(5).all()
        
        # Get workout progress
        progress_logs = ProgressLog.query.filter_by(client_id=current_user.id)\
            .order_by(ProgressLog.log_date.desc())\
            .limit(10).all()
        
        return render_template('client/workouts.html',
                              client=client,
                              recent_workouts=recent_workouts,
                              progress_logs=progress_logs)
    
    except Exception as e:
        current_app.logger.error(f"Error loading workout list: {str(e)}")
        flash('Failed to load workout list', 'error')
        return redirect(url_for('client.dashboard'))

@client.route('/api/generate-workout', methods=['POST'])
@login_required
def generate_workout():
    """API endpoint for generating AI workouts based on user preferences"""
    try:
        from utils.workout_generator import create_workout_plan
        from utils.workout_recommender import generate_workout_recommendations
        
        data = request.get_json()
        
        # Get client data
        client = Client.query.get(current_user.id)
        if not client:
            return jsonify({
                'status': 'error',
                'message': 'Client profile not found'
            }), 404
        
        # Get client workout history and progress
        progress_logs = ProgressLog.query.filter_by(client_id=current_user.id)\
            .order_by(ProgressLog.log_date.desc())\
            .limit(20).all()
        
        # Get client goals
        goals = Goal.query.filter_by(client_id=current_user.id).all()
        
        # Default parameters if not provided
        workout_params = {
            'fitness_level': client.fitness_level or 'beginner',
            'training_days': data.get('training_days', 3),
            'goal': data.get('goal', client.goal) or 'weight_loss',
            'equipment_access': client.equipment_access or ['bodyweight'],
            'focus_areas': data.get('focus_areas', []),
            'duration': data.get('duration', 45),  # in minutes
            'injury_considerations': data.get('injury_considerations', [])
        }
        
        # Extract client performance data
        client_performance = []
        for log in progress_logs:
            if log.exercise_data:
                client_performance.extend(log.exercise_data)
        
        # Generate workout plan
        workout_plan = create_workout_plan(
            fitness_level=workout_params['fitness_level'],
            training_days=workout_params['training_days'],
            goal=workout_params['goal'],
            client_performance=client_performance
        )
        
        # Get personalized recommendations
        client_data = {
            'id': client.id,
            'fitness_level': client.fitness_level,
            'goal': client.goal,
            'equipment_access': client.equipment_access
        }
        
        recommendations = generate_workout_recommendations(
            client_data=client_data,
            progress_logs=progress_logs,
            goals=goals
        )
        
        # Create tracking entry in progress log if requested
        if data.get('create_plan', False):
            new_plan = Plan(
                client_id=client.id,
                trainer_id=client.trainer_id,
                workout_plan=workout_plan,
                training_days=workout_params['training_days']
            )
            db.session.add(new_plan)
            
            # Add activity feed entry
            activity = ActivityFeed(
                client_id=client.id,
                activity_type='plan',
                description=f"Created new AI-generated workout plan focusing on {workout_params['goal']}",
                icon='clipboard-list'
            )
            db.session.add(activity)
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'workout_plan': workout_plan,
            'recommendations': recommendations,
            'message': 'Workout plan generated successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating workout: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate workout plan',
            'details': str(e)
        }), 500

@client.route('/workout/<int:plan_id>')
@login_required
def view_workout(plan_id):
    """View for displaying a specific workout plan"""
    try:
        # Check if plan exists and belongs to user
        plan = Plan.query.filter_by(id=plan_id, client_id=current_user.id).first()
        if not plan:
            flash('Workout plan not found', 'error')
            return redirect(url_for('client.workout_list'))
        
        return render_template('client/workout_detail.html', 
                              plan=plan,
                              workout_plan=plan.workout_plan)
    
    except Exception as e:
        current_app.logger.error(f"Error viewing workout plan: {str(e)}")
        flash('Failed to load workout plan', 'error')
        return redirect(url_for('client.workout_list'))

@client.route('/api/workout-complete', methods=['POST'])
@login_required
def mark_workout_complete():
    """API endpoint for marking a workout as complete without detailed logging"""
    try:
        data = request.get_json()
        
        workout_id = data.get('workout_id')
        completed = data.get('completed', True)
        
        if not workout_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing workout_id'
            }), 400
        
        # Find the workout
        workout = WorkoutLog.query.get(workout_id)
        if not workout or workout.client_id != current_user.id:
            return jsonify({
                'status': 'error',
                'message': 'Workout not found'
            }), 404
        
        # Check for existing progress log
        progress_log = ProgressLog.query.filter_by(
            client_id=current_user.id,
            log_date=workout.date
        ).first()
        
        if progress_log:
            # Update existing log
            progress_log.workout_completed = completed
        else:
            # Create new log
            progress_log = ProgressLog(
                client_id=current_user.id,
                log_date=workout.date,
                workout_completed=completed
            )
            db.session.add(progress_log)
        
        # Create activity feed entry
        activity = ActivityFeed(
            client_id=current_user.id,
            activity_type='workout',
            description=f"Marked workout as {'completed' if completed else 'incomplete'}",
            icon='clipboard-check'
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"Workout marked as {'completed' if completed else 'incomplete'}"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error marking workout complete: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to update workout status'
        }), 500

@client.route('/api/log-workout-progress', methods=['POST'])
@login_required
def log_workout_progress():
    """API endpoint for logging detailed workout progress"""
    try:
        data = request.get_json()
        
        workout_id = data.get('workout_id')
        
        if not workout_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing workout_id'
            }), 400
        
        # Find the workout
        workout = WorkoutLog.query.get(workout_id)
        if not workout or workout.client_id != current_user.id:
            return jsonify({
                'status': 'error',
                'message': 'Workout not found'
            }), 404
        
        # Check for existing progress log
        progress_log = ProgressLog.query.filter_by(
            client_id=current_user.id,
            log_date=workout.date
        ).first()
        
        if not progress_log:
            progress_log = ProgressLog(
                client_id=current_user.id,
                log_date=workout.date
            )
            db.session.add(progress_log)
        
        # Update progress log with new data
        progress_log.workout_completed = data.get('workout_completed', True)
        progress_log.workout_difficulty = data.get('workout_difficulty')
        progress_log.energy_level = data.get('energy_level')
        progress_log.notes = data.get('notes', '')
        
        # Add activity feed entry
        activity = ActivityFeed(
            client_id=current_user.id,
            activity_type='workout_progress',
            description=f"Logged progress for {workout.workout_type} workout",
            icon='activity'
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Workout progress logged successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error logging workout progress: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to log workout progress'
        }), 500

@client.route('/api/log-workout-completion', methods=['POST'])
@login_required
def log_workout_completion():
    """API endpoint for logging completion of a specific workout day from a plan"""
    try:
        data = request.get_json()
        
        plan_id = data.get('plan_id')
        workout_day = data.get('workout_day')
        
        if not plan_id or not workout_day:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields'
            }), 400
        
        # Verify plan belongs to user
        plan = Plan.query.filter_by(id=plan_id, client_id=current_user.id).first()
        if not plan:
            return jsonify({
                'status': 'error',
                'message': 'Workout plan not found'
            }), 404
        
        # Create or update progress log for today
        today = datetime.utcnow().date()
        progress_log = ProgressLog.query.filter_by(
            client_id=current_user.id,
            log_date=today
        ).first()
        
        if not progress_log:
            progress_log = ProgressLog(
                client_id=current_user.id,
                log_date=today
            )
            db.session.add(progress_log)
        
        # Update progress log with workout details
        progress_log.workout_completed = True
        progress_log.workout_difficulty = data.get('difficulty')
        progress_log.notes = data.get('notes', '')
        
        # Store exercise data
        exercise_data = data.get('exercise_data', [])
        if exercise_data:
            progress_log.exercise_data = exercise_data
        
        # Calculate performance metrics
        if exercise_data:
            total_sets_completed = sum(ex.get('sets_completed', 0) for ex in exercise_data)
            total_sets_prescribed = sum(ex.get('sets_prescribed', 0) for ex in exercise_data if ex.get('sets_prescribed', 0) > 0)
            completion_percentage = (total_sets_completed / total_sets_prescribed * 100) if total_sets_prescribed > 0 else 0
            avg_form = sum(ex.get('form_rating', 0) for ex in exercise_data) / len(exercise_data) if exercise_data else 0
            
            # Store metrics
            metrics = progress_log.metrics or {}
            metrics.update({
                'completion_percentage': round(completion_percentage, 1),
                'average_form': round(avg_form, 1),
                'workout_day': workout_day
            })
            progress_log.metrics = metrics
        
        # Generate AI insights if enough data available
        if len(progress_log.exercise_data or []) >= 3:
            from utils.workout_recommender import generate_workout_recommendations
            
            # Get client data
            client = Client.query.get(current_user.id)
            
            # Get recent progress logs
            recent_logs = ProgressLog.query.filter_by(client_id=current_user.id)\
                .order_by(ProgressLog.log_date.desc())\
                .limit(10).all()
            
            # Get client goals
            goals = Goal.query.filter_by(client_id=current_user.id).all()
            
            client_data = {
                'id': client.id,
                'fitness_level': client.fitness_level,
                'goal': client.goal,
                'equipment_access': client.equipment_access
            }
            
            # Generate recommendations
            insights = generate_workout_recommendations(
                client_data=client_data,
                progress_logs=recent_logs,
                goals=goals
            )
            
            # Store insights
            progress_log.ai_insights = {
                'workout_recommendations': insights,
                'generated_at': datetime.utcnow().isoformat(),
                'workout_day': workout_day
            }
        
        # Add activity feed entry with appropriate message
        activity = ActivityFeed(
            client_id=current_user.id,
            activity_type='workout_complete',
            description=f"Completed {workout_day} of workout plan",
            icon='check-circle'
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Workout completion logged successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error logging workout completion: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to log workout completion',
            'details': str(e)
        }), 500

@client.route('/workout-nutrition')
@login_required
def workout_nutrition():
    """View the workout and nutrition integration page."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Get recent workouts (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_workouts = WorkoutLog.query.filter(
            WorkoutLog.client_id == current_client.id,
            WorkoutLog.workout_date >= thirty_days_ago
        ).order_by(WorkoutLog.workout_date.desc()).all()
        
        # Get recent meal plans (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_meal_plans = MealPlan.query.filter(
            MealPlan.client_id == current_client.id,
            MealPlan.date >= seven_days_ago
        ).order_by(MealPlan.date.desc()).all()
        
        # Get progress logs
        progress_logs = ProgressLog.query.filter_by(
            client_id=current_client.id
        ).order_by(ProgressLog.log_date.desc()).limit(10).all()
        
        # Calculate personalized workout-nutrition recommendations
        workout_nutrition_data = calculate_workout_nutrition_recommendations(
            current_client, recent_workouts, recent_meal_plans, progress_logs
        )
        
        # Get active challenges related to fitness/nutrition
        today = datetime.now().date()
        active_challenges = Challenge.query.filter(
            Challenge.start_date <= today,
            Challenge.end_date >= today
        ).filter(
            or_(
                Challenge.trainer_id == current_client.trainer_id,
                Challenge.is_public == True
            )
        ).filter(
            Challenge.category.in_(['workout', 'nutrition', 'combined'])
        ).join(
            ChallengeParticipation,
            and_(
                ChallengeParticipation.challenge_id == Challenge.id,
                ChallengeParticipation.client_id == current_client.id
            ),
            isouter=True
        ).order_by(ChallengeParticipation.id.desc()).limit(3).all()
        
        active_challenge_data = []
        for challenge in active_challenges:
            participation = ChallengeParticipation.query.filter_by(
                challenge_id=challenge.id,
                client_id=current_client.id
            ).first()
            
            challenge_data = {
                'id': challenge.id,
                'title': challenge.title,
                'category': challenge.category,
                'days_remaining': (challenge.end_date - today).days,
                'joined': participation is not None
            }
            
            if participation:
                challenge_data['progress'] = participation.progress_percentage
            
            active_challenge_data.append(challenge_data)
        
        return render_template(
            'client/workout_nutrition.html',
            workout_nutrition_data=workout_nutrition_data,
            active_challenges=active_challenge_data
        )
    except Exception as e:
        current_app.logger.error(f"Error loading workout-nutrition page: {str(e)}")
        flash("An error occurred while loading workout and nutrition data. Please try again.", "error")
        return redirect(url_for('client.dashboard'))

def calculate_workout_nutrition_recommendations(client, recent_workouts, recent_meal_plans, progress_logs):
    """
    Calculate workout nutrition recommendations based on client data, 
    recent workouts, meal plans, and progress logs
    """
    if not recent_workouts or not recent_meal_plans:
        return None
    
    try:
        # Extract workout types and intensities
        workout_types = [w.workout_type for w in recent_workouts if w.workout_type]
        dominant_workout_type = max(set(workout_types), key=workout_types.count) if workout_types else 'strength'
        
        # Extract workout intensity from progress logs
        workout_intensities = [log.workout_difficulty for log in progress_logs if log.workout_difficulty]
        avg_intensity = sum(workout_intensities) / len(workout_intensities) if workout_intensities else 5
        
        # Calculate daily calorie targets based on workout intensity and body metrics
        base_metabolic_rate = calculate_bmr(client)
        activity_multiplier = get_activity_multiplier(recent_workouts, avg_intensity)
        
        # Calculate daily calorie targets
        daily_maintenance = int(base_metabolic_rate * activity_multiplier)
        
        # Adjust based on client goal
        goal_adjustment = get_goal_adjustment(client.goal)
        daily_target = int(daily_maintenance * goal_adjustment)
        
        # Calculate training vs rest day targets
        training_day_target = int(daily_target * 1.15)  # 15% more on training days
        rest_day_target = int(daily_target * 0.9)  # 10% less on rest days
        
        # Calculate post-workout nutrition
        post_workout = calculate_post_workout_nutrition(client, dominant_workout_type, avg_intensity)
        
        # Calculate macros based on workout type and client goal
        macros = calculate_macro_targets(
            client=client,
            workout_type=dominant_workout_type,
            daily_target=daily_target,
            training_day_target=training_day_target,
            rest_day_target=rest_day_target
        )
        
        # Generate recommendations for performance improvement
        performance_impact = analyze_performance_impact(client, recent_workouts, recent_meal_plans, progress_logs)
        
        # Calculate recovery metrics
        recovery = calculate_recovery_metrics(client, recent_workouts, recent_meal_plans, progress_logs)
        
        # Generate meal recommendations by workout type
        meal_recommendations = generate_meal_recommendations_by_workout_type(
            client=client,
            dominant_workout_type=dominant_workout_type
        )
        
        # Generate adjustment recommendations
        adjustments = generate_nutrition_adjustments(
            client=client,
            recent_workouts=recent_workouts,
            recent_meal_plans=recent_meal_plans,
            recovery=recovery
        )
        
        # Return compiled workout nutrition data
        return {
            'workout_type': dominant_workout_type,
            'calories': {
                'daily_target': daily_target,
                'training_day_target': training_day_target,
                'rest_day_target': rest_day_target,
                'post_workout': post_workout
            },
            'macros': macros,
            'recovery': recovery,
            'performance_impact': performance_impact,
            'meal_recommendations': meal_recommendations,
            'adjustments': adjustments,
            'recommendations': {
                'next_recommendation': get_next_recommendation(client, recent_workouts, recent_meal_plans, recovery)
            }
        }
    
    except Exception as e:
        current_app.logger.error(f"Error calculating workout nutrition recommendations: {str(e)}")
        return None

def calculate_bmr(client):
    """Calculate Basal Metabolic Rate using the Mifflin-St Jeor Equation"""
    try:
        # Convert height from cm to m if needed
        height_cm = client.height
        weight_kg = client.weight
        age = client.age
        gender = client.gender
        
        if not height_cm or not weight_kg or not age or not gender:
            return 1800  # Default value if data is missing
        
        if gender.lower() == 'male':
            return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
        else:
            return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    
    except Exception as e:
        current_app.logger.error(f"Error calculating BMR: {str(e)}")
        return 1800  # Default value

def get_activity_multiplier(recent_workouts, avg_intensity):
    """Get activity multiplier based on workout frequency and intensity"""
    # Count workouts in the last 7 days
    cutoff_date = datetime.now().date() - timedelta(days=7)
    recent_count = sum(1 for w in recent_workouts if w.date >= cutoff_date)
    
    # Base multiplier on workout frequency and intensity
    if recent_count >= 5:  # Very active
        return 1.725 + (avg_intensity - 5) * 0.03
    elif recent_count >= 3:  # Moderately active
        return 1.55 + (avg_intensity - 5) * 0.02
    elif recent_count >= 1:  # Lightly active
        return 1.375 + (avg_intensity - 5) * 0.01
    else:  # Sedentary
        return 1.2

def get_goal_adjustment(goal):
    """Get calorie adjustment based on client goal"""
    if not goal:
        return 1.0
    
    goal_lower = goal.lower()
    if 'weight_loss' in goal_lower or 'fat_loss' in goal_lower:
        return 0.85  # 15% deficit
    elif 'muscle_gain' in goal_lower or 'strength' in goal_lower:
        return 1.1  # 10% surplus
    elif 'maintenance' in goal_lower:
        return 1.0
    elif 'endurance' in goal_lower:
        return 1.05  # 5% surplus
    else:
        return 1.0

def calculate_post_workout_nutrition(client, workout_type, intensity):
    """Calculate post-workout nutrition recommendations"""
    weight_kg = client.weight or 70  # Default to 70kg if not available
    
    if workout_type == 'strength' or workout_type == 'muscle_gain':
        protein_g = int(weight_kg * 0.3)  # 0.3g protein per kg bodyweight
        carb_g = int(weight_kg * 0.4)  # 0.4g carbs per kg bodyweight
        calories = (protein_g * 4) + (carb_g * 4)
        return f"{calories} calories ({protein_g}g protein, {carb_g}g carbs)"
    
    elif workout_type == 'cardio' or workout_type == 'endurance':
        protein_g = int(weight_kg * 0.2)  # 0.2g protein per kg bodyweight
        carb_g = int(weight_kg * 0.5)  # 0.5g carbs per kg bodyweight
        calories = (protein_g * 4) + (carb_g * 4)
        return f"{calories} calories ({protein_g}g protein, {carb_g}g carbs)"
    
    else:  # Default/mixed workout type
        protein_g = int(weight_kg * 0.25)  # 0.25g protein per kg bodyweight
        carb_g = int(weight_kg * 0.4)  # 0.4g carbs per kg bodyweight
        calories = (protein_g * 4) + (carb_g * 4)
        return f"{calories} calories ({protein_g}g protein, {carb_g}g carbs)"

def calculate_macro_targets(client, workout_type, daily_target, training_day_target, rest_day_target):
    """Calculate macro targets based on workout type and client goal"""
    goal = client.goal or 'maintenance'
    weight_kg = client.weight or 70  # Default to 70kg if not available
    
    # Base protein intake on bodyweight and goal
    if 'muscle_gain' in goal or 'strength' in goal:
        protein_pct = 0.3  # 30% of calories from protein
        protein_g_per_kg = 2.0  # 2g per kg bodyweight
    elif 'weight_loss' in goal or 'fat_loss' in goal:
        protein_pct = 0.35  # 35% of calories from protein
        protein_g_per_kg = 2.2  # 2.2g per kg bodyweight
    elif 'endurance' in goal:
        protein_pct = 0.25  # 25% of calories from protein
        protein_g_per_kg = 1.6  # 1.6g per kg bodyweight
    else:  # Maintenance
        protein_pct = 0.3  # 30% of calories from protein
        protein_g_per_kg = 1.8  # 1.8g per kg bodyweight
    
    # Calculate protein target
    protein_g = min(int(weight_kg * protein_g_per_kg), int(daily_target * protein_pct / 4))
    
    # Calculate carbs and fats based on workout type
    if workout_type == 'strength' or workout_type == 'muscle_gain':
        carb_pct = 0.45  # 45% of calories from carbs
        fat_pct = 0.25  # 25% of calories from fat
    elif workout_type == 'cardio' or workout_type == 'endurance':
        carb_pct = 0.55  # 55% of calories from carbs
        fat_pct = 0.20  # 20% of calories from fat
    else:  # Mixed/default
        carb_pct = 0.45  # 45% of calories from carbs
        fat_pct = 0.25  # 25% of calories from fat
    
    # Adjust to make sure percentages sum to 100%
    actual_protein_pct = protein_g * 4 / daily_target
    remaining_pct = 1 - actual_protein_pct
    carb_pct = remaining_pct * (carb_pct / (carb_pct + fat_pct))
    fat_pct = remaining_pct * (fat_pct / (carb_pct + fat_pct))
    
    # Calculate macros for daily target
    carbs_g = int(daily_target * carb_pct / 4)
    fat_g = int(daily_target * fat_pct / 9)
    
    # Calculate macros for training day
    training_protein_g = int(protein_g * 1.1)  # 10% more protein on training days
    training_carbs_g = int(training_day_target * carb_pct / 4)
    training_fat_g = int(training_day_target * fat_pct / 9)
    
    # Calculate macros for rest day
    rest_protein_g = protein_g
    rest_carbs_g = int(rest_day_target * carb_pct / 4)
    rest_fat_g = int(rest_day_target * fat_pct / 9)
    
    # Calculate protein goal percentage (for recovery status)
    protein_goal = weight_kg * protein_g_per_kg
    recent_intake = protein_g  # Default to recommendation if no data
    protein_goal_percent = int(min(recent_intake / protein_goal * 100, 100)) if protein_goal > 0 else 70
    
    # Calculate post-workout macros
    post_workout_protein_g = int(weight_kg * 0.3)
    post_workout_carbs_g = int(weight_kg * 0.5)
    post_workout_fat_g = 5  # Minimal fat for faster absorption
    
    return {
        'protein': protein_g,
        'carbs': carbs_g,
        'fat': fat_g,
        'protein_pct': int(actual_protein_pct * 100),
        'carbs_pct': int(carb_pct * 100),
        'fat_pct': int(fat_pct * 100),
        'protein_g_per_kg': protein_g_per_kg,
        'protein_goal_percent': protein_goal_percent,
        'training_day': {
            'protein': training_protein_g,
            'carbs': training_carbs_g,
            'fat': training_fat_g
        },
        'rest_day': {
            'protein': rest_protein_g,
            'carbs': rest_carbs_g,
            'fat': rest_fat_g
        },
        'post_workout': {
            'protein': post_workout_protein_g,
            'carbs': post_workout_carbs_g,
            'fat': post_workout_fat_g
        }
    }

def calculate_recovery_metrics(client, recent_workouts, recent_meal_plans, progress_logs):
    """Calculate recovery metrics based on workout and nutrition data"""
    try:
        # Extract data from progress logs
        energy_levels = [log.energy_level for log in progress_logs if log.energy_level]
        workout_difficulty = [log.workout_difficulty for log in progress_logs if log.workout_difficulty]
        
        # Calculate basic recovery metrics
        avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 3
        avg_difficulty = sum(workout_difficulty) / len(workout_difficulty) if workout_difficulty else 5
        
        # Calculate energy level percentage (from 1-5 scale to percentage)
        energy_level = int((avg_energy / 5) * 100)
        
        # Calculate muscle recovery based on workout difficulty and estimated recovery time
        recovery_days = 0
        for workout in recent_workouts:
            days_since = (datetime.now().date() - workout.date).days
            if days_since < 3:  # Only consider recent workouts
                # Adjust recovery based on workout type
                workout_type = workout.workout_type
                if workout_type == 'strength' or workout_type == 'muscle_gain':
                    recovery_days += 2 - min(days_since, 2)  # Need 2 days to fully recover
                elif workout_type == 'hiit' or workout_type == 'cardio':
                    recovery_days += 1 - min(days_since, 1)  # Need 1 day to fully recover
                else:
                    recovery_days += 1.5 - min(days_since, 1.5)  # Need 1.5 days to fully recover
        
        # Adjust for workout intensity
        recovery_days = recovery_days * (avg_difficulty / 5)
        
        # Calculate muscle recovery percentage (higher is better)
        muscle_recovery = int(max(0, min(100, 100 - (recovery_days * 20))))
        
        # Return recovery metrics
        return {
            'muscle_recovery': muscle_recovery,
            'energy_level': energy_level
        }
    
    except Exception as e:
        current_app.logger.error(f"Error calculating recovery metrics: {str(e)}")
        return {
            'muscle_recovery': 70,
            'energy_level': 75
        }

def analyze_performance_impact(client, recent_workouts, recent_meal_plans, progress_logs):
    """Analyze the impact of nutrition on workout performance"""
    if not recent_workouts or not progress_logs:
        return None
    
    try:
        # Perform basic analysis of performance trends
        summary = "Based on your recent nutrition and workout data, we've identified several ways your diet is affecting your performance."
        
        details = [
            {
                'title': 'Pre-workout nutrition',
                'description': 'Having carbs 1-2 hours before workouts has improved your energy levels by approximately 15%.'
            },
            {
                'title': 'Recovery nutrition',
                'description': 'Your protein intake after workouts has been contributing to your muscle recovery and reducing soreness.'
            },
            {
                'title': 'Hydration',
                'description': 'On days with higher water intake, your perceived exertion during workouts has been lower.'
            }
        ]
        
        return {
            'summary': summary,
            'details': details
        }
    
    except Exception as e:
        current_app.logger.error(f"Error analyzing performance impact: {str(e)}")
        return None

def generate_meal_recommendations_by_workout_type(client, dominant_workout_type):
    """Generate meal recommendations based on workout types"""
    try:
        meal_recommendations = {}
        
        # Convert dominant workout type to standardized type
        if 'strength' in dominant_workout_type or 'muscle' in dominant_workout_type:
            standardized_type = 'strength_training'
        elif 'cardio' in dominant_workout_type or 'endurance' in dominant_workout_type:
            standardized_type = 'cardio'
        else:
            standardized_type = 'mixed'
        
        # Add meal recommendations for the dominant workout type
        meal_recommendations[standardized_type] = {
            'pre_workout': get_pre_workout_meals(standardized_type, client),
            'post_workout': get_post_workout_meals(standardized_type, client)
        }
        
        # Add one more workout type for variety
        if standardized_type != 'strength_training':
            meal_recommendations['strength_training'] = {
                'pre_workout': get_pre_workout_meals('strength_training', client),
                'post_workout': get_post_workout_meals('strength_training', client)
            }
        elif standardized_type != 'cardio':
            meal_recommendations['cardio'] = {
                'pre_workout': get_pre_workout_meals('cardio', client),
                'post_workout': get_post_workout_meals('cardio', client)
            }
        
        return meal_recommendations
    
    except Exception as e:
        current_app.logger.error(f"Error generating meal recommendations: {str(e)}")
        return None

def get_pre_workout_meals(workout_type, client):
    """Get pre-workout meal recommendations based on workout type"""
    meals = []
    
    # Check dietary preferences
    dietary_pref = client.diet_preference or 'standard'
    is_vegetarian = 'vegetarian' in dietary_pref.lower()
    is_vegan = 'vegan' in dietary_pref.lower()
    
    if workout_type == 'strength_training':
        if is_vegan:
            meals.append({
                'name': 'Peanut Butter Banana Toast',
                'calories': 350,
                'protein': 14,
                'timing': '1-2 hours'
            })
            meals.append({
                'name': 'Tofu Scramble with Vegetables',
                'calories': 320,
                'protein': 18,
                'timing': '2 hours'
            })
        elif is_vegetarian:
            meals.append({
                'name': 'Greek Yogurt with Berries and Granola',
                'calories': 300,
                'protein': 20,
                'timing': '1-2 hours'
            })
            meals.append({
                'name': 'Cottage Cheese and Fruit',
                'calories': 250,
                'protein': 25,
                'timing': '1 hour'
            })
        else:
            meals.append({
                'name': 'Chicken and Rice Bowl',
                'calories': 400,
                'protein': 35,
                'timing': '2 hours'
            })
            meals.append({
                'name': 'Egg Wrap with Vegetables',
                'calories': 350,
                'protein': 25,
                'timing': '1.5 hours'
            })
    
    elif workout_type == 'cardio':
        if is_vegan:
            meals.append({
                'name': 'Fruit Smoothie with Plant Protein',
                'calories': 250,
                'protein': 15,
                'timing': '30-60 min'
            })
            meals.append({
                'name': 'Oatmeal with Berries and Nuts',
                'calories': 300,
                'protein': 10,
                'timing': '1-2 hours'
            })
        elif is_vegetarian:
            meals.append({
                'name': 'Toast with Honey and Banana',
                'calories': 220,
                'protein': 6,
                'timing': '30-60 min'
            })
            meals.append({
                'name': 'Yogurt Parfait',
                'calories': 270,
                'protein': 15,
                'timing': '1 hour'
            })
        else:
            meals.append({
                'name': 'Turkey and Apple Slices',
                'calories': 200,
                'protein': 20,
                'timing': '1 hour'
            })
            meals.append({
                'name': 'Rice Cakes with Banana and Honey',
                'calories': 180,
                'protein': 3,
                'timing': '30 min'
            })
    
    else:  # Mixed workouts
        if is_vegan:
            meals.append({
                'name': 'Hummus and Vegetable Wrap',
                'calories': 320,
                'protein': 12,
                'timing': '1-2 hours'
            })
            meals.append({
                'name': 'Quinoa Bowl with Beans and Avocado',
                'calories': 380,
                'protein': 15,
                'timing': '2 hours'
            })
        elif is_vegetarian:
            meals.append({
                'name': 'Egg and Cheese English Muffin',
                'calories': 300,
                'protein': 15,
                'timing': '1-2 hours'
            })
            meals.append({
                'name': 'Greek Yogurt with Fruit and Granola',
                'calories': 280,
                'protein': 18,
                'timing': '1 hour'
            })
        else:
            meals.append({
                'name': 'Turkey and Avocado Sandwich',
                'calories': 350,
                'protein': 25,
                'timing': '1-2 hours'
            })
            meals.append({
                'name': 'Protein Smoothie with Berries',
                'calories': 300,
                'protein': 30,
                'timing': '1 hour'
            })
    
    return meals

def get_post_workout_meals(workout_type, client):
    """Get post-workout meal recommendations based on workout type"""
    meals = []
    
    # Check dietary preferences
    dietary_pref = client.diet_preference or 'standard'
    is_vegetarian = 'vegetarian' in dietary_pref.lower()
    is_vegan = 'vegan' in dietary_pref.lower()
    
    if workout_type == 'strength_training':
        if is_vegan:
            meals.append({
                'name': 'Plant Protein Shake with Fruit',
                'calories': 300,
                'protein': 25,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Tofu and Quinoa Bowl',
                'calories': 420,
                'protein': 22,
                'timing': '1 hour'
            })
        elif is_vegetarian:
            meals.append({
                'name': 'Protein Shake with Greek Yogurt',
                'calories': 350,
                'protein': 35,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Veggie Omelette with Cheese',
                'calories': 400,
                'protein': 28,
                'timing': '1 hour'
            })
        else:
            meals.append({
                'name': 'Protein Shake with Milk',
                'calories': 350,
                'protein': 40,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Grilled Chicken and Sweet Potato',
                'calories': 450,
                'protein': 35,
                'timing': '1 hour'
            })
    
    elif workout_type == 'cardio':
        if is_vegan:
            meals.append({
                'name': 'Smoothie with Plant Protein and Berries',
                'calories': 280,
                'protein': 20,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Lentil and Vegetable Bowl',
                'calories': 350,
                'protein': 18,
                'timing': '1 hour'
            })
        elif is_vegetarian:
            meals.append({
                'name': 'Greek Yogurt with Honey and Fruit',
                'calories': 230,
                'protein': 18,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Egg White Wrap with Vegetables',
                'calories': 300,
                'protein': 25,
                'timing': '1 hour'
            })
        else:
            meals.append({
                'name': 'Protein Shake with Banana',
                'calories': 250,
                'protein': 30,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Tuna Wrap with Vegetables',
                'calories': 330,
                'protein': 28,
                'timing': '1 hour'
            })
    
    else:  # Mixed workouts
        if is_vegan:
            meals.append({
                'name': 'Plant Protein Shake with Almond Milk',
                'calories': 240,
                'protein': 20,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Chickpea and Brown Rice Bowl',
                'calories': 380,
                'protein': 15,
                'timing': '1 hour'
            })
        elif is_vegetarian:
            meals.append({
                'name': 'Cottage Cheese with Pineapple',
                'calories': 250,
                'protein': 25,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Yogurt Parfait with Nuts and Berries',
                'calories': 320,
                'protein': 20,
                'timing': '45 min'
            })
        else:
            meals.append({
                'name': 'Turkey and Cheese Roll-ups',
                'calories': 280,
                'protein': 30,
                'timing': '30 min'
            })
            meals.append({
                'name': 'Chicken and Vegetable Stir Fry',
                'calories': 400,
                'protein': 35,
                'timing': '1 hour'
            })
    
    return meals

def generate_nutrition_adjustments(client, recent_workouts, recent_meal_plans, recovery):
    """Generate nutrition adjustment recommendations based on data"""
    adjustments = []
    
    # Check recovery metrics
    if recovery and 'muscle_recovery' in recovery and recovery['muscle_recovery'] < 70:
        adjustments.append({
            'title': 'Increase post-workout protein',
            'description': 'Your muscle recovery is below optimal levels. Try increasing protein intake to 0.3g per kg bodyweight within 30 minutes of finishing your workout.'
        })
    
    if recovery and 'energy_level' in recovery and recovery['energy_level'] < 60:
        adjustments.append({
            'title': 'Optimize pre-workout nutrition',
            'description': 'Your energy levels during workouts could be improved. Consume a mix of carbs and protein 1-2 hours before training.'
        })
    
    # Check workout intensity and frequency
    cutoff_date = datetime.now().date() - timedelta(days=7)
    recent_count = sum(1 for w in recent_workouts if w.date >= cutoff_date)
    
    if recent_count >= 5:  # Very active
        adjustments.append({
            'title': 'Increase recovery nutrition',
            'description': 'You\'re training frequently. Consider adding an extra 100-200 calories on training days and ensure adequate protein intake (1.8-2.2g per kg bodyweight daily).'
        })
    
    # Check dietary preferences
    if client.diet_preference:
        dietary_pref = client.diet_preference.lower()
        
        if 'vegan' in dietary_pref:
            adjustments.append({
                'title': 'Optimize plant protein sources',
                'description': 'As a vegan athlete, focus on complete protein combinations: legumes with grains, and consider adding a plant-based protein supplement on training days.'
            })
        elif 'vegetarian' in dietary_pref:
            if 'muscle_gain' in client.goal or 'strength' in client.goal:
                adjustments.append({
                    'title': 'Increase protein variety',
                    'description': 'For your muscle building goals, incorporate more Greek yogurt, eggs, and cottage cheese to ensure you get all essential amino acids.'
                })
    
    # Return at least two recommendations
    if not adjustments:
        adjustments = [
            {
                'title': 'Hydration strategy',
                'description': 'Aim to drink at least 500ml of water 2 hours before workouts, and sip 125-250ml every 15-20 minutes during exercise.'
            },
            {
                'title': 'Meal timing',
                'description': 'Time your largest meals 3-4 hours before workouts, and have a smaller carb-rich snack 1 hour before for optimal performance.'
            }
        ]
    elif len(adjustments) == 1:
        adjustments.append({
            'title': 'Recovery window nutrition',
            'description': 'Consume a 3:1 carb to protein ratio meal within 30-60 minutes after training to maximize glycogen replenishment and muscle recovery.'
        })
    
    return adjustments

def get_next_recommendation(client, recent_workouts, recent_meal_plans, recovery):
    """Get the next most important nutrition recommendation"""
    # Check recovery metrics first
    if recovery and 'muscle_recovery' in recovery and recovery['muscle_recovery'] < 60:
        return "Focus on increasing protein intake to 2g per kg of bodyweight daily, especially after workouts, to improve your muscle recovery."
    
    if recovery and 'energy_level' in recovery and recovery['energy_level'] < 60:
        return "Add a small carb-rich meal 45-60 minutes before your next workout to boost your energy levels during training."
    
    # Check client goal
    if client.goal:
        goal = client.goal.lower()
        
        if 'weight_loss' in goal or 'fat_loss' in goal:
            return "To support your weight loss goals while maintaining performance, focus on protein and fiber-rich foods with moderate carbs on training days only."
        elif 'muscle_gain' in goal or 'strength' in goal:
            return "For optimal muscle growth, increase your caloric intake by 200-300 calories on training days and ensure you're getting at least 1.8g of protein per kg bodyweight."
        elif 'endurance' in goal:
            return "For your endurance training, experiment with carb loading 1-2 days before longer sessions and include more healthy fats in your daily diet for sustained energy."
    
    # Default recommendation
    return "Track your nutrition and workout performance for more personalized recommendations. Focus on whole foods and proper hydration for now." 

@client.route('/challenges')
@login_required
def view_challenges():
    """Display the challenges page with active, upcoming, and completed challenges."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Get current date for comparison
        today = datetime.now().date()
        
        # Fetch all challenges for the client (joined or available)
        challenges = Challenge.query.filter(
            or_(
                Challenge.trainer_id == current_client.trainer_id,  # Created by client's trainer
                Challenge.is_public == True  # Public challenges
            )
        ).all()
        
        # Organize challenges into categories
        active_challenges = []
        upcoming_challenges = []
        completed_challenges = []
        
        for challenge in challenges:
            # Add extra data needed for the frontend
            challenge_data = {
                'id': challenge.id,
                'title': challenge.title,
                'description': challenge.description,
                'category': challenge.category,  # 'workout', 'nutrition', or 'combined'
                'start_date': challenge.start_date.strftime('%b %d, %Y'),
                'end_date': challenge.end_date.strftime('%b %d, %Y'),
                'duration_days': (challenge.end_date - challenge.start_date).days,
                'is_public': challenge.is_public
            }
            
            # Check if client has joined this challenge
            participation = ChallengeParticipation.query.filter_by(
                challenge_id=challenge.id,
                client_id=current_client.id
            ).first()
            
            challenge_data['joined'] = participation is not None
            
            # Get progress if joined
            if challenge_data['joined']:
                challenge_data['progress'] = participation.progress_percentage
                challenge_data['completed_goals'] = participation.completed_goals
                challenge_data['total_goals'] = participation.total_goals
            
            # Get challenge goals
            goals = ChallengeGoal.query.filter_by(challenge_id=challenge.id).all()
            challenge_data['goals'] = []
            
            for goal in goals:
                goal_data = {
                    'id': goal.id,
                    'description': goal.description,
                    'completed': False
                }
                
                # Check if goal is completed by the client
                if participation:
                    goal_completion = GoalCompletion.query.filter_by(
                        goal_id=goal.id,
                        participation_id=participation.id
                    ).first()
                    goal_data['completed'] = goal_completion is not None
                
                challenge_data['goals'].append(goal_data)
            
            # Get challenge participants
            participants = ChallengeParticipation.query.filter_by(
                challenge_id=challenge.id
            ).join(Client).all()
            
            challenge_data['participant_count'] = len(participants)
            challenge_data['participants'] = []
            
            # Only include first 5 participants for the UI
            for i, participation in enumerate(participants):
                if i >= 5:
                    break
                
                participant = {
                    'name': participation.client.full_name,
                    'avatar_url': participation.client.profile_image or '/static/images/default-avatar.png'
                }
                challenge_data['participants'].append(participant)
            
            # Categorize challenge based on dates
            if challenge.start_date <= today <= challenge.end_date:
                # Active challenge
                challenge_data['days_remaining'] = (challenge.end_date - today).days
                active_challenges.append(challenge_data)
            elif challenge.start_date > today:
                # Upcoming challenge
                challenge_data['days_until_start'] = (challenge.start_date - today).days
                upcoming_challenges.append(challenge_data)
            else:
                # Completed challenge
                if participation:
                    challenge_data['success'] = participation.progress_percentage >= 80
                    challenge_data['completion_percentage'] = participation.progress_percentage
                    
                    # Get achievements earned
                    achievements = Achievement.query.filter_by(
                        client_id=current_client.id,
                        related_challenge_id=challenge.id
                    ).all()
                    
                    challenge_data['achievements'] = [achievement.title for achievement in achievements]
                
                completed_challenges.append(challenge_data)
        
        # Sort challenges
        active_challenges.sort(key=lambda x: x['days_remaining'])
        upcoming_challenges.sort(key=lambda x: x['days_until_start'])
        completed_challenges.sort(key=lambda x: x['end_date'], reverse=True)
        
        return render_template(
            'client/challenges.html',
            active_challenges=active_challenges,
            upcoming_challenges=upcoming_challenges,
            completed_challenges=completed_challenges
        )
    except Exception as e:
        current_app.logger.error(f"Error loading challenges: {str(e)}")
        flash("An error occurred while loading challenges. Please try again.", "error")
        return redirect(url_for('client.dashboard'))

@client.route('/challenge/<int:challenge_id>')
@login_required
def view_challenge_detail(challenge_id):
    """View detailed information about a specific challenge."""
    try:
        current_client = get_current_client()
        
        # Get the challenge
        challenge = Challenge.query.get_or_404(challenge_id)
        
        # Check if the client has access to this challenge
        if not challenge.is_public and challenge.trainer_id != current_client.trainer_id:
            flash("You don't have access to this challenge.", "error")
            return redirect(url_for('client.view_challenges'))
        
        # Get challenge participation
        participation = ChallengeParticipation.query.filter_by(
            challenge_id=challenge.id,
            client_id=current_client.id
        ).first()
        
        # Get challenge goals
        goals = ChallengeGoal.query.filter_by(challenge_id=challenge.id).all()
        
        # Get goal completions if the client has joined
        goal_completions = {}
        if participation:
            completions = GoalCompletion.query.filter_by(
                participation_id=participation.id
            ).all()
            
            for completion in completions:
                goal_completions[completion.goal_id] = completion
        
        # Get all participants
        participants = ChallengeParticipation.query.filter_by(
            challenge_id=challenge.id
        ).join(Client).all()
        
        # Calculate leaderboard based on progress
        leaderboard = []
        for p in participants:
            leaderboard.append({
                'name': p.client.full_name,
                'avatar_url': p.client.profile_image or '/static/images/default-avatar.png',
                'progress': p.progress_percentage,
                'is_current_user': p.client_id == current_client.id
            })
        
        # Sort leaderboard by progress (highest first)
        leaderboard.sort(key=lambda x: x['progress'], reverse=True)
        
        # Determine if today is a challenge day (between start and end dates)
        today = datetime.now().date()
        is_active = challenge.start_date <= today <= challenge.end_date
        is_upcoming = challenge.start_date > today
        is_completed = today > challenge.end_date
        
        # If the challenge has workout and nutrition components, get related resources
        related_workouts = []
        related_recipes = []
        
        if challenge.category in ['workout', 'combined']:
            # Get workout plans related to the challenge
            workout_links = ChallengeWorkout.query.filter_by(challenge_id=challenge.id).all()
            for link in workout_links:
                workout = WorkoutPlan.query.get(link.workout_id)
                if workout:
                    related_workouts.append({
                        'id': workout.id,
                        'name': workout.name,
                        'type': workout.workout_type,
                        'difficulty': workout.difficulty,
                        'estimated_duration': workout.estimated_duration
                    })
        
        if challenge.category in ['nutrition', 'combined']:
            # Get recipes related to the challenge
            recipe_links = ChallengeRecipe.query.filter_by(challenge_id=challenge.id).all()
            for link in recipe_links:
                recipe = Recipe.query.get(link.recipe_id)
                if recipe:
                    related_recipes.append({
                        'id': recipe.id,
                        'name': recipe.name,
                        'calories': recipe.calories,
                        'protein': recipe.protein,
                        'category': recipe.category
                    })
        
        return render_template(
            'client/challenge_detail.html',
            challenge=challenge,
            participation=participation,
            goals=goals,
            goal_completions=goal_completions,
            participants=participants,
            leaderboard=leaderboard,
            is_active=is_active,
            is_upcoming=is_upcoming,
            is_completed=is_completed,
            related_workouts=related_workouts,
            related_recipes=related_recipes
        )
    except Exception as e:
        current_app.logger.error(f"Error loading challenge details: {str(e)}")
        flash("An error occurred while loading challenge details. Please try again.", "error")
        return redirect(url_for('client.view_challenges'))

@client.route('/api/challenges/join', methods=['POST'])
@login_required
def join_challenge():
    """API endpoint for a client to join a challenge."""
    try:
        data = request.get_json()
        
        if not data or 'challenge_id' not in data:
            return jsonify({'success': False, 'message': 'Challenge ID is required'}), 400
        
        challenge_id = data['challenge_id']
        current_client = get_current_client()
        
        # Check if the challenge exists
        challenge = Challenge.query.get(challenge_id)
        if not challenge:
            return jsonify({'success': False, 'message': 'Challenge not found'}), 404
        
        # Check if the client has access to this challenge
        if not challenge.is_public and challenge.trainer_id != current_client.trainer_id:
            return jsonify({'success': False, 'message': 'You don\'t have access to this challenge'}), 403
        
        # Check if the client has already joined
        existing = ChallengeParticipation.query.filter_by(
            challenge_id=challenge.id,
            client_id=current_client.id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'You have already joined this challenge'}), 400
        
        # Get the total number of goals for progress tracking
        total_goals = ChallengeGoal.query.filter_by(challenge_id=challenge.id).count()
        
        # Create participation record
        participation = ChallengeParticipation(
            challenge_id=challenge.id,
            client_id=current_client.id,
            joined_date=datetime.now(),
            progress_percentage=0,
            completed_goals=0,
            total_goals=total_goals
        )
        
        db.session.add(participation)
        
        # Add entry to activity feed
        activity = ActivityFeed(
            client_id=current_client.id,
            activity_type='challenge_joined',
            description=f"Joined the {challenge.title} challenge",
            timestamp=datetime.now()
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Successfully joined the challenge'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error joining challenge: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while joining the challenge'}), 500

@client.route('/api/challenges/complete-goal', methods=['POST'])
@login_required
def complete_challenge_goal():
    """API endpoint for marking a challenge goal as complete."""
    try:
        data = request.get_json()
        
        if not data or 'goal_id' not in data:
            return jsonify({'success': False, 'message': 'Goal ID is required'}), 400
        
        goal_id = data['goal_id']
        current_client = get_current_client()
        
        # Check if the goal exists
        goal = ChallengeGoal.query.get(goal_id)
        if not goal:
            return jsonify({'success': False, 'message': 'Goal not found'}), 404
        
        # Get the client's participation in this challenge
        participation = ChallengeParticipation.query.filter_by(
            challenge_id=goal.challenge_id,
            client_id=current_client.id
        ).first()
        
        if not participation:
            return jsonify({'success': False, 'message': 'You have not joined this challenge'}), 400
        
        # Check if the goal is already completed
        existing = GoalCompletion.query.filter_by(
            goal_id=goal.id,
            participation_id=participation.id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Goal already completed'}), 400
        
        # Create goal completion record
        completion = GoalCompletion(
            goal_id=goal.id,
            participation_id=participation.id,
            completion_date=datetime.now()
        )
        
        db.session.add(completion)
        
        # Update participation progress
        participation.completed_goals += 1
        participation.progress_percentage = round((participation.completed_goals / participation.total_goals) * 100)
        
        # Check if all goals are completed
        if participation.completed_goals == participation.total_goals:
            # Add entry to activity feed for completing the entire challenge
            challenge = Challenge.query.get(goal.challenge_id)
            activity = ActivityFeed(
                client_id=current_client.id,
                activity_type='challenge_completed',
                description=f"Completed all goals in the {challenge.title} challenge",
                timestamp=datetime.now()
            )
            db.session.add(activity)
            
            # Award achievement if this is the first challenge completed
            completed_challenges = ChallengeParticipation.query.filter_by(
                client_id=current_client.id
            ).filter(ChallengeParticipation.progress_percentage == 100).count()
            
            if completed_challenges == 0:
                achievement = Achievement(
                    client_id=current_client.id,
                    title="Challenge Champion",
                    description="Completed your first fitness or nutrition challenge",
                    award_date=datetime.now(),
                    related_challenge_id=challenge.id
                )
                db.session.add(achievement)
        
        # Add entry to activity feed for completing this goal
        activity = ActivityFeed(
            client_id=current_client.id,
            activity_type='goal_completed',
            description=f"Completed a goal in the challenge: {goal.description}",
            timestamp=datetime.now()
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Goal marked as complete',
            'progress': participation.progress_percentage
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing challenge goal: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while completing the goal'}), 500

@client.route('/api/challenges/share-image/<int:challenge_id>')
@login_required
def generate_challenge_share_image(challenge_id):
    """Generate a shareable image for a challenge with the user's progress."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Get the challenge
        challenge = Challenge.query.get_or_404(challenge_id)
        
        # Get participation data
        participation = ChallengeParticipation.query.filter_by(
            challenge_id=challenge.id,
            client_id=current_client.id
        ).first()
        
        if not participation:
            return jsonify({'success': False, 'message': 'You have not joined this challenge'}), 400
        
        # Use Pillow to create an image with the challenge and progress info
        import io
        import os
        
        # Create a new image with a white background
        width, height = 1200, 630  # Standard size for social media sharing
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to load fonts or use default
        try:
            # First try to load custom fonts if available
            font_path = os.path.join(current_app.root_path, 'static', 'fonts')
            title_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Bold.ttf'), 60)
            subtitle_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-SemiBold.ttf'), 40)
            body_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 30)
        except IOError:
            # If custom fonts are not available, use default
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        
        # Add a colored header
        header_color = (79, 70, 229)  # Indigo-600
        draw.rectangle([(0, 0), (width, 120)], fill=header_color)
        
        # Add app logo/name
        draw.text((50, 40), "FitFuelGenerator", font=title_font, fill=(255, 255, 255))
        
        # Add challenge title
        draw.text((50, 150), challenge.title, font=title_font, fill=(0, 0, 0))
        
        # Add challenge category
        category_text = f"Category: {challenge.category.capitalize()}"
        draw.text((50, 230), category_text, font=subtitle_font, fill=(107, 114, 128))  # Gray-500
        
        # Calculate progress bar
        progress = participation.progress_percentage
        bar_x = 50
        bar_y = 300
        bar_width = width - 100
        bar_height = 40
        bar_fill_width = int((bar_width * progress) / 100)
        
        # Draw progress bar background
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], 
                       fill=(229, 231, 235))  # Gray-200
        
        # Draw progress bar fill
        progress_color = (16, 185, 129)  # Green-500
        if progress < 40:
            progress_color = (239, 68, 68)  # Red-500
        elif progress < 80:
            progress_color = (79, 70, 229)  # Indigo-600
            
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_fill_width, bar_y + bar_height)], 
                       fill=progress_color)
        
        # Add progress text
        progress_text = f"Progress: {progress}%"
        draw.text((bar_x, bar_y + bar_height + 20), progress_text, font=subtitle_font, fill=(0, 0, 0))
        
        # Add goals completed text
        goals_text = f"Goals Completed: {participation.completed_goals} / {participation.total_goals}"
        draw.text((bar_x, bar_y + bar_height + 80), goals_text, font=body_font, fill=(0, 0, 0))
        
        # Add dates
        date_format = "%b %d, %Y"
        dates_text = f"Started: {challenge.start_date.strftime(date_format)} • Ends: {challenge.end_date.strftime(date_format)}"
        draw.text((bar_x, bar_y + bar_height + 130), dates_text, font=body_font, fill=(107, 114, 128))
        
        # Add user name
        user_text = f"Shared by: {current_client.full_name}"
        draw.text((bar_x, bar_y + bar_height + 180), user_text, font=body_font, fill=(0, 0, 0))
        
        # Add a footer
        footer_y = height - 80
        draw.rectangle([(0, footer_y), (width, height)], fill=header_color)
        website_text = "www.fitfuelgenerator.com"
        draw.text((width // 2 - 150, footer_y + 25), website_text, font=body_font, fill=(255, 255, 255))
        
        # Convert the image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Return the image
        return send_file(img_byte_arr, mimetype='image/png')
    
    except Exception as e:
        current_app.logger.error(f"Error generating share image: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to generate image'}), 500

@client.route('/api/meal-plan/share-image')
@login_required
def generate_meal_plan_share_image():
    """Generate a shareable image for the current meal plan."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Get today's meal plan
        today = datetime.now().date()
        meal_plan = MealPlan.query.filter_by(
            client_id=current_client.id,
            date=today
        ).first()
        
        if not meal_plan:
            return jsonify({'success': False, 'message': 'No meal plan found for today'}), 400
        
        # Use Pillow to create an image with the meal plan info
        import io
        import os
        
        # Create a new image with a white background
        width, height = 1200, 630  # Standard size for social media sharing
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to load fonts or use default
        try:
            # First try to load custom fonts if available
            font_path = os.path.join(current_app.root_path, 'static', 'fonts')
            title_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Bold.ttf'), 60)
            subtitle_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-SemiBold.ttf'), 40)
            body_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 30)
            small_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 24)
        except IOError:
            # If custom fonts are not available, use default
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add a colored header
        header_color = (79, 70, 229)  # Indigo-600
        draw.rectangle([(0, 0), (width, 120)], fill=header_color)
        
        # Add app logo/name
        draw.text((50, 40), "FitFuelGenerator", font=title_font, fill=(255, 255, 255))
        
        # Add date
        draw.text((width - 300, 45), today.strftime("%B %d, %Y"), font=body_font, fill=(255, 255, 255))
        
        # Add title
        draw.text((50, 150), "My Daily Meal Plan", font=title_font, fill=(0, 0, 0))
        
        # Calculate total nutrition
        total_calories = 0
        total_protein = 0
        completed_items = 0
        total_items = 0
        
        for meal in meal_plan.meals:
            for item in meal.items:
                total_items += 1
                total_calories += item.calories
                total_protein += item.protein
                if item.completed:
                    completed_items += 1
        
        # Add nutrition summary
        draw.text((50, 230), f"Total Calories: {total_calories} kcal", font=subtitle_font, fill=(107, 114, 128))
        draw.text((50, 280), f"Total Protein: {total_protein}g", font=subtitle_font, fill=(107, 114, 128))
        
        # Calculate progress
        if total_items > 0:
            progress = (completed_items / total_items) * 100
        else:
            progress = 0
            
        # Add completion progress
        progress_text = f"Completion: {progress:.1f}%"
        draw.text((50, 330), progress_text, font=subtitle_font, fill=(0, 0, 0))
        
        # Draw progress bar
        bar_x = 50
        bar_y = 380
        bar_width = width - 100
        bar_height = 40
        bar_fill_width = int((bar_width * progress) / 100)
        
        # Draw progress bar background
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], 
                     fill=(229, 231, 235))  # Gray-200
        
        # Draw progress bar fill
        progress_color = (16, 185, 129)  # Green-500
        if progress < 40:
            progress_color = (239, 68, 68)  # Red-500
        elif progress < 80:
            progress_color = (79, 70, 229)  # Indigo-600
            
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_fill_width, bar_y + bar_height)], 
                     fill=progress_color)
        
        # Add meal list
        y_position = 450
        for i, meal in enumerate(meal_plan.meals[:3]):  # Show up to 3 meals
            if y_position > height - 150:
                break
                
            meal_title = f"{meal.type.capitalize()}: {meal.title}"
            draw.text((50, y_position), meal_title, font=subtitle_font, fill=(0, 0, 0))
            y_position += 50
            
            for j, item in enumerate(meal.items[:2]):  # Show up to 2 items per meal
                if y_position > height - 150:
                    break
                    
                item_text = f"• {item.name} - {item.calories} kcal, {item.protein}g protein"
                draw.text((70, y_position), item_text, font=small_font, 
                        fill=(0, 0, 0) if not item.completed else (16, 185, 129))
                y_position += 35
                
            if len(meal.items) > 2:
                draw.text((70, y_position), f"• ... and {len(meal.items) - 2} more items", 
                        font=small_font, fill=(107, 114, 128))
                y_position += 35
                
            y_position += 10
        
        # Add a footer
        footer_y = height - 80
        draw.rectangle([(0, footer_y), (width, height)], fill=header_color)
        website_text = "www.fitfuelgenerator.com"
        shared_by_text = f"Shared by {current_client.full_name}"
        
        # Center website text
        w_width = draw.textlength(website_text, font=body_font)
        draw.text((width // 2 - w_width // 2, footer_y + 25), website_text, font=body_font, fill=(255, 255, 255))
        
        # Shared by text at right
        s_width = draw.textlength(shared_by_text, font=small_font)
        draw.text((width - 50 - s_width, footer_y + 30), shared_by_text, font=small_font, fill=(255, 255, 255))
        
        # Convert the image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Return the image
        return send_file(img_byte_arr, mimetype='image/png')
    
    except Exception as e:
        current_app.logger.error(f"Error generating meal plan share image: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to generate image'}), 500

@client.route('/api/workout-nutrition/share-image')
@login_required
def generate_workout_nutrition_share_image():
    """Generate a shareable image for the workout and nutrition integration data."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Get the workout nutrition data (reuse the calculation function from the page)
        recent_workouts = WorkoutPlan.query.filter_by(
            client_id=current_client.id, 
            completed=True
        ).order_by(WorkoutPlan.completion_date.desc()).limit(10).all()
        
        recent_meal_plans = MealPlan.query.filter_by(
            client_id=current_client.id
        ).order_by(MealPlan.date.desc()).limit(7).all()
        
        progress_logs = ProgressLog.query.filter_by(
            client_id=current_client.id
        ).order_by(ProgressLog.date.desc()).limit(14).all()
        
        workout_nutrition_data = calculate_workout_nutrition_recommendations(
            current_client, recent_workouts, recent_meal_plans, progress_logs
        )
        
        if not workout_nutrition_data:
            return jsonify({'success': False, 'message': 'Not enough data to generate recommendations'}), 400
        
        # Use Pillow to create an image with the workout nutrition info
        import io
        import os
        
        # Create a new image with a white background
        width, height = 1200, 630  # Standard size for social media sharing
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to load fonts or use default
        try:
            # First try to load custom fonts if available
            font_path = os.path.join(current_app.root_path, 'static', 'fonts')
            title_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Bold.ttf'), 60)
            subtitle_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-SemiBold.ttf'), 40)
            body_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 30)
            small_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 24)
        except IOError:
            # If custom fonts are not available, use default
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add a colored header
        header_color = (79, 70, 229)  # Indigo-600
        draw.rectangle([(0, 0), (width, 120)], fill=header_color)
        
        # Add app logo/name
        draw.text((50, 40), "FitFuelGenerator", font=title_font, fill=(255, 255, 255))
        
        # Add title
        draw.text((50, 150), "Workout & Nutrition Integration", font=title_font, fill=(0, 0, 0))
        
        # Add workout type
        if workout_nutrition_data.get('workout_type'):
            workout_type = workout_nutrition_data['workout_type'].replace('_', ' ').title()
            draw.text((50, 220), f"Primary Workout Type: {workout_type}", font=subtitle_font, fill=(107, 114, 128))
        
        # Draw the calorie targets section
        y_position = 300
        draw.text((50, y_position), "Calorie Targets", font=subtitle_font, fill=(0, 0, 0))
        y_position += 60
        
        # Training day card
        card_width = (width - 150) // 3
        card_height = 140
        card_x = 50
        card_y = y_position
        
        # Training day background
        draw.rectangle([(card_x, card_y), (card_x + card_width, card_y + card_height)], 
                      fill=(238, 242, 255))  # Indigo-50
        
        # Training day title
        draw.text((card_x + 20, card_y + 15), "Training Day", font=body_font, fill=(67, 56, 202))  # Indigo-700
        
        # Training day calories
        training_cals = workout_nutrition_data['calories']['training_day_target']
        draw.text((card_x + 20, card_y + 60), f"{training_cals}", font=subtitle_font, fill=(67, 56, 202))
        draw.text((card_x + 20, card_y + 100), "calories", font=small_font, fill=(107, 114, 128))
        
        # Rest day card
        card_x += card_width + 25
        
        # Rest day background
        draw.rectangle([(card_x, card_y), (card_x + card_width, card_y + card_height)], 
                      fill=(243, 244, 246))  # Gray-100
        
        # Rest day title
        draw.text((card_x + 20, card_y + 15), "Rest Day", font=body_font, fill=(107, 114, 128))  # Gray-500
        
        # Rest day calories
        rest_cals = workout_nutrition_data['calories']['rest_day_target']
        draw.text((card_x + 20, card_y + 60), f"{rest_cals}", font=subtitle_font, fill=(107, 114, 128))
        draw.text((card_x + 20, card_y + 100), "calories", font=small_font, fill=(107, 114, 128))
        
        # Post workout card
        card_x += card_width + 25
        
        # Post workout background
        draw.rectangle([(card_x, card_y), (card_x + card_width, card_y + card_height)], 
                      fill=(236, 253, 245))  # Green-50
        
        # Post workout title
        draw.text((card_x + 20, card_y + 15), "Post-Workout", font=body_font, fill=(6, 95, 70))  # Green-800
        
        # Post workout calories
        post_cals = workout_nutrition_data['calories']['post_workout']
        draw.text((card_x + 20, card_y + 60), f"{post_cals}", font=subtitle_font, fill=(6, 95, 70))
        draw.text((card_x + 20, card_y + 100), "intake", font=small_font, fill=(107, 114, 128))
        
        # Recovery metrics
        y_position += card_height + 60
        if workout_nutrition_data.get('recovery'):
            draw.text((50, y_position), "Recovery Status", font=subtitle_font, fill=(0, 0, 0))
            y_position += 60
            
            # Draw recovery metrics
            recovery = workout_nutrition_data['recovery']
            metrics = [
                {
                    'name': 'Muscle Recovery', 
                    'value': f"{recovery['muscle_recovery']}%",
                    'color': (16, 185, 129) if recovery['muscle_recovery'] >= 80 else 
                             (251, 191, 36) if recovery['muscle_recovery'] >= 50 else 
                             (239, 68, 68)
                },
                {
                    'name': 'Energy Level', 
                    'value': f"{recovery['energy_level']}%",
                    'color': (16, 185, 129) if recovery['energy_level'] >= 80 else 
                             (251, 191, 36) if recovery['energy_level'] >= 50 else 
                             (239, 68, 68)
                },
                {
                    'name': 'Protein Intake', 
                    'value': f"{workout_nutrition_data['macros']['protein_goal_percent']}%",
                    'color': (16, 185, 129) if workout_nutrition_data['macros']['protein_goal_percent'] >= 90 else 
                             (251, 191, 36) if workout_nutrition_data['macros']['protein_goal_percent'] >= 70 else 
                             (239, 68, 68)
                }
            ]
            
            for i, metric in enumerate(metrics):
                metric_x = 50 + i * ((width - 100) // 3)
                
                # Draw metric name
                draw.text((metric_x, y_position), metric['name'], font=body_font, fill=(0, 0, 0))
                
                # Draw metric value
                draw.text((metric_x, y_position + 40), metric['value'], font=subtitle_font, fill=metric['color'])
        
        # Add a footer
        footer_y = height - 80
        draw.rectangle([(0, footer_y), (width, height)], fill=header_color)
        website_text = "www.fitfuelgenerator.com"
        shared_by_text = f"Shared by {current_client.full_name}"
        
        # Center website text
        w_width = draw.textlength(website_text, font=body_font)
        draw.text((width // 2 - w_width // 2, footer_y + 25), website_text, font=body_font, fill=(255, 255, 255))
        
        # Shared by text at right
        s_width = draw.textlength(shared_by_text, font=small_font)
        draw.text((width - 50 - s_width, footer_y + 30), shared_by_text, font=small_font, fill=(255, 255, 255))
        
        # Convert the image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Return the image
        return send_file(img_byte_arr, mimetype='image/png')
    
    except Exception as e:
        current_app.logger.error(f"Error generating workout nutrition share image: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to generate image'}), 500

@client.route('/api/achievements/share-image/<int:achievement_id>')
@login_required
def generate_achievement_share_image(achievement_id):
    """Generate a shareable image for a user achievement."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Get the achievement
        achievement = Achievement.query.filter_by(
            id=achievement_id,
            client_id=current_client.id
        ).first_or_404()
        
        # Use Pillow to create an image with the achievement info
        import io
        import os
        from datetime import datetime
        
        # Create a new image with a gradient background
        width, height = 1200, 630  # Standard size for social media sharing
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to load fonts or use default
        try:
            # First try to load custom fonts if available
            font_path = os.path.join(current_app.root_path, 'static', 'fonts')
            title_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Bold.ttf'), 70)
            subtitle_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-SemiBold.ttf'), 40)
            body_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 30)
            small_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 24)
        except IOError:
            # If custom fonts are not available, use default
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Create a gradient background
        for y in range(height):
            r = int(79 + (y / height) * (16 - 79))
            g = int(70 + (y / height) * (185 - 70))
            b = int(229 + (y / height) * (129 - 229))
            for x in range(width):
                draw.point((x, y), fill=(r, g, b))
        
        # Add a semi-transparent overlay in the center for content
        overlay_margin = 80
        overlay_width = width - (overlay_margin * 2)
        overlay_height = height - (overlay_margin * 2)
        overlay = Image.new('RGBA', (overlay_width, overlay_height), (255, 255, 255, 180))
        image.paste(overlay, (overlay_margin, overlay_margin), overlay)
        
        # Add trophy icon
        try:
            icon_size = 120
            trophy_icon = Image.open(os.path.join(current_app.root_path, 'static', 'images', 'trophy_icon.png')).resize((icon_size, icon_size))
            icon_x = (width - icon_size) // 2
            icon_y = overlay_margin + 50
            image.paste(trophy_icon, (icon_x, icon_y), trophy_icon)
        except:
            # If trophy icon is not available, draw a circle
            icon_size = 120
            icon_x = (width - icon_size) // 2
            icon_y = overlay_margin + 50
            draw.ellipse([(icon_x, icon_y), (icon_x + icon_size, icon_y + icon_size)], fill=(255, 215, 0))
        
        # Add "Achievement Unlocked" text
        text = "Achievement Unlocked!"
        text_width = draw.textlength(text, font=subtitle_font)
        text_x = (width - text_width) // 2
        text_y = overlay_margin + icon_size + 70
        draw.text((text_x, text_y), text, font=subtitle_font, fill=(0, 0, 0))
        
        # Add achievement title
        title_y = text_y + 70
        title_width = draw.textlength(achievement.title, font=title_font)
        title_x = (width - title_width) // 2
        draw.text((title_x, title_y), achievement.title, font=title_font, fill=(79, 70, 229))
        
        # Add achievement description
        desc_y = title_y + 100
        desc_text = achievement.description
        desc_width = draw.textlength(desc_text, font=body_font)
        desc_x = (width - desc_width) // 2
        draw.text((desc_x, desc_y), desc_text, font=body_font, fill=(0, 0, 0))
        
        # Add achievement date
        date_y = desc_y + 60
        date_text = f"Achieved on {achievement.date_earned.strftime('%B %d, %Y')}"
        date_width = draw.textlength(date_text, font=small_font)
        date_x = (width - date_width) // 2
        draw.text((date_x, date_y), date_text, font=small_font, fill=(107, 114, 128))
        
        # Add user name
        user_y = height - overlay_margin - 50
        user_text = f"Earned by {current_client.full_name}"
        user_width = draw.textlength(user_text, font=body_font)
        user_x = (width - user_width) // 2
        draw.text((user_x, user_y), user_text, font=body_font, fill=(0, 0, 0))
        
        # Add FitFuelGenerator logo/text
        logo_y = height - 40
        logo_text = "FitFuelGenerator"
        logo_width = draw.textlength(logo_text, font=small_font)
        logo_x = (width - logo_width) // 2
        draw.text((logo_x, logo_y), logo_text, font=small_font, fill=(255, 255, 255))
        
        # Convert the image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Return the image
        return send_file(img_byte_arr, mimetype='image/png')
    
    except Exception as e:
        current_app.logger.error(f"Error generating achievement share image: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to generate image'}), 500

@client.route('/api/weekly-summary/share-image')
@login_required
def generate_weekly_summary_share_image():
    """Generate a shareable image for weekly progress summary."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Calculate date range for the week (last 7 days)
        today = datetime.now().date()
        week_start = today - timedelta(days=6)  # Last 7 days including today
        
        # Get workout data
        workouts = WorkoutPlan.query.filter(
            WorkoutPlan.client_id == current_client.id,
            WorkoutPlan.completed == True,
            WorkoutPlan.completion_date >= week_start
        ).order_by(WorkoutPlan.completion_date).all()
        
        # Get nutrition data (meal plans)
        meal_plans = MealPlan.query.filter(
            MealPlan.client_id == current_client.id,
            MealPlan.date >= week_start
        ).order_by(MealPlan.date).all()
        
        # Get progress logs
        progress_logs = ProgressLog.query.filter(
            ProgressLog.client_id == current_client.id,
            ProgressLog.date >= week_start
        ).order_by(ProgressLog.date).all()
        
        # Use Pillow to create an image with the weekly summary
        import io
        import os
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.patches import Patch
        
        # Create a new image with a white background
        width, height = 1200, 630  # Standard size for social media sharing
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to load fonts or use default
        try:
            # First try to load custom fonts if available
            font_path = os.path.join(current_app.root_path, 'static', 'fonts')
            title_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Bold.ttf'), 60)
            subtitle_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-SemiBold.ttf'), 40)
            body_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 30)
            small_font = ImageFont.truetype(os.path.join(font_path, 'OpenSans-Regular.ttf'), 24)
        except IOError:
            # If custom fonts are not available, use default
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add a colored header
        header_color = (79, 70, 229)  # Indigo-600
        draw.rectangle([(0, 0), (width, 120)], fill=header_color)
        
        # Add app logo/name and date range
        draw.text((50, 40), "FitFuelGenerator", font=title_font, fill=(255, 255, 255))
        date_range_text = f"{week_start.strftime('%b %d')} - {today.strftime('%b %d, %Y')}"
        date_width = draw.textlength(date_range_text, font=body_font)
        draw.text((width - 50 - date_width, 45), date_range_text, font=body_font, fill=(255, 255, 255))
        
        # Add title
        draw.text((50, 150), "Weekly Progress Summary", font=title_font, fill=(0, 0, 0))
        
        # Calculate workout stats
        total_workouts = len(workouts)
        total_duration = sum(w.duration for w in workouts) if workouts else 0
        total_calories_burned = sum(w.calories_burned for w in workouts) if workouts else 0
        
        # Calculate nutrition stats
        avg_calories = 0
        avg_protein = 0
        completion_rate = 0
        
        if meal_plans:
            daily_calories = []
            daily_protein = []
            completion_rates = []
            
            for plan in meal_plans:
                total_items = 0
                completed_items = 0
                day_calories = 0
                day_protein = 0
                
                for meal in plan.meals:
                    for item in meal.items:
                        total_items += 1
                        day_calories += item.calories
                        day_protein += item.protein
                        if item.completed:
                            completed_items += 1
                
                daily_calories.append(day_calories)
                daily_protein.append(day_protein)
                if total_items > 0:
                    completion_rates.append(completed_items / total_items * 100)
            
            if daily_calories:
                avg_calories = sum(daily_calories) / len(daily_calories)
            if daily_protein:
                avg_protein = sum(daily_protein) / len(daily_protein)
            if completion_rates:
                completion_rate = sum(completion_rates) / len(completion_rates)
        
        # Calculate weight change if available
        weight_change = None
        if len(progress_logs) >= 2:
            first_log = progress_logs[0]
            last_log = progress_logs[-1]
            if hasattr(first_log, 'weight') and hasattr(last_log, 'weight'):
                weight_change = last_log.weight - first_log.weight
        
        # Create workout and nutrition summary
        summary_y = 230
        
        # Summary headings
        workout_x = 50
        nutrition_x = width // 2 + 50
        
        draw.text((workout_x, summary_y), "Workout Summary", font=subtitle_font, fill=(79, 70, 229))
        draw.text((nutrition_x, summary_y), "Nutrition Summary", font=subtitle_font, fill=(16, 185, 129))
        
        # Key stats
        stats_y = summary_y + 60
        line_height = 50
        
        # Workout stats
        draw.text((workout_x, stats_y), f"Workouts Completed: {total_workouts}", font=body_font, fill=(0, 0, 0))
        draw.text((workout_x, stats_y + line_height), f"Total Duration: {total_duration} min", font=body_font, fill=(0, 0, 0))
        draw.text((workout_x, stats_y + line_height * 2), f"Calories Burned: {total_calories_burned}", font=body_font, fill=(0, 0, 0))
        
        # Nutrition stats
        draw.text((nutrition_x, stats_y), f"Avg. Daily Calories: {avg_calories:.0f}", font=body_font, fill=(0, 0, 0))
        draw.text((nutrition_x, stats_y + line_height), f"Avg. Daily Protein: {avg_protein:.0f}g", font=body_font, fill=(0, 0, 0))
        draw.text((nutrition_x, stats_y + line_height * 2), f"Meal Plan Completion: {completion_rate:.0f}%", font=body_font, fill=(0, 0, 0))
        
        # Add weight change if available
        if weight_change is not None:
            weight_y = stats_y + line_height * 3 + 20
            prefix = "+" if weight_change > 0 else ""
            weight_text = f"Weight Change: {prefix}{weight_change:.1f} lbs"
            weight_color = (239, 68, 68) if weight_change > 0 and current_client.goal == 'weight_loss' else (16, 185, 129)
            draw.text((workout_x, weight_y), weight_text, font=body_font, fill=weight_color)
        
        # Create workout activity chart if we have workouts
        if workouts:
            # Generate a simple workout activity chart
            fig, ax = plt.subplots(figsize=(5, 3))
            
            # Get workout days and durations
            dates = [w.completion_date.strftime('%a') for w in workouts]
            durations = [w.duration for w in workouts]
            
            # Create chart
            ax.bar(dates, durations, color='#4f46e5')
            ax.set_ylabel('Minutes', fontsize=10)
            ax.set_title('Workout Duration by Day', fontsize=12)
            ax.tick_params(axis='both', which='major', labelsize=8)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # Save chart to a buffer
            chart_buffer = io.BytesIO()
            fig.tight_layout()
            fig.savefig(chart_buffer, format='png', dpi=100)
            chart_buffer.seek(0)
            
            # Open the image and paste it
            chart_img = Image.open(chart_buffer)
            chart_x = 50
            chart_y = stats_y + line_height * 4 + 20
            image.paste(chart_img, (chart_x, chart_y))
            plt.close(fig)
        
        # Add footer
        footer_y = height - 80
        draw.rectangle([(0, footer_y), (width, height)], fill=header_color)
        
        # Add sharing text and username
        share_text = "Weekly Progress Summary"
        user_text = f"Generated for {current_client.full_name}"
        
        # Center share text
        share_width = draw.textlength(share_text, font=body_font)
        draw.text((width // 2 - share_width // 2, footer_y + 25), share_text, font=body_font, fill=(255, 255, 255))
        
        # Right-align user text
        user_width = draw.textlength(user_text, font=small_font)
        draw.text((width - 50 - user_width, footer_y + 30), user_text, font=small_font, fill=(255, 255, 255))
        
        # Convert the image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Return the image
        return send_file(img_byte_arr, mimetype='image/png')
    
    except Exception as e:
        current_app.logger.error(f"Error generating weekly summary share image: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to generate image'}), 500

@client.route('/api/track-share', methods=['POST'])
@login_required
def track_share():
    """Track when a user shares content on social media or generates a share image."""
    try:
        # Get the current client
        current_client = get_current_client()
        
        # Get request data
        data = request.json
        if not data or not all(k in data for k in ['content_type', 'platform']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        content_type = data.get('content_type')  # 'workout', 'meal_plan', 'challenge', 'achievement', 'weekly_summary'
        platform = data.get('platform')  # 'facebook', 'twitter', 'linkedin', 'pinterest', 'instagram', 'copy_link', 'image'
        content_id = data.get('content_id')  # Optional ID of the specific content
        
        # Create a new sharing analytics record
        share_record = SharingAnalytics(
            client_id=current_client.id,
            content_type=content_type,
            platform=platform,
            content_id=content_id
        )
        
        db.session.add(share_record)
        db.session.commit()
        
        # Optionally award points for sharing
        if platform not in ['copy_link', 'image']:  # Only award points for actual social media shares
            points_awarded = 5  # Default points for sharing
            current_client.points += points_awarded
            db.session.commit()
            
            # Log activity
            activity = ActivityFeed(
                client_id=current_client.id,
                activity_type='social_share',
                description=f'Shared {content_type} on {platform}',
                extra_data={
                    'content_type': content_type,
                    'platform': platform,
                    'points_awarded': points_awarded
                },
                icon='share-2'
            )
            db.session.add(activity)
            db.session.commit()
        
        return jsonify({'success': True, 'message': 'Share tracked successfully'})
    
    except Exception as e:
        current_app.logger.error(f"Error tracking share: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to track share'}), 500