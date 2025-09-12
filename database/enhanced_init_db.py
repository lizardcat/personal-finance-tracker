from flask import Flask
from models import db, User, BudgetCategory, Transaction, Milestone, ExchangeRate
from config import config
from decimal import Decimal
import os

def enhanced_init_db(app=None):
    """Enhanced database initialization with sample data"""
    if app is None:
        app = Flask(__name__)
        env = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[env])
        db.init_app(app)
    
    with app.app_context():
        # Drop all tables first for clean start
        db.drop_all()
        
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create sample data
        create_sample_user()
        create_default_exchange_rates()
        create_sample_budget_categories()
        create_sample_transactions()
        create_sample_milestones()
        
        print("Enhanced database initialization completed!")

def create_sample_user():
    """Create a sample user for testing"""
    user = User(
        username='demo',
        email='demo@example.com',
        default_currency='USD',
        monthly_income=Decimal('5000.00')
    )
    user.set_password('password123')
    
    db.session.add(user)
    db.session.commit()
    print("Sample user created: demo/password123")

def create_default_exchange_rates():
    """Create realistic exchange rates"""
    rates = [
        {'base': 'USD', 'target': 'KES', 'rate': 147.50},
        {'base': 'KES', 'target': 'USD', 'rate': 0.00678},
        {'base': 'USD', 'target': 'EUR', 'rate': 0.849},
        {'base': 'EUR', 'target': 'USD', 'rate': 1.178},
        {'base': 'USD', 'target': 'GBP', 'rate': 0.732},
        {'base': 'GBP', 'target': 'USD', 'rate': 1.366},
        {'base': 'EUR', 'target': 'GBP', 'rate': 0.862},
        {'base': 'GBP', 'target': 'EUR', 'rate': 1.160},
        {'base': 'KES', 'target': 'EUR', 'rate': 0.00575},
        {'base': 'EUR', 'target': 'KES', 'rate': 173.85},
    ]
    
    for rate_data in rates:
        rate = ExchangeRate(
            base_currency=rate_data['base'],
            target_currency=rate_data['target'],
            rate=Decimal(str(rate_data['rate']))
        )
        db.session.add(rate)
    
    db.session.commit()
    print("Exchange rates created!")

def create_sample_budget_categories():
    """Create sample budget categories following YNAB principles"""
    user = User.query.filter_by(username='demo').first()
    
    categories = [
        # Essential expenses
        {'name': 'Rent/Mortgage', 'allocated': 1200.00, 'type': 'expense', 'color': '#dc3545'},
        {'name': 'Groceries', 'allocated': 400.00, 'type': 'expense', 'color': '#28a745'},
        {'name': 'Utilities', 'allocated': 150.00, 'type': 'expense', 'color': '#ffc107'},
        {'name': 'Transportation', 'allocated': 300.00, 'type': 'expense', 'color': '#17a2b8'},
        {'name': 'Phone', 'allocated': 50.00, 'type': 'expense', 'color': '#6f42c1'},
        
        # Lifestyle
        {'name': 'Dining Out', 'allocated': 200.00, 'type': 'expense', 'color': '#fd7e14'},
        {'name': 'Entertainment', 'allocated': 150.00, 'type': 'expense', 'color': '#e83e8c'},
        {'name': 'Shopping', 'allocated': 200.00, 'type': 'expense', 'color': '#20c997'},
        {'name': 'Health & Fitness', 'allocated': 100.00, 'type': 'expense', 'color': '#6c757d'},
        
        # Savings & Goals
        {'name': 'Emergency Fund', 'allocated': 500.00, 'type': 'saving', 'color': '#007bff'},
        {'name': 'Vacation Fund', 'allocated': 300.00, 'type': 'saving', 'color': '#198754'},
        {'name': 'Retirement', 'allocated': 600.00, 'type': 'saving', 'color': '#0d6efd'},
        
        # Income
        {'name': 'Salary', 'allocated': 5000.00, 'type': 'income', 'color': '#20c997'},
    ]
    
    for cat_data in categories:
        category = BudgetCategory(
            user_id=user.id,
            name=cat_data['name'],
            allocated_amount=Decimal(str(cat_data['allocated'])),
            available_amount=Decimal(str(cat_data['allocated'])),
            category_type=cat_data['type'],
            color=cat_data['color']
        )
        db.session.add(category)
    
    db.session.commit()
    print("Sample budget categories created!")

