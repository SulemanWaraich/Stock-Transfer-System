import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    APP_NAME = os.getenv("APP_NAME", "Stock Transfer Ultra")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-ultra")
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
    ENV = os.getenv("ENV", "dev")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

settings = Settings()
