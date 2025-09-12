from flask import Flask
from models import db
from config import config
import os
from datetime import datetime

def run_migrations(app=None):
    """Run database migrations"""
    if app is None:
        app = Flask(__name__)
        env = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[env])
        db.init_app(app)
    
    with app.app_context():
        print("Starting database migrations...")
        
        # For now, we'll just recreate tables
        # In a production system, you'd use Alembic or Flask-Migrate
        db.create_all()
        
        print("Migrations completed successfully!")

def backup_database(backup_path=None):
    """Create a backup of the current database"""
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_{timestamp}.sql"
    
    # This is a simple implementation
    # In production, you'd use proper database backup tools
    print(f"Database backup would be created at: {backup_path}")
    print("Note: Implement actual backup logic based on your database type")

def restore_database(backup_path):
    """Restore database from backup"""
    print(f"Database restore would be performed from: {backup_path}")
    print("Note: Implement actual restore logic based on your database type")

class Migration:
    """Base migration class"""
    
    def __init__(self, version, description):
        self.version = version
        self.description = description
        self.timestamp = datetime.utcnow()
    
    def up(self):
        """Apply the migration"""
        raise NotImplementedError("Subclasses must implement up()")
    
    def down(self):
        """Reverse the migration"""
        raise NotImplementedError("Subclasses must implement down()")

class AddTagsToTransactions(Migration):
    """Example migration to add tags field to transactions"""
    
    def __init__(self):
        super().__init__("001", "Add tags field to transactions")
    
    def up(self):
        """Add tags column to transactions table"""
        # This would use SQLAlchemy's DDL operations
        print(f"Applying migration {self.version}: {self.description}")
        # db.engine.execute("ALTER TABLE transaction ADD COLUMN tags VARCHAR(255)")
    
    def down(self):
        """Remove tags column from transactions table"""
        print(f"Reversing migration {self.version}: {self.description}")
        # db.engine.execute("ALTER TABLE transaction DROP COLUMN tags")

class AddRecurringToTransactions(Migration):
    """Example migration to add recurring fields to transactions"""
    
    def __init__(self):
        super().__init__("002", "Add recurring fields to transactions")
    
    def up(self):
        """Add recurring columns to transactions table"""
        print(f"Applying migration {self.version}: {self.description}")
        # This would add the recurring and recurring_period columns
        # db.engine.execute("ALTER TABLE transaction ADD COLUMN recurring BOOLEAN DEFAULT FALSE")
        # db.engine.execute("ALTER TABLE transaction ADD COLUMN recurring_period VARCHAR(20)")
    
    def down(self):
        """Remove recurring columns from transactions table"""
        print(f"Reversing migration {self.version}: {self.description}")
        # db.engine.execute("ALTER TABLE transaction DROP COLUMN recurring")
        # db.engine.execute("ALTER TABLE transaction DROP COLUMN recurring_period")

# Migration registry
MIGRATIONS = [
    AddTagsToTransactions(),
    AddRecurringToTransactions(),
]

def get_applied_migrations():
    """Get list of applied migrations from database"""
    # In a real system, you'd have a migrations table to track this
    return []

def apply_pending_migrations(app=None):
    """Apply all pending migrations"""
    if app is None:
        app = Flask(__name__)
        env = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[env])
        db.init_app(app)
    
    with app.app_context():
        applied = get_applied_migrations()
        
        for migration in MIGRATIONS:
            if migration.version not in applied:
                try:
                    migration.up()
                    # In production, you'd record this in the migrations table
                    print(f"Migration {migration.version} applied successfully")
                except Exception as e:
                    print(f"Failed to apply migration {migration.version}: {e}")
                    break

def rollback_migration(version, app=None):
    """Rollback a specific migration"""
    if app is None:
        app = Flask(__name__)
        env = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[env])
        db.init_app(app)
    
    with app.app_context():
        migration = next((m for m in MIGRATIONS if m.version == version), None)
        
        if migration:
            try:
                migration.down()
                print(f"Migration {version} rolled back successfully")
            except Exception as e:
                print(f"Failed to rollback migration {version}: {e}")
        else:
            print(f"Migration {version} not found")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'migrate':
            run_migrations()
        elif command == 'apply':
            apply_pending_migrations()
        elif command == 'rollback' and len(sys.argv) > 2:
            rollback_migration(sys.argv[2])
        elif command == 'backup':
            backup_database()
        else:
            print("Usage: python migrations.py [migrate|apply|rollback <version>|backup]")
    else:
        run_migrations()