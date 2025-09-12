from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_required, current_user
from models import db, User
from config import config
import os

def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
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
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(budget_api_bp, url_prefix='/api/budget')
    app.register_blueprint(transactions_api_bp, url_prefix='/api/transactions')
    app.register_blueprint(milestones_api_bp, url_prefix='/api/milestones')
    app.register_blueprint(reports_api_bp, url_prefix='/api/reports')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('403.html'), 403
    
    # Template context processors
    @app.context_processor
    def inject_user():
        return {'current_user': current_user}
    
    @app.context_processor
    def utility_processor():
        from utils import format_currency, calculate_percentage
        return dict(format_currency=format_currency, calculate_percentage=calculate_percentage)
    
    # Create tables on first run
    with app.app_context():
        db.create_all()
    
    return app

# Create the Flask app
app = create_app()

# CLI commands for development
@app.cli.command()
def init_db():
    """Initialize the database."""
    from database.init_db import init_db
    init_db(app)
    print('Database initialized.')

@app.cli.command()
def init_enhanced():
    """Initialize database with sample data."""
    from database.enhanced_init_db import enhanced_init_db
    enhanced_init_db(app)
    print('Database initialized with sample data.')

@app.cli.command()
def seed():
    """Seed database with additional data."""
    from database.seed_data import seed_data
    with app.app_context():
        seed_data()
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
            print(f'Admin user "{username}" created successfully.')
        except Exception as e:
            print(f'Error creating admin user: {e}')
            db.session.rollback()

if __name__ == '__main__':
    # For development only
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))