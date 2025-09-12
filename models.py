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