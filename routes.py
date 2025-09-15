from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import db, BudgetCategory, Transaction, Milestone, ExchangeRate
from utils import get_month_range, get_transaction_summary, format_currency, get_budget_health_status
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, desc

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with financial overview"""
    # Get current month range
    today = date.today()
    month_start, month_end = get_month_range(today.year, today.month)
    
    # Get budget categories
    categories = BudgetCategory.query.filter_by(user_id=current_user.id).all()
    
    # Calculate budget totals
    total_allocated = sum(cat.allocated_amount for cat in categories if cat.category_type == 'expense')
    total_available = sum(cat.available_amount for cat in categories if cat.category_type == 'expense')
    total_spent = total_allocated - total_available
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .filter(Transaction.transaction_date >= month_start)\
        .filter(Transaction.transaction_date <= month_end)\
        .order_by(desc(Transaction.created_at)).limit(10).all()
    
    # Calculate monthly summary
    monthly_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .filter(Transaction.transaction_date >= month_start)\
        .filter(Transaction.transaction_date <= month_end).all()
    
    monthly_summary = get_transaction_summary(monthly_transactions)
    
    # Get milestones
    active_milestones = Milestone.query.filter_by(user_id=current_user.id, completed=False)\
        .order_by(Milestone.target_date.asc()).limit(5).all()
    
    # Get expense categories for chart
    expense_categories = [cat for cat in categories if cat.category_type == 'expense']
    
    # Get exchange rate (USD to KES)
    exchange_rate = ExchangeRate.query.filter_by(base_currency='USD', target_currency='KES').first()
    current_rate = exchange_rate.rate if exchange_rate else Decimal('150.0')
    
    return render_template('dashboard.html',
                         categories=categories,
                         expense_categories=expense_categories,
                         recent_transactions=recent_transactions,
                         monthly_summary=monthly_summary,
                         active_milestones=active_milestones,
                         total_allocated=total_allocated,
                         total_available=total_available,
                         total_spent=total_spent,
                         exchange_rate=current_rate,
                         current_month=today.strftime('%B %Y'))

@main_bp.route('/budget')
@login_required
def budget():
    """Budget management page"""
    categories = BudgetCategory.query.filter_by(user_id=current_user.id)\
        .order_by(BudgetCategory.category_type, BudgetCategory.name).all()
    
    # Get exchange rate
    exchange_rate = ExchangeRate.query.filter_by(base_currency='USD', target_currency='KES').first()
    current_rate = exchange_rate.rate if exchange_rate else Decimal('150.0')
    
    # Calculate totals by category type
    income_total = sum(cat.allocated_amount for cat in categories if cat.category_type == 'income')
    expense_total = sum(cat.allocated_amount for cat in categories if cat.category_type == 'expense')
    saving_total = sum(cat.allocated_amount for cat in categories if cat.category_type == 'saving')
    
    return render_template('budget.html',
                         categories=categories,
                         exchange_rate=current_rate,
                         income_total=income_total,
                         expense_total=expense_total,
                         saving_total=saving_total)

@main_bp.route('/transactions')
@login_required
def transactions():
    """Transaction management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    # Filter options
    category_filter = request.args.get('category', '')
    type_filter = request.args.get('type', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if category_filter:
        try:
            category_id = int(category_filter)
            query = query.filter(Transaction.category_id == category_id)
        except (ValueError, TypeError):
            pass
    
    if type_filter:
        query = query.filter(Transaction.transaction_type == type_filter)
    
    if search_query:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Transaction.description.contains(search_query),
                Transaction.payee.contains(search_query)
            )
        )
    
    # Paginate results
    try:
        transactions = query.order_by(desc(Transaction.transaction_date),
                                    desc(Transaction.created_at))\
            .paginate(page=page, per_page=per_page, error_out=False)
    except Exception as e:
        # Fallback for SQLAlchemy compatibility
        print(f"Pagination error: {e}")
        transactions = query.order_by(desc(Transaction.transaction_date),
                                    desc(Transaction.created_at)).all()
        # Create a simple pagination object
        class SimplePagination:
            def __init__(self, items):
                self.items = items
                self.pages = 1
                self.page = 1
                self.has_prev = False
                self.has_next = False
                self.prev_num = None
                self.next_num = None
            def iter_pages(self):
                return [1]
        transactions = SimplePagination(transactions)
    
    # Get categories for filter dropdown
    categories = BudgetCategory.query.filter_by(user_id=current_user.id)\
        .order_by(BudgetCategory.name).all()
    
    # Calculate page totals
    page_transactions = transactions.items
    page_summary = get_transaction_summary(page_transactions)
    
    return render_template('transactions.html',
                         transactions=transactions,
                         categories=categories,
                         page_summary=page_summary,
                         today=date.today(),
                         filters={
                             'category': category_filter,
                             'type': type_filter,
                             'search': search_query
                         })

