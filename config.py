import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:admin@localhost:5432/gym_icesi"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/gym_icesi")