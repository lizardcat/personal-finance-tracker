from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from decimal import Decimal
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User preferences
    default_currency = db.Column(db.String(3), default='KES')
    monthly_income = db.Column(db.Numeric(10, 2), default=0)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    budget_categories = db.relationship('BudgetCategory', backref='user', lazy=True, cascade='all, delete-orphan')
    milestones = db.relationship('Milestone', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class BudgetCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    allocated_amount = db.Column(db.Numeric(10, 2), default=0)
    available_amount = db.Column(db.Numeric(10, 2), default=0)
    category_type = db.Column(db.String(50), default='expense')  # expense, income, saving
    color = db.Column(db.String(7), default='#007bff')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='budget_category', lazy=True)
    
    def update_available_amount(self, start_date=None, end_date=None):
        """Update available amount based on allocated amount and transactions for a specific period

        Args:
            start_date: Start date for the budget period (defaults to first day of current month)
            end_date: End date for the budget period (defaults to last day of current month)
        """
        from datetime import date
        from calendar import monthrange

        # Default to current month if no dates provided
        if start_date is None:
            today = date.today()
            start_date = date(today.year, today.month, 1)

        if end_date is None:
            today = date.today()
            last_day = monthrange(today.year, today.month)[1]
            end_date = date(today.year, today.month, last_day)

        # Calculate total spent for this period only
        total_spent = sum(
            t.amount for t in self.transactions
            if t.transaction_type == 'expense'
            and t.transaction_date >= start_date
            and t.transaction_date <= end_date
        )
        self.available_amount = self.allocated_amount - total_spent
    
    def __repr__(self):
        return f'<BudgetCategory {self.name}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('budget_category.id'), nullable=True)
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='KES')
    exchange_rate_to_user_currency = db.Column(db.Numeric(12, 6), nullable=True)  # Historical exchange rate
    description = db.Column(db.String(255), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # income, expense, transfer
    transaction_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional fields
    payee = db.Column(db.String(100))
    account = db.Column(db.String(50), default='checking')
    tags = db.Column(db.String(255))  # Comma-separated tags
    recurring = db.Column(db.Boolean, default=False)
    recurring_period = db.Column(db.String(20))  # daily, weekly, monthly, yearly

    def get_amount_in_currency(self, target_currency):
        """Get transaction amount converted to target currency

        Uses historical exchange rate if available, otherwise uses current rate
        """
        if self.currency == target_currency:
            return self.amount

        # Use stored historical rate if available
        if self.exchange_rate_to_user_currency and target_currency == self.user.default_currency:
            return self.amount * self.exchange_rate_to_user_currency

        # Fall back to current exchange rate
        from services.exchange_rate_service import exchange_rate_service
        try:
            rate = exchange_rate_service.get_rate(self.currency, target_currency)
            return self.amount * rate
        except:
            return self.amount  # Return original if conversion fails

    def __repr__(self):
        return f'<Transaction {self.description}: {self.amount} {self.currency}>'

class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    target_amount = db.Column(db.Numeric(10, 2), nullable=False)
    current_amount = db.Column(db.Numeric(10, 2), default=0)
    target_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.Date)
    category = db.Column(db.String(50), default='saving')  # saving, debt, investment
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def progress_percentage(self):
        if self.target_amount <= 0:
            return 0
        return min((float(self.current_amount) / float(self.target_amount)) * 100, 100)
    
    @property
    def is_overdue(self):
        return self.target_date and self.target_date < date.today() and not self.completed
    
    def __repr__(self):
        return f'<Milestone {self.name}: {self.current_amount}/{self.target_amount}>'

class ExchangeRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    base_currency = db.Column(db.String(3), nullable=False)
    target_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Numeric(10, 6), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('base_currency', 'target_currency'),)
    
    def __repr__(self):
        return f'<ExchangeRate {self.base_currency}/{self.target_currency}: {self.rate}>'

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # monthly, yearly, category, custom
    parameters = db.Column(db.JSON)  # Store report parameters as JSON
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(255))  # Path to generated report file
    
    user = db.relationship('User', backref=db.backref('reports', lazy=True))

    def __repr__(self):
        return f'<Report {self.name} - {self.report_type}>'

