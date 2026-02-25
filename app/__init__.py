from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os


def create_app():
    load_dotenv()

    app = Flask(__name__)

    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # Configuration
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")

    # Initialize extensions
    from app.extensions import mongo
    mongo.init_app(app)

    # Register Blueprints
    from app.routes.user_routes import user_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.documents_routes import documents_bp
    
    app.register_blueprint(user_bp, url_prefix="/users")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(documents_bp, url_prefix="/documents")

    @app.route('/')
    def home():
        return "server is running"

    return app
