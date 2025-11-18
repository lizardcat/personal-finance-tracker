from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from decimal import Decimal

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User preferences
    default_currency = db.Column(db.String(3), default='USD')
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
    
    def update_available_amount(self):
        """Update available amount based on allocated amount and transactions"""
        total_spent = sum(t.amount for t in self.transactions if t.transaction_type == 'expense')
        self.available_amount = self.allocated_amount - total_spent
    
    def __repr__(self):
        return f'<BudgetCategory {self.name}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('budget_category.id'), nullable=True)
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
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