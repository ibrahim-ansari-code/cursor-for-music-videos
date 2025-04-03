import os
import logging
from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import or_

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the base model class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the base model class
db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)

# Setup a secret key, required by sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

@app.route('/')
def index():
    """Home endpoint for the API"""
    return jsonify({
        "status": "success",
        "message": "Property Management API is running",
        "version": "1.0.0"
    })

@app.route('/api/health')
def health():
    """Health check endpoint for the API"""
    # Check database connection
    try:
        db.session.execute(db.select(db.text("1"))).scalar()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"
    
    return jsonify({
        "status": "ok",
        "database": db_status
    })

# Initialize database and create tables
with app.app_context():
    # Import models here to prevent circular imports
    import models
    
    try:
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

# Register blueprints for API routes
from routes.auth import auth_bp
from routes.properties import properties_bp
from routes.leases import leases_bp
from routes.accounting import accounting_bp

# Register blueprints with URL prefixes
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(properties_bp, url_prefix='/api/properties')
app.register_blueprint(leases_bp, url_prefix='/api/leases')
app.register_blueprint(accounting_bp, url_prefix='/api/accounting')

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'message': 'Bad request', 'error': str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Resource not found', 'error': str(error)}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {str(error)}")
    return jsonify({'message': 'Internal server error', 'error': str(error)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)