class BudgetTemplate(db.Model):
    """Budget template for saving and reusing budget allocations"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    is_default = db.Column(db.Boolean, default=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('budget_templates', lazy=True, cascade='all, delete-orphan'))
    items = db.relationship('BudgetTemplateItem', backref='template', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BudgetTemplate {self.name}>'

    def apply_to_budget(self, clear_existing=False):
        """Apply this template to the user's current budget

        Args:
            clear_existing: If True, clear all existing budget categories before applying

        Returns:
            dict with statistics about the operation
        """
        from models import BudgetCategory

        stats = {
            'categories_created': 0,
            'categories_updated': 0,
            'categories_deleted': 0
        }

        if clear_existing:
            # Delete existing categories
            existing = BudgetCategory.query.filter_by(user_id=self.user_id).all()
            for cat in existing:
                db.session.delete(cat)
                stats['categories_deleted'] += 1

        # Create or update categories from template
        for item in self.items:
            existing_cat = BudgetCategory.query.filter_by(
                user_id=self.user_id,
                name=item.category_name,
                category_type=item.category_type
            ).first()

            if existing_cat:
                # Update existing category
                existing_cat.allocated_amount = item.allocated_amount
                existing_cat.available_amount = item.allocated_amount
                existing_cat.color = item.color
                stats['categories_updated'] += 1
            else:
                # Create new category
                new_cat = BudgetCategory(
                    user_id=self.user_id,
                    name=item.category_name,
                    allocated_amount=item.allocated_amount,
                    available_amount=item.allocated_amount,
                    category_type=item.category_type,
                    color=item.color
                )
                db.session.add(new_cat)
                stats['categories_created'] += 1

        # Update last used timestamp
        self.last_used = datetime.utcnow()

        return stats

class BudgetTemplateItem(db.Model):
    """Individual category items within a budget template"""
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('budget_template.id'), nullable=False)

    category_name = db.Column(db.String(100), nullable=False)
    category_type = db.Column(db.String(50), nullable=False)  # expense, income, saving
    allocated_amount = db.Column(db.Numeric(10, 2), nullable=False)
    color = db.Column(db.String(7), default='#007bff')

    def __repr__(self):
        return f'<BudgetTemplateItem {self.category_name}: {self.allocated_amount}>'

class AccountReconciliation(db.Model):
    """Account reconciliation for matching transactions with bank statements"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    account = db.Column(db.String(50), nullable=False)  # checking, savings, credit, cash
    statement_date = db.Column(db.Date, nullable=False)
    statement_balance = db.Column(db.Numeric(10, 2), nullable=False)
    book_balance = db.Column(db.Numeric(10, 2))  # Calculated from transactions
    difference = db.Column(db.Numeric(10, 2))  # statement_balance - book_balance
    reconciled = db.Column(db.Boolean, default=False)
    reconciled_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', backref=db.backref('reconciliations', lazy=True, cascade='all, delete-orphan'))
    items = db.relationship('ReconciliationItem', backref='reconciliation', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AccountReconciliation {self.account} - {self.statement_date}>'

    def calculate_balances(self):
        """Calculate book balance and difference from reconciliation items"""
        # Calculate book balance from cleared transactions
        cleared_total = sum(
            item.transaction.amount if item.transaction.transaction_type == 'income' else -item.transaction.amount
            for item in self.items if item.cleared
        )

        self.book_balance = Decimal(str(cleared_total))
        self.difference = self.statement_balance - self.book_balance

        # Auto-mark as reconciled if difference is zero
        if self.difference == 0 and not self.reconciled:
            self.reconciled = True
            self.reconciled_at = datetime.utcnow()

class ReconciliationItem(db.Model):
    """Individual transaction items within a reconciliation"""
    id = db.Column(db.Integer, primary_key=True)
    reconciliation_id = db.Column(db.Integer, db.ForeignKey('account_reconciliation.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)

    cleared = db.Column(db.Boolean, default=False)  # Marked as cleared/matched
    notes = db.Column(db.Text)

    # Relationships
    transaction = db.relationship('Transaction', backref='reconciliation_items')

    def __repr__(self):
        return f'<ReconciliationItem Transaction:{self.transaction_id} Cleared:{self.cleared}>'

class PasswordResetToken(db.Model):
    """Password reset tokens for user account recovery"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('reset_tokens', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<PasswordResetToken User:{self.user_id} Expires:{self.expires_at}>'

    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_for_user(user, expiration_hours=1):
        """Create a new password reset token for a user"""
        token = PasswordResetToken.generate_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=expiration_hours)
        )
        return reset_token

    def is_valid(self):
        """Check if token is still valid (not expired and not used)"""
        return not self.used and datetime.utcnow() < self.expires_at

    def mark_as_used(self):
        """Mark token as used"""
        self.used = True