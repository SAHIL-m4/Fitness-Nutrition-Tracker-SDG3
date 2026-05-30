from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import FitnessLog, WaterLog

fitness_bp = Blueprint("fitness", __name__)

EXERCISE_CATEGORIES = ["cardio", "strength", "flexibility", "sports", "other"]
INTENSITY_LEVELS = ["low", "moderate", "high"]

EXERCISE_LIBRARY = {
    "cardio": ["Running", "Walking", "Cycling", "Swimming", "Jump Rope", "Rowing", "Elliptical", "HIIT", "Dancing"],
    "strength": ["Push-ups", "Pull-ups", "Squats", "Deadlift", "Bench Press", "Bicep Curls", "Plank", "Lunges"],
    "flexibility": ["Yoga", "Stretching", "Pilates", "Foam Rolling"],
    "sports": ["Basketball", "Football", "Tennis", "Badminton", "Volleyball", "Soccer", "Cricket"],
    "other": ["Hiking", "Rock Climbing", "Martial Arts", "Boxing", "Gymnastics"],
}


@fitness_bp.route("/")
@login_required
def index():
    selected_date = request.args.get("date", date.today().isoformat())
    try:
        log_date = date.fromisoformat(selected_date)
    except ValueError:
        log_date = date.today()

    fitness_logs = FitnessLog.query.filter_by(
        user_id=current_user.id, log_date=log_date
    ).order_by(FitnessLog.logged_at.desc()).all()

    water_logs = WaterLog.query.filter_by(
        user_id=current_user.id, log_date=log_date
    ).order_by(WaterLog.logged_at.desc()).all()

    water_total = sum(w.amount_ml for w in water_logs)

    fitness_totals = db.session.query(
        func.sum(FitnessLog.duration_minutes).label("duration"),
        func.sum(FitnessLog.calories_burned).label("calories"),
    ).filter(
        FitnessLog.user_id == current_user.id,
        FitnessLog.log_date == log_date
    ).first()

    # Weekly exercise minutes for chart
    today = date.today()
    weekly_exercise = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        mins = db.session.query(func.sum(FitnessLog.duration_minutes)).filter(
            FitnessLog.user_id == current_user.id,
            FitnessLog.log_date == day
        ).scalar() or 0
        weekly_exercise.append({"date": day.strftime("%a"), "minutes": round(mins, 0)})

    return render_template(
        "fitness/index.html",
        fitness_logs=fitness_logs,
        water_logs=water_logs,
        water_total=water_total,
        totals=fitness_totals,
        log_date=log_date,
        weekly_exercise=weekly_exercise,
    )


@fitness_bp.route("/log", methods=["GET", "POST"])
@login_required
def log_exercise():
    if request.method == "POST":
        duration = request.form.get("duration_minutes", type=float)
        if not duration or duration <= 0:
            flash("Duration must be greater than 0.", "danger")
            return redirect(url_for("fitness.log_exercise"))

        log = FitnessLog(
            user_id=current_user.id,
            log_date=date.fromisoformat(request.form.get("log_date", date.today().isoformat())),
            exercise_name=request.form.get("exercise_name", "").strip(),
            category=request.form.get("category", "other"),
            duration_minutes=duration,
            intensity=request.form.get("intensity", "moderate"),
            sets=request.form.get("sets", type=int),
            reps=request.form.get("reps", type=int),
            weight_kg=request.form.get("weight_kg", type=float),
            distance_km=request.form.get("distance_km", type=float),
            notes=request.form.get("notes", "").strip() or None,
        )

        # Auto-calculate calories if not manually provided
        manual_calories = request.form.get("calories_burned", type=float)
        log.calories_burned = manual_calories or log.estimate_calories_burned(
            user_weight_kg=current_user.weight_kg or 70
        )

        db.session.add(log)
        db.session.commit()
        flash(f"{log.exercise_name} logged! Approx {log.calories_burned} kcal burned.", "success")
        return redirect(url_for("fitness.index"))

    return render_template(
        "fitness/log_exercise.html",
        categories=EXERCISE_CATEGORIES,
        intensities=INTENSITY_LEVELS,
        exercise_library=EXERCISE_LIBRARY,
    )


@fitness_bp.route("/delete/<int:log_id>", methods=["POST"])
@login_required
def delete_exercise(log_id):
    log = FitnessLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    name = log.exercise_name
    db.session.delete(log)
    db.session.commit()
    flash(f"{name} removed.", "info")
    return redirect(url_for("fitness.index"))


@fitness_bp.route("/water/log", methods=["POST"])
@login_required
def log_water():
    amount = request.form.get("amount_ml", type=float)
    if not amount or amount <= 0:
        flash("Invalid water amount.", "danger")
        return redirect(url_for("fitness.index"))

    log = WaterLog(
        user_id=current_user.id,
        log_date=date.fromisoformat(request.form.get("log_date", date.today().isoformat())),
        amount_ml=amount,
    )
    db.session.add(log)
    db.session.commit()
    flash(f"{int(amount)}ml of water logged!", "success")
    return redirect(url_for("fitness.index"))


@fitness_bp.route("/water/delete/<int:log_id>", methods=["POST"])
@login_required
def delete_water(log_id):
    log = WaterLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    flash("Water entry removed.", "info")
    return redirect(url_for("fitness.index"))


@fitness_bp.route("/api/exercises")
@login_required
def api_exercises():
    category = request.args.get("category", "")
    exercises = EXERCISE_LIBRARY.get(category, [e for lst in EXERCISE_LIBRARY.values() for e in lst])
    return jsonify(exercises)
