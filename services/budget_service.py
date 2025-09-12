from models import db, BudgetCategory, Transaction, User
from decimal import Decimal
from datetime import date, datetime, timedelta
from sqlalchemy import func
from utils import get_month_range, get_budget_health_status
import logging

logger = logging.getLogger(__name__)

class BudgetService:
    """Service for budget-related operations"""
    
    @staticmethod
    def create_default_categories(user_id):
        """Create default budget categories for a new user"""
        default_categories = [
            # Essential expenses
            {'name': 'Housing', 'type': 'expense', 'allocated': 0, 'color': '#dc3545'},
            {'name': 'Groceries', 'type': 'expense', 'allocated': 0, 'color': '#28a745'},
            {'name': 'Transportation', 'type': 'expense', 'allocated': 0, 'color': '#17a2b8'},
            {'name': 'Utilities', 'type': 'expense', 'allocated': 0, 'color': '#ffc107'},
            {'name': 'Insurance', 'type': 'expense', 'allocated': 0, 'color': '#6f42c1'},
            
            # Lifestyle
            {'name': 'Dining Out', 'type': 'expense', 'allocated': 0, 'color': '#fd7e14'},
            {'name': 'Entertainment', 'type': 'expense', 'allocated': 0, 'color': '#e83e8c'},
            {'name': 'Shopping', 'type': 'expense', 'allocated': 0, 'color': '#20c997'},
            {'name': 'Health & Medical', 'type': 'expense', 'allocated': 0, 'color': '#6c757d'},
            
            # Savings
            {'name': 'Emergency Fund', 'type': 'saving', 'allocated': 0, 'color': '#007bff'},
            {'name': 'Vacation Fund', 'type': 'saving', 'allocated': 0, 'color': '#198754'},
            
            # Income
            {'name': 'Salary', 'type': 'income', 'allocated': 0, 'color': '#20c997'},
        ]
        
        created_categories = []
        for cat_data in default_categories:
            # Check if category already exists
            existing = BudgetCategory.query.filter_by(
                user_id=user_id, 
                name=cat_data['name']
            ).first()
            
            if not existing:
                category = BudgetCategory(
                    user_id=user_id,
                    name=cat_data['name'],
                    category_type=cat_data['type'],
                    allocated_amount=Decimal(str(cat_data['allocated'])),
                    available_amount=Decimal(str(cat_data['allocated'])),
                    color=cat_data['color']
                )
                db.session.add(category)
                created_categories.append(category)
        
        db.session.commit()
        logger.info(f"Created {len(created_categories)} default categories for user {user_id}")
        return created_categories
    
    @staticmethod
    def allocate_budget(category_id, amount, user_id):
        """Allocate budget to a category"""
        category = BudgetCategory.query.filter_by(id=category_id, user_id=user_id).first()
        
        if not category:
            raise ValueError("Category not found")
        
        if amount < 0:
            raise ValueError("Allocation amount cannot be negative")
        
        # Calculate the difference to adjust available amount
        old_allocated = category.allocated_amount
        difference = amount - old_allocated
        
        category.allocated_amount = amount
        category.available_amount += difference
        
        db.session.commit()
        
        logger.info(f"Allocated {amount} to category {category.name} for user {user_id}")
        return category
    
    @staticmethod
    def transfer_budget(from_category_id, to_category_id, amount, user_id):
        """Transfer budget between categories"""
        from_category = BudgetCategory.query.filter_by(
            id=from_category_id, user_id=user_id
        ).first()
        to_category = BudgetCategory.query.filter_by(
            id=to_category_id, user_id=user_id
        ).first()
        
        if not from_category or not to_category:
            raise ValueError("One or both categories not found")
        
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        
        # Update available amounts first to get current state
        from_category.update_available_amount()
        to_category.update_available_amount()
        
        if from_category.available_amount < amount:
            raise ValueError(f"Insufficient budget in {from_category.name}")
        
        # Perform the transfer
        from_category.available_amount -= amount
        from_category.allocated_amount -= amount
        
        to_category.available_amount += amount
        to_category.allocated_amount += amount
        
        db.session.commit()
        
        logger.info(f"Transferred {amount} from {from_category.name} to {to_category.name}")
        return from_category, to_category
    
    @staticmethod
    def get_budget_summary(user_id, month=None, year=None):
        """Get comprehensive budget summary"""
        if not month:
            month = date.today().month
        if not year:
            year = date.today().year
        
        start_date, end_date = get_month_range(year, month)
        
        categories = BudgetCategory.query.filter_by(user_id=user_id).all()
        
        summary = {
            'income': {'allocated': Decimal('0'), 'actual': Decimal('0')},
            'expenses': {'allocated': Decimal('0'), 'spent': Decimal('0'), 'available': Decimal('0')},
            'savings': {'allocated': Decimal('0'), 'saved': Decimal('0')},
            'categories': [],
            'health_score': 0
        }
        
        health_scores = []
        
        for category in categories:
            # Get actual spending/income for this category in the period
            actual_amount = db.session.query(func.sum(Transaction.amount))\
                .filter_by(user_id=user_id, category_id=category.id)\
                .filter(Transaction.transaction_date >= start_date)\
                .filter(Transaction.transaction_date <= end_date)
            
            if category.category_type == 'expense':
                actual_amount = actual_amount.filter_by(transaction_type='expense').scalar() or Decimal('0')
                available = category.allocated_amount - actual_amount
                
                summary['expenses']['allocated'] += category.allocated_amount
                summary['expenses']['spent'] += actual_amount
                summary['expenses']['available'] += available
                
                # Calculate health score for this category
                health_status = get_budget_health_status(available, category.allocated_amount)
                health_score = {'success': 100, 'warning': 60, 'danger': 20}.get(health_status, 50)
                health_scores.append(health_score)
                
            elif category.category_type == 'income':
                actual_amount = actual_amount.filter_by(transaction_type='income').scalar() or Decimal('0')
                summary['income']['allocated'] += category.allocated_amount
                summary['income']['actual'] += actual_amount
                
            elif category.category_type == 'saving':
                actual_amount = actual_amount.filter_by(transaction_type='transfer').scalar() or Decimal('0')
                summary['savings']['allocated'] += category.allocated_amount
                summary['savings']['saved'] += actual_amount
            
            category_data = {
                'id': category.id,
                'name': category.name,
                'type': category.category_type,
                'allocated': float(category.allocated_amount),
                'actual': float(actual_amount),
                'available': float(category.allocated_amount - actual_amount) if category.category_type == 'expense' else 0,
                'color': category.color,
                'health_status': get_budget_health_status(
                    category.allocated_amount - actual_amount, 
                    category.allocated_amount
                ) if category.category_type == 'expense' else 'success'
            }
            
            summary['categories'].append(category_data)
        
        # Calculate overall health score
        summary['health_score'] = int(sum(health_scores) / len(health_scores)) if health_scores else 100
        
        # Calculate budget balance
        summary['net_income'] = float(summary['income']['actual'] - summary['expenses']['spent'])
        summary['budget_balance'] = float(
            summary['income']['allocated'] - 
            summary['expenses']['allocated'] - 
            summary['savings']['allocated']
        )
        
        return summary
    
    @staticmethod
    def auto_allocate_budget(user_id, monthly_income):
        """Auto-allocate budget based on recommended percentages"""
        if not monthly_income or monthly_income <= 0:
            raise ValueError("Valid monthly income is required")
        
        # Recommended allocation percentages (YNAB-inspired)
        allocations = {
            'Housing': 0.25,          # 25%
            'Groceries': 0.10,        # 10%
            'Transportation': 0.10,   # 10%
            'Utilities': 0.05,        # 5%
            'Insurance': 0.05,        # 5%
            'Dining Out': 0.05,       # 5%
            'Entertainment': 0.05,    # 5%
            'Shopping': 0.05,         # 5%
            'Health & Medical': 0.05, # 5%
            'Emergency Fund': 0.15,   # 15%
            'Vacation Fund': 0.05,    # 5%
            'Miscellaneous': 0.05,    # 5%
        }
        
        updated_categories = []
        
        for category_name, percentage in allocations.items():
            category = BudgetCategory.query.filter_by(
                user_id=user_id, 
                name=category_name
            ).first()
            
            if category:
                new_allocation = monthly_income * Decimal(str(percentage))
                
                # Update allocation
                old_allocated = category.allocated_amount
                difference = new_allocation - old_allocated
                
                category.allocated_amount = new_allocation
                category.available_amount += difference
                
                updated_categories.append(category)
        
        db.session.commit()
        
        logger.info(f"Auto-allocated budget for {len(updated_categories)} categories for user {user_id}")
        return updated_categories
    
    @staticmethod
    def get_spending_alerts(user_id):
        """Get budget alerts for overspending or approaching limits"""
        categories = BudgetCategory.query.filter_by(
            user_id=user_id, 
            category_type='expense'
        ).all()
        
        alerts = []
        
        for category in categories:
            if category.allocated_amount <= 0:
                continue
            
            category.update_available_amount()
            
            spent_percentage = (
                (category.allocated_amount - category.available_amount) / 
                category.allocated_amount * 100
            )
            
            if spent_percentage >= 100:
                alerts.append({
                    'type': 'danger',
                    'category': category.name,
                    'message': f"You've exceeded your {category.name} budget by {format_currency(category.available_amount * -1)}",
                    'percentage': float(spent_percentage)
                })
            elif spent_percentage >= 90:
                alerts.append({
                    'type': 'warning',
                    'category': category.name,
                    'message': f"You're close to your {category.name} budget limit ({spent_percentage:.1f}% used)",
                    'percentage': float(spent_percentage)
                })
            elif spent_percentage >= 75:
                alerts.append({
                    'type': 'info',
                    'category': category.name,
                    'message': f"You've used {spent_percentage:.1f}% of your {category.name} budget",
                    'percentage': float(spent_percentage)
                })
        
        return alerts
    
    @staticmethod
    def update_category_amounts(user_id):
        """Update available amounts for all categories based on transactions"""
        categories = BudgetCategory.query.filter_by(user_id=user_id).all()
        
        updated_count = 0
        for category in categories:
            old_available = category.available_amount
            category.update_available_amount()
            
            if category.available_amount != old_available:
                updated_count += 1
        
        db.session.commit()
        
        logger.info(f"Updated available amounts for {updated_count} categories for user {user_id}")
        return updated_count
    
    @staticmethod
    def get_category_trend(category_id, user_id, months=6):
        """Get spending trend for a category over time"""
        category = BudgetCategory.query.filter_by(
            id=category_id, 
            user_id=user_id
        ).first()
        
        if not category:
            raise ValueError("Category not found")
        
        trend_data = []
        end_date = date.today()
        
        for i in range(months - 1, -1, -1):
            month_date = end_date.replace(day=1) - timedelta(days=30 * i)
            start_date, month_end = get_month_range(month_date.year, month_date.month)
            
            # Get spending for this month
            spent_amount = db.session.query(func.sum(Transaction.amount))\
                .filter_by(user_id=user_id, category_id=category_id, transaction_type='expense')\
                .filter(Transaction.transaction_date >= start_date)\
                .filter(Transaction.transaction_date <= month_end)\
                .scalar() or Decimal('0')
            
            trend_data.append({
                'month': month_date.strftime('%Y-%m'),
                'month_name': month_date.strftime('%B %Y'),
                'spent': float(spent_amount),
                'allocated': float(category.allocated_amount),
                'percentage_used': float((spent_amount / category.allocated_amount * 100)) if category.allocated_amount > 0 else 0
            })
        
        return {
            'category': category.name,
            'trend': trend_data,
            'average_spending': sum(item['spent'] for item in trend_data) / len(trend_data),
            'trend_direction': BudgetService._calculate_trend_direction(trend_data)
        }
    
    @staticmethod
    def _calculate_trend_direction(trend_data):
        """Calculate whether spending is trending up, down, or stable"""
        if len(trend_data) < 2:
            return 'stable'
        
        recent_avg = sum(item['spent'] for item in trend_data[-2:]) / 2
        older_avg = sum(item['spent'] for item in trend_data[:-2]) / max(1, len(trend_data) - 2)
        
        if recent_avg > older_avg * 1.1:  # 10% threshold
            return 'increasing'
        elif recent_avg < older_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'

# Create singleton instance
budget_service = BudgetService()