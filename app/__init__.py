"""
Reports App - Cloud Run Edition
Optimized for stateless, on-demand scaling on Google Cloud Run.
"""
import logging
import os
from flask import Flask
from flask_caching import Cache

# Initialize extensions
cache = Cache()


def create_app(config_name: str = None):
    """
    Application factory for Flask app.
    Optimized for Cloud Run with lazy initialization.
    """
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')

    from app.config import get_config
    app.config.from_object(get_config())

    # Setup logging
    setup_logging(app)

    # Initialize extensions
    cache.init_app(app)

    # Initialize database (lazy)
    init_database(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Add security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Health check endpoint for Cloud Run
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200

    # Readiness check
    @app.route('/ready')
    def readiness_check():
        try:
            from app.utils.database import db_manager
            with db_manager.engine.connect() as conn:
                conn.execute("SELECT 1")
            return {'status': 'ready'}, 200
        except Exception as e:
            app.logger.error(f"Readiness check failed: {e}")
            return {'status': 'not ready', 'error': str(e)}, 503

    return app


def setup_logging(app):
    """Configure logging for Cloud Run"""
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )


def init_database(app):
    """Initialize database connection (lazy) - only when first used"""
    from app.utils.database import db_manager
    from app.config import Config

    # Don't initialize at startup - let it initialize lazily on first use
    # This allows the app to start even if database is not available
    with app.app_context():
        app.logger.info("Database will be initialized on first use")
        # Store config for lazy initialization
        database_url = Config.get_database_url()
        # Only initialize if we have valid connection info
        if database_url and database_url != "postgresql://postgres:@localhost:5432/reports_db":
            try:
                db_manager.init_engine(database_url)
                app.logger.info("Database connection initialized")
            except Exception as e:
                app.logger.warning(f"Could not initialize database at startup: {e}. Will retry on first use.")
        else:
            app.logger.warning("Database URL not configured. App will work but database features will be unavailable.")


def register_blueprints(app):
    """Register Flask blueprints"""
    from app.blueprints.main import main_bp
    app.register_blueprint(main_bp)


def register_error_handlers(app):
    """Register error handlers"""

    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return {'error': 'Internal server error'}, 500
