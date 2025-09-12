from flask import Flask
from models import db, User, BudgetCategory, Transaction, Milestone, ExchangeRate, Report
from config import config
import os

def init_db(app=None):
    """Initialize the database with all tables"""
    if app is None:
        app = Flask(__name__)
        env = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[env])
        db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create default exchange rates
        create_default_exchange_rates()
        
        print("Database initialization completed!")

def create_default_exchange_rates():
    """Create default exchange rate entries"""
    default_rates = [
        {'base': 'USD', 'target': 'KES', 'rate': 150.0},
        {'base': 'KES', 'target': 'USD', 'rate': 0.0067},
        {'base': 'USD', 'target': 'EUR', 'rate': 0.85},
        {'base': 'EUR', 'target': 'USD', 'rate': 1.18},
        {'base': 'USD', 'target': 'GBP', 'rate': 0.73},
        {'base': 'GBP', 'target': 'USD', 'rate': 1.37},
    ]
    
    for rate_data in default_rates:
        existing = ExchangeRate.query.filter_by(
            base_currency=rate_data['base'],
            target_currency=rate_data['target']
        ).first()
        
        if not existing:
            rate = ExchangeRate(
                base_currency=rate_data['base'],
                target_currency=rate_data['target'],
                rate=rate_data['rate']
            )
            db.session.add(rate)
    
    db.session.commit()
    print("Default exchange rates created!")

def drop_all_tables(app=None):
    """Drop all database tables - use with caution!"""
    if app is None:
        app = Flask(__name__)
        env = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[env])
        db.init_app(app)
    
    with app.app_context():
        db.drop_all()
        print("All tables dropped!")

if __name__ == '__main__':
    init_db()