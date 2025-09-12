from models import db, User, BudgetCategory, Transaction, Milestone, ExchangeRate
from decimal import Decimal
from datetime import date, datetime, timedelta
import random

def seed_data():
    """Seed the database with additional sample data"""
    print("Seeding database with sample data...")
    
    # Check if demo user exists
    demo_user = User.query.filter_by(username='demo').first()
    if not demo_user:
        print("Demo user not found. Please run enhanced_init_db first.")
        return
    
    # Add more transactions for better demo experience
    seed_additional_transactions(demo_user)
    
    # Update budget category available amounts based on transactions
    update_budget_amounts(demo_user)
    
    print("Database seeding completed!")

def seed_additional_transactions(user):
    """Add more varied transactions for demonstration"""
    categories = {cat.name: cat for cat in user.budget_categories}
    
    # Generate transactions for the last 3 months
    start_date = date.today() - timedelta(days=90)
    
    transaction_templates = [
        # Regular monthly expenses
        {'description': 'Electric Bill', 'amount_range': (80, 120), 'category': 'Utilities', 'frequency': 30},
        {'description': 'Gas Bill', 'amount_range': (30, 60), 'category': 'Utilities', 'frequency': 30},
        {'description': 'Water Bill', 'amount_range': (25, 45), 'category': 'Utilities', 'frequency': 30},
        
        # Weekly groceries with variation
        {'description': 'Grocery Shopping', 'amount_range': (70, 130), 'category': 'Groceries', 'frequency': 7},
        {'description': 'Farmers Market', 'amount_range': (25, 50), 'category': 'Groceries', 'frequency': 14},
        
        # Transportation
        {'description': 'Gas Station Fill-up', 'amount_range': (40, 80), 'category': 'Transportation', 'frequency': 10},
        {'description': 'Car Maintenance', 'amount_range': (150, 400), 'category': 'Transportation', 'frequency': 60},
        {'description': 'Parking', 'amount_range': (5, 25), 'category': 'Transportation', 'frequency': 5},
        
        # Dining and entertainment
        {'description': 'Restaurant', 'amount_range': (35, 85), 'category': 'Dining Out', 'frequency': 8},
        {'description': 'Coffee Shop', 'amount_range': (4, 12), 'category': 'Dining Out', 'frequency': 3},
        {'description': 'Movie Theater', 'amount_range': (15, 30), 'category': 'Entertainment', 'frequency': 14},
        {'description': 'Streaming Service', 'amount_range': (9, 20), 'category': 'Entertainment', 'frequency': 30},
        
        # Health and fitness
        {'description': 'Gym Membership', 'amount_range': (30, 80), 'category': 'Health & Fitness', 'frequency': 30},
        {'description': 'Doctor Visit', 'amount_range': (100, 250), 'category': 'Health & Fitness', 'frequency': 45},
        
        # Shopping
        {'description': 'Online Purchase', 'amount_range': (25, 150), 'category': 'Shopping', 'frequency': 12},
        {'description': 'Clothing Store', 'amount_range': (40, 200), 'category': 'Shopping', 'frequency': 21},
        
        # Savings transfers
        {'description': 'Transfer to Emergency Fund', 'amount_range': (200, 500), 'category': 'Emergency Fund', 'frequency': 30},
        {'description': 'Vacation Savings', 'amount_range': (100, 300), 'category': 'Vacation Fund', 'frequency': 30},
    ]
    
    # Generate transactions
    current_date = start_date
    while current_date <= date.today():
        for template in transaction_templates:
            # Check if it's time for this transaction based on frequency
            days_since_start = (current_date - start_date).days
            if days_since_start % template['frequency'] == 0:
                
                category_name = template['category']
                if category_name in categories:
                    category = categories[category_name]
                    
                    # Generate random amount within range
                    min_amt, max_amt = template['amount_range']
                    amount = round(random.uniform(min_amt, max_amt), 2)
                    
                    # Determine transaction type based on category
                    trans_type = 'expense'
                    if category.category_type == 'income':
                        trans_type = 'income'
                    elif category.category_type == 'saving':
                        trans_type = 'transfer'
                    
                    transaction = Transaction(
                        user_id=user.id,
                        category_id=category.id,
                        amount=Decimal(str(amount)),
                        description=template['description'],
                        transaction_type=trans_type,
                        transaction_date=current_date
                    )
                    db.session.add(transaction)
        
        current_date += timedelta(days=1)
    
    # Add some income transactions
    salary_category = categories.get('Salary')
    if salary_category:
        # Add monthly salary for last 3 months
        for month_offset in [2, 1, 0]:  # 2 months ago, 1 month ago, this month
            salary_date = date.today().replace(day=1) - timedelta(days=30 * month_offset)
            salary = Transaction(
                user_id=user.id,
                category_id=salary_category.id,
                amount=Decimal('5000.00'),
                description='Monthly Salary',
                transaction_type='income',
                transaction_date=salary_date
            )
            db.session.add(salary)
    
    db.session.commit()
    print(f"Added additional transactions for demonstration")

def update_budget_amounts(user):
    """Update budget category available amounts based on actual transactions"""
    for category in user.budget_categories:
        if category.category_type == 'expense':
            # Calculate total spent in this category
            total_spent = sum(
                t.amount for t in category.transactions 
                if t.transaction_type == 'expense'
            )
            category.available_amount = category.allocated_amount - total_spent
        
        elif category.category_type == 'saving':
            # For savings categories, available amount is what's been saved
            total_saved = sum(
                t.amount for t in category.transactions 
                if t.transaction_type == 'transfer'
            )
            category.available_amount = total_saved
        
        elif category.category_type == 'income':
            # For income categories, show total received
            total_income = sum(
                t.amount for t in category.transactions 
                if t.transaction_type == 'income'
            )
            category.available_amount = total_income
    
    db.session.commit()
    print("Updated budget category amounts based on transactions")

if __name__ == '__main__':
    seed_data()