def create_sample_transactions():
    """Create sample transactions for the demo user"""
    user = User.query.filter_by(username='demo').first()
    
    # Get categories
    salary_cat = BudgetCategory.query.filter_by(user_id=user.id, name='Salary').first()
    rent_cat = BudgetCategory.query.filter_by(user_id=user.id, name='Rent/Mortgage').first()
    groceries_cat = BudgetCategory.query.filter_by(user_id=user.id, name='Groceries').first()
    dining_cat = BudgetCategory.query.filter_by(user_id=user.id, name='Dining Out').first()
    gas_cat = BudgetCategory.query.filter_by(user_id=user.id, name='Transportation').first()
    
    transactions = [
        # Income
        {'amount': 5000.00, 'description': 'Monthly Salary', 'type': 'income', 'category': salary_cat},
        
        # Regular expenses
        {'amount': 1200.00, 'description': 'Monthly Rent', 'type': 'expense', 'category': rent_cat, 'payee': 'Property Manager'},
        {'amount': 85.50, 'description': 'Weekly Groceries', 'type': 'expense', 'category': groceries_cat, 'payee': 'SuperMarket'},
        {'amount': 92.30, 'description': 'Weekly Groceries', 'type': 'expense', 'category': groceries_cat, 'payee': 'SuperMarket'},
        {'amount': 45.75, 'description': 'Coffee Shop', 'type': 'expense', 'category': dining_cat, 'payee': 'Local Cafe'},
        {'amount': 67.80, 'description': 'Gas Station', 'type': 'expense', 'category': gas_cat, 'payee': 'Shell'},
        {'amount': 32.50, 'description': 'Fast Food', 'type': 'expense', 'category': dining_cat, 'payee': 'Burger Place'},
        {'amount': 125.00, 'description': 'Internet Bill', 'type': 'expense', 'category': None, 'payee': 'Internet Provider'},
        {'amount': 78.25, 'description': 'Grocery Store', 'type': 'expense', 'category': groceries_cat, 'payee': 'Organic Foods'},
        {'amount': 156.90, 'description': 'Restaurant Dinner', 'type': 'expense', 'category': dining_cat, 'payee': 'Italian Restaurant'},
    ]
    
    for trans_data in transactions:
        transaction = Transaction(
            user_id=user.id,
            category_id=trans_data['category'].id if trans_data['category'] else None,
            amount=Decimal(str(trans_data['amount'])),
            description=trans_data['description'],
            transaction_type=trans_data['type'],
            payee=trans_data.get('payee', ''),
            account='checking'
        )
        db.session.add(transaction)
    
    db.session.commit()
    print("Sample transactions created!")

def create_sample_milestones():
    """Create sample milestones"""
    user = User.query.filter_by(username='demo').first()
    
    milestones = [
        {
            'name': 'Emergency Fund',
            'description': '6 months of expenses saved',
            'target_amount': 10000.00,
            'current_amount': 2500.00,
            'category': 'saving'
        },
        {
            'name': 'Vacation to Europe',
            'description': 'Save for 2-week European vacation',
            'target_amount': 4000.00,
            'current_amount': 850.00,
            'category': 'saving'
        },
        {
            'name': 'Pay off Credit Card',
            'description': 'Eliminate credit card debt',
            'target_amount': 2500.00,
            'current_amount': 1200.00,
            'category': 'debt'
        },
        {
            'name': 'Down Payment Fund',
            'description': 'Save for house down payment',
            'target_amount': 50000.00,
            'current_amount': 12000.00,
            'category': 'saving'
        }
    ]
    
    for milestone_data in milestones:
        milestone = Milestone(
            user_id=user.id,
            name=milestone_data['name'],
            description=milestone_data['description'],
            target_amount=Decimal(str(milestone_data['target_amount'])),
            current_amount=Decimal(str(milestone_data['current_amount'])),
            category=milestone_data['category']
        )
        db.session.add(milestone)
    
    db.session.commit()
    print("Sample milestones created!")

if __name__ == '__main__':
    enhanced_init_db()