import os
from datetime import date, datetime
from app import create_app, db
from app.models import User, NutritionLog, FitnessLog, WaterLog, Goal

app = create_app(os.environ.get("FLASK_ENV", "default"))


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "User": User,
        "NutritionLog": NutritionLog,
        "FitnessLog": FitnessLog,
        "WaterLog": WaterLog,
        "Goal": Goal,
    }


@app.context_processor
def inject_globals():
    return {"today": date.today(), "now": datetime.now()}


@app.cli.command("init-db")
def init_db():
    """Initialise database tables."""
    db.create_all()
    print("✅ Database tables created.")


@app.cli.command("seed")
def seed_db():
    """Seed database with a demo user."""
    if User.query.filter_by(username="demo").first():
        print("Demo user already exists.")
        return

    user = User(username="demo", email="demo@fittrack.app")
    user.set_password("demo1234")
    user.age = 28
    user.gender = "male"
    user.height_cm = 175.0
    user.weight_kg = 75.0
    user.activity_level = "moderate"
    db.session.add(user)
    db.session.flush()

    goal = Goal(
        user_id=user.id,
        goal_type="general_health",
        target_calories=2200,
        target_protein_g=120,
        target_water_ml=2500,
        target_exercise_minutes=150,
    )
    db.session.add(goal)
    db.session.commit()
    print("✅ Demo user created: username=demo, password=demo1234")


if __name__ == "__main__":
    app.run(debug=True)
