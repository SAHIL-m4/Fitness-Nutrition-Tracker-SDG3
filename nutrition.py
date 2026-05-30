import requests
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import NutritionLog

nutrition_bp = Blueprint("nutrition", __name__)

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def search_openfoodfacts(query, page=1, page_size=10):
    """Search Open Food Facts public API — no API key required."""
    try:
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page": page,
            "page_size": page_size,
            "fields": "product_name,brands,nutriments,serving_size,image_small_url",
        }
        resp = requests.get(
            "https://world.openfoodfacts.org/cgi/search.pl",
            params=params,
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        products = []
        for p in data.get("products", []):
            n = p.get("nutriments", {})
            if not p.get("product_name"):
                continue
            products.append({
                "name": p.get("product_name", "Unknown"),
                "brand": p.get("brands", ""),
                "serving_size": p.get("serving_size", "100g"),
                "calories": round(n.get("energy-kcal_100g", 0), 1),
                "protein": round(n.get("proteins_100g", 0), 1),
                "carbs": round(n.get("carbohydrates_100g", 0), 1),
                "fat": round(n.get("fat_100g", 0), 1),
                "fiber": round(n.get("fiber_100g", 0), 1),
                "sugar": round(n.get("sugars_100g", 0), 1),
                "sodium": round(n.get("sodium_100g", 0) * 1000, 1),  # convert to mg
                "image": p.get("image_small_url", ""),
            })
        return products
    except Exception:
        return []


@nutrition_bp.route("/")
@login_required
def index():
    selected_date = request.args.get("date", date.today().isoformat())
    try:
        log_date = date.fromisoformat(selected_date)
    except ValueError:
        log_date = date.today()

    logs_by_meal = {}
    for meal in MEAL_TYPES:
        logs_by_meal[meal] = NutritionLog.query.filter_by(
            user_id=current_user.id,
            log_date=log_date,
            meal_type=meal
        ).all()

    daily_totals = db.session.query(
        func.sum(NutritionLog.calories * NutritionLog.quantity).label("calories"),
        func.sum(NutritionLog.protein_g * NutritionLog.quantity).label("protein"),
        func.sum(NutritionLog.carbs_g * NutritionLog.quantity).label("carbs"),
        func.sum(NutritionLog.fat_g * NutritionLog.quantity).label("fat"),
        func.sum(NutritionLog.fiber_g * NutritionLog.quantity).label("fiber"),
    ).filter(
        NutritionLog.user_id == current_user.id,
        NutritionLog.log_date == log_date
    ).first()

    return render_template(
        "nutrition/index.html",
        logs_by_meal=logs_by_meal,
        meal_types=MEAL_TYPES,
        log_date=log_date,
        totals=daily_totals,
    )


@nutrition_bp.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip()
    results = []
    if query:
        results = search_openfoodfacts(query)
    return render_template("nutrition/search.html", query=query, results=results)


@nutrition_bp.route("/api/search")
@login_required
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    results = search_openfoodfacts(query)
    return jsonify(results)


@nutrition_bp.route("/log", methods=["GET", "POST"])
@login_required
def log_food():
    if request.method == "POST":
        try:
            log = NutritionLog(
                user_id=current_user.id,
                log_date=date.fromisoformat(request.form.get("log_date", date.today().isoformat())),
                meal_type=request.form.get("meal_type", "lunch"),
                food_name=request.form.get("food_name", "").strip(),
                brand=request.form.get("brand", "").strip(),
                serving_size_g=float(request.form.get("serving_size_g") or 100),
                quantity=float(request.form.get("quantity") or 1),
                calories=float(request.form.get("calories") or 0),
                protein_g=float(request.form.get("protein_g") or 0),
                carbs_g=float(request.form.get("carbs_g") or 0),
                fat_g=float(request.form.get("fat_g") or 0),
                fiber_g=float(request.form.get("fiber_g") or 0),
                sugar_g=float(request.form.get("sugar_g") or 0),
                sodium_mg=float(request.form.get("sodium_mg") or 0),
            )
            if not log.food_name:
                flash("Food name is required.", "danger")
                return redirect(request.referrer or url_for("nutrition.index"))

            db.session.add(log)
            db.session.commit()
            flash(f"{log.food_name} logged successfully!", "success")
        except (ValueError, TypeError) as e:
            flash("Invalid data submitted. Please check your input.", "danger")

        return redirect(url_for("nutrition.index"))

    meal_type = request.args.get("meal_type", "lunch")
    return render_template("nutrition/log_food.html", meal_types=MEAL_TYPES, selected_meal=meal_type)


@nutrition_bp.route("/delete/<int:log_id>", methods=["POST"])
@login_required
def delete_log(log_id):
    log = NutritionLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    flash(f"{log.food_name} removed.", "info")
    return redirect(url_for("nutrition.index"))


@nutrition_bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    logs = NutritionLog.query.filter_by(user_id=current_user.id)\
        .order_by(NutritionLog.log_date.desc(), NutritionLog.logged_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template("nutrition/history.html", logs=logs)