@main_bp.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    # Get date range from query params (default to current month)
    today = date.today()
    start_date = request.args.get('start_date', today.replace(day=1).isoformat())
    end_date = request.args.get('end_date', today.isoformat())
    
    try:
        start_date = datetime.fromisoformat(start_date).date()
        end_date = datetime.fromisoformat(end_date).date()
    except:
        start_date, end_date = get_month_range(today.year, today.month)
    
    # Get transactions in date range
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .filter(Transaction.transaction_date >= start_date)\
        .filter(Transaction.transaction_date <= end_date).all()
    
    # Generate summary
    summary = get_transaction_summary(transactions)
    
    # Category breakdown
    category_spending = {}
    for trans in transactions:
        if trans.transaction_type == 'expense' and trans.budget_category:
            cat_name = trans.budget_category.name
            category_spending[cat_name] = category_spending.get(cat_name, Decimal('0')) + trans.amount
    
    # Monthly trend (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):  # Last 6 months
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        month_start, month_end = get_month_range(month_date.year, month_date.month)
        
        month_transactions = Transaction.query.filter_by(user_id=current_user.id)\
            .filter(Transaction.transaction_date >= month_start)\
            .filter(Transaction.transaction_date <= month_end).all()
        
        month_summary = get_transaction_summary(month_transactions)
        monthly_data.append({
            'month': month_date.strftime('%B %Y'),
            'income': float(month_summary['total_income']),
            'expenses': float(month_summary['total_expenses']),
            'net': float(month_summary['net_amount'])
        })
    
    return render_template('reports.html',
                         summary=summary,
                         category_spending=category_spending,
                         monthly_data=monthly_data,
                         start_date=start_date,
                         end_date=end_date,
                         date_range=f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}")

@main_bp.route('/settings')
@login_required
def settings():
    """User settings and preferences"""
    return render_template('settings.html', user=current_user)

@main_bp.route('/api/dashboard-data')
@login_required
def dashboard_data():
    """API endpoint for dashboard chart data"""
    # Get budget categories for pie chart
    categories = BudgetCategory.query.filter_by(user_id=current_user.id, category_type='expense').all()
    
    chart_data = {
        'labels': [],
        'data': [],
        'colors': []
    }
    
    for category in categories:
        if category.allocated_amount > 0:
            spent_amount = category.allocated_amount - category.available_amount
            chart_data['labels'].append(category.name)
            chart_data['data'].append(float(spent_amount))
            chart_data['colors'].append(category.color)
    
    return jsonify(chart_data)

@main_bp.route('/api/monthly-trend')
@login_required
def monthly_trend():
    """API endpoint for monthly spending trend"""
    months = []
    for i in range(5, -1, -1):  # Last 6 months
        month_date = date.today().replace(day=1) - timedelta(days=30 * i)
        month_start, month_end = get_month_range(month_date.year, month_date.month)
        
        # Get expenses for this month
        expenses = db.session.query(func.sum(Transaction.amount))\
            .filter_by(user_id=current_user.id, transaction_type='expense')\
            .filter(Transaction.transaction_date >= month_start)\
            .filter(Transaction.transaction_date <= month_end)\
            .scalar() or Decimal('0')
        
        months.append({
            'month': month_date.strftime('%b %Y'),
            'amount': float(expenses)
        })
    
    return jsonify(months)

@main_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected'
    })

# Error handler helpers
@main_bp.app_errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500