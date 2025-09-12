#!/usr/bin/env python3
"""
Database migration script for the Personal Finance Tracker
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from flask import Flask
from config import config
from database.migrations import run_migrations, apply_pending_migrations, rollback_migration, backup_database
from database.init_db import init_db
from database.enhanced_init_db import enhanced_init_db
from database.seed_data import seed_data

def create_app():
    """Create Flask app for migration context"""
    app = Flask(__name__)
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[env])
    
    from models import db
    db.init_app(app)
    
    return app

def main():
    """Main migration script entry point"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1]
    app = create_app()
    
    if command == 'init':
        print("Initializing database...")
        with app.app_context():
            init_db(app)
    
    elif command == 'init-enhanced':
        print("Initializing database with sample data...")
        with app.app_context():
            enhanced_init_db(app)
    
    elif command == 'seed':
        print("Seeding database with additional data...")
        with app.app_context():
            seed_data()
    
    elif command == 'migrate':
        print("Running basic migrations...")
        with app.app_context():
            run_migrations(app)
    
    elif command == 'apply':
        print("Applying pending migrations...")
        with app.app_context():
            apply_pending_migrations(app)
    
    elif command == 'rollback':
        if len(sys.argv) < 3:
            print("Error: Migration version required for rollback")
            print("Usage: python migrate.py rollback <version>")
            return
        
        version = sys.argv[2]
        print(f"Rolling back migration {version}...")
        with app.app_context():
            rollback_migration(version, app)
    
    elif command == 'backup':
        backup_path = sys.argv[2] if len(sys.argv) > 2 else None
        print("Creating database backup...")
        from database.backup_restore import backup_database as create_backup
        with app.app_context():
            create_backup(backup_path)
    
    elif command == 'restore':
        if len(sys.argv) < 3:
            print("Error: Backup file path required for restore")
            print("Usage: python migrate.py restore <backup_file>")
            return
        
        backup_file = sys.argv[2]
        print(f"Restoring database from {backup_file}...")
        from database.backup_restore import restore_database
        restore_database(backup_file, app)
    
    elif command == 'reset':
        print("WARNING: This will delete all data and reinitialize the database!")
        confirm = input("Are you sure? Type 'yes' to confirm: ")
        
        if confirm.lower() == 'yes':
            with app.app_context():
                from models import db
                print("Dropping all tables...")
                db.drop_all()
                print("Recreating tables...")
                db.create_all()
                print("Database reset complete!")
        else:
            print("Reset cancelled.")
    
    elif command == 'status':
        print("Database status:")
        with app.app_context():
            from models import db, User, Transaction, BudgetCategory, Milestone
            
            try:
                users_count = User.query.count()
                transactions_count = Transaction.query.count()
                categories_count = BudgetCategory.query.count()
                milestones_count = Milestone.query.count()
                
                print(f"  Users: {users_count}")
                print(f"  Transactions: {transactions_count}")
                print(f"  Budget Categories: {categories_count}")
                print(f"  Milestones: {milestones_count}")
                print(f"  Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
                
            except Exception as e:
                print(f"  Error accessing database: {e}")
                print("  Database may not be initialized yet.")
    
    elif command == 'help':
        print_usage()
    
    else:
        print(f"Unknown command: {command}")
        print_usage()

def print_usage():
    """Print usage information"""
    print("Database Migration Script")
    print("=" * 50)
    print("Usage: python migrate.py <command> [options]")
    print()
    print("Commands:")
    print("  init              Initialize empty database")
    print("  init-enhanced     Initialize database with sample data")
    print("  seed              Add additional sample data to existing database")
    print("  migrate           Run basic database migrations")
    print("  apply             Apply all pending migrations")
    print("  rollback <ver>    Rollback to specific migration version")
    print("  backup [file]     Create database backup")
    print("  restore <file>    Restore database from backup")
    print("  reset             Reset database (WARNING: deletes all data)")
    print("  status            Show database status and statistics")
    print("  help              Show this help message")
    print()
    print("Examples:")
    print("  python migrate.py init")
    print("  python migrate.py init-enhanced")
    print("  python migrate.py backup my_backup.json")
    print("  python migrate.py restore my_backup.json")
    print("  python migrate.py rollback 001")

if __name__ == '__main__':
    main()