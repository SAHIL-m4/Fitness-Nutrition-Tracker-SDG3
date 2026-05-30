from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import User, NutritionLog, FitnessLog, WaterLog, Goal

dashboard_bp = Blueprint("dashboard", __name__)


def get_daily_summary(user_id, target_date=None):
    """Return today's nutrition, fitness, and water totals for a user."""
    if target_date is None:
        target_date = date.today()

    nutrition = db.session.query(
        func.sum(NutritionLog.calories * NutritionLog.quantity).label("calories"),
        func.sum(NutritionLog.protein_g * NutritionLog.quantity).label("protein"),
        func.sum(NutritionLog.carbs_g * NutritionLog.quantity).label("carbs"),
        func.sum(NutritionLog.fat_g * NutritionLog.quantity).label("fat"),
    ).filter(
        NutritionLog.user_id == user_id,
        NutritionLog.log_date == target_date
    ).first()

    fitness = db.session.query(
        func.sum(FitnessLog.duration_minutes).label("minutes"),
        func.sum(FitnessLog.calories_burned).label("calories_burned"),
        func.count(FitnessLog.id).label("sessions"),
    ).filter(
        FitnessLog.user_id == user_id,
        FitnessLog.log_date == target_date
    ).first()

    water = db.session.query(
        func.sum(WaterLog.amount_ml).label("total_ml")
    ).filter(
        WaterLog.user_id == user_id,
        WaterLog.log_date == target_date
    ).scalar() or 0

    return {
        "calories": round(nutrition.calories or 0, 1),
        "protein": round(nutrition.protein or 0, 1),
        "carbs": round(nutrition.carbs or 0, 1),
        "fat": round(nutrition.fat or 0, 1),
        "exercise_minutes": round(fitness.minutes or 0, 1),
        "calories_burned": round(fitness.calories_burned or 0, 1),
        "exercise_sessions": fitness.sessions or 0,
        "water_ml": round(water, 0),
    }


def get_weekly_calories(user_id):
    """Return calorie data for the last 7 days."""
    today = date.today()
    result = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        total = db.session.query(
            func.sum(NutritionLog.calories * NutritionLog.quantity)
        ).filter(
            NutritionLog.user_id == user_id,
            NutritionLog.log_date == day
        ).scalar() or 0
        result.append({"date": day.strftime("%a"), "calories": round(total, 0)})
    return result


@dashboard_bp.route("/")
@login_required
def index():
    today_summary = get_daily_summary(current_user.id)
    weekly_data = get_weekly_calories(current_user.id)
    active_goal = Goal.query.filter_by(user_id=current_user.id, is_active=True).first()
    recent_nutrition = NutritionLog.query.filter_by(
        user_id=current_user.id
    ).order_by(NutritionLog.logged_at.desc()).limit(5).all()
    recent_fitness = FitnessLog.query.filter_by(
        user_id=current_user.id
    ).order_by(FitnessLog.logged_at.desc()).limit(5).all()

    tdee = current_user.calculate_tdee()
    calorie_target = (active_goal.target_calories if active_goal and active_goal.target_calories else tdee) or 2000

    from datetime import datetime as _dt
    return render_template(
        "dashboard/index.html",
        summary=today_summary,
        weekly_data=weekly_data,
        goal=active_goal,
        recent_nutrition=recent_nutrition,
        recent_fitness=recent_fitness,
        calorie_target=calorie_target,
        tdee=tdee,
        now=_dt.now(),
        today=date.today(),
    )


@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def setup_profile():
    if request.method == "POST":
        current_user.age = request.form.get("age", type=int)
        current_user.gender = request.form.get("gender")
        current_user.height_cm = request.form.get("height_cm", type=float)
        current_user.weight_kg = request.form.get("weight_kg", type=float)
        current_user.activity_level = request.form.get("activity_level", "moderate")
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("dashboard.goals"))

    return render_template("dashboard/profile.html")


@dashboard_bp.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    active_goal = Goal.query.filter_by(user_id=current_user.id, is_active=True).first()

    if request.method == "POST":
        # Deactivate existing goals
        Goal.query.filter_by(user_id=current_user.id).update({"is_active": False})

        goal = Goal(
            user_id=current_user.id,
            goal_type=request.form.get("goal_type"),
            target_weight_kg=request.form.get("target_weight_kg", type=float),
            target_calories=request.form.get("target_calories", type=int),
            target_protein_g=request.form.get("target_protein_g", type=int),
            target_water_ml=request.form.get("target_water_ml", type=int) or 2500,
            target_exercise_minutes=request.form.get("target_exercise_minutes", type=int) or 150,
        )
        db.session.add(goal)
        db.session.commit()
        flash("Goal saved!", "success")
        return redirect(url_for("dashboard.index"))

    tdee = current_user.calculate_tdee()
    return render_template("dashboard/goals.html", goal=active_goal, tdee=tdee)


@dashboard_bp.route("/api/summary")
@login_required
def api_summary():
    summary = get_daily_summary(current_user.id)
    return jsonify(summary)
