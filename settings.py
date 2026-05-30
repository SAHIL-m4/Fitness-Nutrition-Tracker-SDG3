import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_ENABLED = True

    # Nutrition API (Open Food Facts - free, no key needed)
    OPENFOODFACTS_API = "https://world.openfoodfacts.org/cgi/search.pl"

    # Pagination
    ITEMS_PER_PAGE = 10

    # Daily recommended values (FDA)
    DAILY_CALORIES = 2000
    DAILY_PROTEIN_G = 50
    DAILY_CARBS_G = 275
    DAILY_FAT_G = 78
    DAILY_FIBER_G = 28
    DAILY_WATER_ML = 2500


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'fittrack_dev.db')}"
    )


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SECRET_KEY = os.environ.get("SECRET_KEY")

    @classmethod
    def init_app(cls, app):
        assert cls.SECRET_KEY, "SECRET_KEY environment variable must be set in production"
        assert cls.SQLALCHEMY_DATABASE_URI, "DATABASE_URL environment variable must be set in production"


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
