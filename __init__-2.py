from datetime import datetime, date
from flask_login import UserMixin
from app import db, login_manager, bcrypt


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Profile
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    activity_level = db.Column(db.String(20), default="moderate")  # sedentary, light, moderate, active, very_active

    # Relationships
    nutrition_logs = db.relationship("NutritionLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    fitness_logs = db.relationship("FitnessLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    water_logs = db.relationship("WaterLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    goals = db.relationship("Goal", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None

    @property
    def bmi_category(self):
        bmi = self.bmi
        if bmi is None:
            return "Unknown"
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Overweight"
        return "Obese"

    def calculate_tdee(self):
        """Total Daily Energy Expenditure using Mifflin-St Jeor equation."""
        if not all([self.age, self.gender, self.height_cm, self.weight_kg]):
            return None

        if self.gender == "male":
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5
        else:
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age - 161

        multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9,
        }
        return round(bmr * multipliers.get(self.activity_level, 1.55))

    def __repr__(self):
        return f"<User {self.username}>"


class NutritionLog(db.Model):
    __tablename__ = "nutrition_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    log_date = db.Column(db.Date, default=date.today, index=True)
    meal_type = db.Column(db.String(20), nullable=False)  # breakfast, lunch, dinner, snack

    # Food info
    food_name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    serving_size_g = db.Column(db.Float, default=100.0)
    quantity = db.Column(db.Float, default=1.0)

    # Macros (per serving)
    calories = db.Column(db.Float, default=0)
    protein_g = db.Column(db.Float, default=0)
    carbs_g = db.Column(db.Float, default=0)
    fat_g = db.Column(db.Float, default=0)
    fiber_g = db.Column(db.Float, default=0)
    sugar_g = db.Column(db.Float, default=0)
    sodium_mg = db.Column(db.Float, default=0)

    @property
    def total_calories(self):
        return round(self.calories * self.quantity, 1)

    @property
    def total_protein(self):
        return round(self.protein_g * self.quantity, 1)

    @property
    def total_carbs(self):
        return round(self.carbs_g * self.quantity, 1)

    @property
    def total_fat(self):
        return round(self.fat_g * self.quantity, 1)

    def __repr__(self):
        return f"<NutritionLog {self.food_name} - {self.log_date}>"


class FitnessLog(db.Model):
    __tablename__ = "fitness_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    log_date = db.Column(db.Date, default=date.today, index=True)

    # Exercise info
    exercise_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))  # cardio, strength, flexibility, sports, other
    duration_minutes = db.Column(db.Float, nullable=False)
    intensity = db.Column(db.String(20), default="moderate")  # low, moderate, high

    # Optional details
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight_kg = db.Column(db.Float)
    distance_km = db.Column(db.Float)
    calories_burned = db.Column(db.Float)
    notes = db.Column(db.Text)

    def estimate_calories_burned(self, user_weight_kg=70):
        """Estimate calories burned using MET values."""
        met_values = {
            "cardio": {"low": 4.0, "moderate": 7.0, "high": 11.0},
            "strength": {"low": 3.0, "moderate": 5.0, "high": 6.0},
            "flexibility": {"low": 2.5, "moderate": 3.0, "high": 4.0},
            "sports": {"low": 4.0, "moderate": 6.0, "high": 10.0},
            "other": {"low": 3.0, "moderate": 4.5, "high": 7.0},
        }
        category = self.category or "other"
        intensity = self.intensity or "moderate"
        met = met_values.get(category, met_values["other"]).get(intensity, 4.5)
        return round(met * user_weight_kg * (self.duration_minutes / 60), 1)

    def __repr__(self):
        return f"<FitnessLog {self.exercise_name} - {self.log_date}>"


class WaterLog(db.Model):
    __tablename__ = "water_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    log_date = db.Column(db.Date, default=date.today, index=True)
    amount_ml = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<WaterLog {self.amount_ml}ml - {self.log_date}>"


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    goal_type = db.Column(db.String(50), nullable=False)  # weight_loss, muscle_gain, maintain, endurance
    target_weight_kg = db.Column(db.Float)
    target_calories = db.Column(db.Integer)
    target_protein_g = db.Column(db.Integer)
    target_water_ml = db.Column(db.Integer, default=2500)
    target_exercise_minutes = db.Column(db.Integer, default=150)  # WHO recommendation
    target_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Goal {self.goal_type} for user {self.user_id}>"
