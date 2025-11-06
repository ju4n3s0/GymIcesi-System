from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient
from config import Config

db = SQLAlchemy()
mongo_client = MongoClient(Config.MONGO_URI)
mongo_db = mongo_client["gym_icesi"]

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    JWTManager(app)
    db.init_app(app)

    # Importar y registrar rutas
    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)