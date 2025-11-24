from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from flask_talisman import Talisman
from models import db, User
from config import config
from logging_config import setup_logging
from limiter import limiter
import os

# Initialize Flask-Mail
mail = Mail()

def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    # Setup logging
    setup_logging(app)

    # Setup rate limiting
    limiter.init_app(app)

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes import main_bp
    from api.auth import auth_bp
    from api.budget import budget_api_bp
    from api.transactions import transactions_api_bp
    from api.milestones import milestones_api_bp
    from api.reports import reports_api_bp
    from api.reconciliation import reconciliation_api_bp
    from api.exchange_rates import exchange_rates_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(budget_api_bp, url_prefix='/api/budget')
    app.register_blueprint(transactions_api_bp, url_prefix='/api/transactions')
    app.register_blueprint(milestones_api_bp, url_prefix='/api/milestones')
    app.register_blueprint(reports_api_bp, url_prefix='/api/reports')
    app.register_blueprint(reconciliation_api_bp, url_prefix='/api/reconciliation')
    app.register_blueprint(exchange_rates_bp)

    # Enable HTTPS enforcement in production
    if config_name == 'production':
        Talisman(app,
                force_https=True,
                strict_transport_security=True,
                strict_transport_security_max_age=31536000,
                content_security_policy={
                    'default-src': "'self'",
                    'script-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com'],
                    'style-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com'],
                    'img-src': ["'self'", 'data:', 'https:'],
                    'font-src': ["'self'", 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com']
                })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f'404 error: {request.url} from IP {request.remote_addr}')
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500 error: {str(error)}', exc_info=True)
        db.session.rollback()
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.warning(f'403 error: User {current_user.username if current_user.is_authenticated else "Anonymous"} attempted to access {request.url} from IP {request.remote_addr}')
        return render_template('403.html'), 403

    @app.errorhandler(429)
    def ratelimit_handler(error):
        """Handle rate limit exceeded errors"""
        app.logger.warning(f'Rate limit exceeded: {request.url} from IP {request.remote_addr}')
        if request.is_json:
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429
        return render_template('429.html'), 429
    
    # Template context processors
    @app.context_processor
    def inject_user():
        return {'current_user': current_user}
    
    @app.context_processor
    def utility_processor():
        from utils import format_currency, calculate_percentage
        return dict(format_currency=format_currency, calculate_percentage=calculate_percentage)

    # Add security headers
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Only set HSTS if in production (with HTTPS)
        if config_name == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Create tables on first run (development only)
    # In production, use migrations or init_db CLI command instead
    if config_name == 'development':
        with app.app_context():
            try:
                db.create_all()
            except Exception as e:
                app.logger.warning(f'Could not create tables: {e}')

    return app

# Create the Flask app
app = create_app()

# CLI commands for development
@app.cli.command()
def init_db():
    """Initialize the database."""
    from database.init_db import init_db
    init_db(app)
    app.logger.info('Database initialized via CLI command')
    print('Database initialized.')

@app.cli.command()
def init_enhanced():
    """Initialize database with sample data."""
    from database.enhanced_init_db import enhanced_init_db
    enhanced_init_db(app)
    app.logger.info('Database initialized with sample data via CLI command')
    print('Database initialized with sample data.')

@app.cli.command()
def seed():
    """Seed database with additional data."""
    from database.seed_data import seed_data
    with app.app_context():
        seed_data()
    app.logger.info('Database seeded via CLI command')
    print('Database seeded.')

@app.cli.command()
def create_admin():
    """Create an admin user."""
    username = input('Admin username: ')
    email = input('Admin email: ')
    password = input('Admin password: ')

    with app.app_context():
        admin = User(username=username, email=email)
        admin.set_password(password)

        try:
            db.session.add(admin)
            db.session.commit()
            app.logger.info(f'Admin user "{username}" created via CLI command')
            print(f'Admin user "{username}" created successfully.')
        except Exception as e:
            app.logger.error(f'Error creating admin user: {e}')
            print(f'Error creating admin user: {e}')
            db.session.rollback()

if __name__ == '__main__':
    # For development only
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))