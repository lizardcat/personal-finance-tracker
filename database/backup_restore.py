import os
import sqlite3
import json
from datetime import datetime
from models import db, User, BudgetCategory, Transaction, Milestone, ExchangeRate, Report
from flask import Flask
from config import config

def backup_database(backup_path=None):
    """Create a comprehensive backup of the database"""
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_{timestamp}.json"
    
    # Ensure backup directory exists
    backup_dir = os.path.dirname(backup_path) if os.path.dirname(backup_path) else 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_data = {
        'backup_timestamp': datetime.now().isoformat(),
        'users': [],
        'budget_categories': [],
        'transactions': [],
        'milestones': [],
        'exchange_rates': [],
        'reports': []
    }
    
    try:
        # Backup users
        users = User.query.all()
        for user in users:
            backup_data['users'].append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'password_hash': user.password_hash,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'default_currency': user.default_currency,
                'monthly_income': float(user.monthly_income) if user.monthly_income else 0
            })
        
        # Backup budget categories
        categories = BudgetCategory.query.all()
        for category in categories:
            backup_data['budget_categories'].append({
                'id': category.id,
                'user_id': category.user_id,
                'name': category.name,
                'allocated_amount': float(category.allocated_amount) if category.allocated_amount else 0,
                'available_amount': float(category.available_amount) if category.available_amount else 0,
                'category_type': category.category_type,
                'color': category.color,
                'created_at': category.created_at.isoformat() if category.created_at else None
            })
        
        # Backup transactions
        transactions = Transaction.query.all()
        for transaction in transactions:
            backup_data['transactions'].append({
                'id': transaction.id,
                'user_id': transaction.user_id,
                'category_id': transaction.category_id,
                'amount': float(transaction.amount) if transaction.amount else 0,
                'currency': transaction.currency,
                'description': transaction.description,
                'transaction_type': transaction.transaction_type,
                'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
                'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
                'payee': transaction.payee,
                'account': transaction.account,
                'tags': transaction.tags,
                'recurring': transaction.recurring,
                'recurring_period': transaction.recurring_period
            })
        
        # Backup milestones
        milestones = Milestone.query.all()
        for milestone in milestones:
            backup_data['milestones'].append({
                'id': milestone.id,
                'user_id': milestone.user_id,
                'name': milestone.name,
                'description': milestone.description,
                'target_amount': float(milestone.target_amount) if milestone.target_amount else 0,
                'current_amount': float(milestone.current_amount) if milestone.current_amount else 0,
                'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
                'completed': milestone.completed,
                'completed_date': milestone.completed_date.isoformat() if milestone.completed_date else None,
                'category': milestone.category,
                'created_at': milestone.created_at.isoformat() if milestone.created_at else None
            })
        
        # Backup exchange rates
        rates = ExchangeRate.query.all()
        for rate in rates:
            backup_data['exchange_rates'].append({
                'id': rate.id,
                'base_currency': rate.base_currency,
                'target_currency': rate.target_currency,
                'rate': float(rate.rate) if rate.rate else 0,
                'updated_at': rate.updated_at.isoformat() if rate.updated_at else None
            })
        
        # Backup reports
        reports = Report.query.all()
        for report in reports:
            backup_data['reports'].append({
                'id': report.id,
                'user_id': report.user_id,
                'name': report.name,
                'report_type': report.report_type,
                'parameters': report.parameters,
                'generated_at': report.generated_at.isoformat() if report.generated_at else None,
                'file_path': report.file_path
            })
        
        # Write backup to file
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        print(f"Database backup created successfully: {backup_path}")
        print(f"Backed up {len(backup_data['users'])} users, {len(backup_data['transactions'])} transactions")
        
        return backup_path
    
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def restore_database(backup_path, app=None):
    """Restore database from backup file"""
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return False
    
    if app is None:
        app = Flask(__name__)
        env = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[env])
        db.init_app(app)
    
    try:
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        with app.app_context():
            # Clear existing data
            print("Clearing existing database...")
            db.drop_all()
            db.create_all()
            
            # Restore users first (since other tables depend on them)
            print("Restoring users...")
            for user_data in backup_data['users']:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    default_currency=user_data.get('default_currency', 'USD'),
                    monthly_income=user_data.get('monthly_income', 0)
                )
                if user_data.get('created_at'):
                    user.created_at = datetime.fromisoformat(user_data['created_at'])
                db.session.add(user)
            
            db.session.commit()
            
            # Restore exchange rates
            print("Restoring exchange rates...")
            for rate_data in backup_data['exchange_rates']:
                rate = ExchangeRate(
                    base_currency=rate_data['base_currency'],
                    target_currency=rate_data['target_currency'],
                    rate=rate_data['rate']
                )
                if rate_data.get('updated_at'):
                    rate.updated_at = datetime.fromisoformat(rate_data['updated_at'])
                db.session.add(rate)
            
            db.session.commit()
            
            # Restore budget categories
            print("Restoring budget categories...")
            for cat_data in backup_data['budget_categories']:
                category = BudgetCategory(
                    user_id=cat_data['user_id'],
                    name=cat_data['name'],
                    allocated_amount=cat_data.get('allocated_amount', 0),
                    available_amount=cat_data.get('available_amount', 0),
                    category_type=cat_data.get('category_type', 'expense'),
                    color=cat_data.get('color', '#007bff')
                )
                if cat_data.get('created_at'):
                    category.created_at = datetime.fromisoformat(cat_data['created_at'])
                db.session.add(category)
            
            db.session.commit()
            
            # Restore transactions
            print("Restoring transactions...")
            for trans_data in backup_data['transactions']:
                transaction = Transaction(
                    user_id=trans_data['user_id'],
                    category_id=trans_data.get('category_id'),
                    amount=trans_data['amount'],
                    currency=trans_data.get('currency', 'USD'),
                    description=trans_data['description'],
                    transaction_type=trans_data['transaction_type'],
                    payee=trans_data.get('payee'),
                    account=trans_data.get('account', 'checking'),
                    tags=trans_data.get('tags'),
                    recurring=trans_data.get('recurring', False),
                    recurring_period=trans_data.get('recurring_period')
                )
                if trans_data.get('transaction_date'):
                    transaction.transaction_date = datetime.fromisoformat(trans_data['transaction_date']).date()
                if trans_data.get('created_at'):
                    transaction.created_at = datetime.fromisoformat(trans_data['created_at'])
                db.session.add(transaction)
            
            db.session.commit()
            
            # Restore milestones
            print("Restoring milestones...")
            for milestone_data in backup_data['milestones']:
                milestone = Milestone(
                    user_id=milestone_data['user_id'],
                    name=milestone_data['name'],
                    description=milestone_data.get('description'),
                    target_amount=milestone_data['target_amount'],
                    current_amount=milestone_data.get('current_amount', 0),
                    completed=milestone_data.get('completed', False),
                    category=milestone_data.get('category', 'saving')
                )
                if milestone_data.get('target_date'):
                    milestone.target_date = datetime.fromisoformat(milestone_data['target_date']).date()
                if milestone_data.get('completed_date'):
                    milestone.completed_date = datetime.fromisoformat(milestone_data['completed_date']).date()
                if milestone_data.get('created_at'):
                    milestone.created_at = datetime.fromisoformat(milestone_data['created_at'])
                db.session.add(milestone)
            
            db.session.commit()
            
            # Restore reports
            print("Restoring reports...")
            for report_data in backup_data['reports']:
                report = Report(
                    user_id=report_data['user_id'],
                    name=report_data['name'],
                    report_type=report_data['report_type'],
                    parameters=report_data.get('parameters'),
                    file_path=report_data.get('file_path')
                )
                if report_data.get('generated_at'):
                    report.generated_at = datetime.fromisoformat(report_data['generated_at'])
                db.session.add(report)
            
            db.session.commit()
            
            print(f"Database restored successfully from {backup_path}")
            print(f"Restored {len(backup_data['users'])} users, {len(backup_data['transactions'])} transactions")
            
            return True
    
    except Exception as e:
        print(f"Restore failed: {e}")
        return False

def create_sqlite_backup(db_path, backup_path=None):
    """Create a direct SQLite backup (for SQLite databases only)"""
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"sqlite_backup_{timestamp}.db"
    
    try:
        # Create backup directory
        backup_dir = os.path.dirname(backup_path) if os.path.dirname(backup_path) else 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy SQLite database file
        import shutil
        shutil.copy2(db_path, backup_path)
        
        print(f"SQLite backup created: {backup_path}")
        return backup_path
    
    except Exception as e:
        print(f"SQLite backup failed: {e}")
        return None

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'backup':
            backup_path = sys.argv[2] if len(sys.argv) > 2 else None
            backup_database(backup_path)
        
        elif command == 'restore' and len(sys.argv) > 2:
            backup_path = sys.argv[2]
            restore_database(backup_path)
        
        elif command == 'sqlite-backup':
            db_path = sys.argv[2] if len(sys.argv) > 2 else 'finance_tracker.db'
            backup_path = sys.argv[3] if len(sys.argv) > 3 else None
            create_sqlite_backup(db_path, backup_path)
        
        else:
            print("Usage: python backup_restore.py [backup|restore <file>|sqlite-backup <db_path> [backup_path]]")
    else:
        backup_database()