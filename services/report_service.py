from models import db, Transaction, BudgetCategory, Milestone, User
from decimal import Decimal
from datetime import date, datetime, timedelta
from sqlalchemy import func, desc, extract
from utils import get_month_range, get_year_range, format_currency, get_transaction_summary
import logging

logger = logging.getLogger(__name__)

class ReportService:
    """Service for generating financial reports and analytics"""
    
    @staticmethod
    def generate_monthly_report(user_id, month=None, year=None):
        """Generate comprehensive monthly financial report"""
        if not month:
            month = date.today().month
        if not year:
            year = date.today().year
        
        start_date, end_date = get_month_range(year, month)
        
        # Get all transactions for the month
        transactions = Transaction.query.filter_by(user_id=user_id)\
            .filter(Transaction.transaction_date >= start_date)\
            .filter(Transaction.transaction_date <= end_date).all()
        
        # Calculate summary
        summary = get_transaction_summary(transactions)
        
        # Category breakdown
        category_analysis = ReportService._analyze_categories(transactions)
        
        # Daily spending pattern
        daily_spending = ReportService._analyze_daily_spending(transactions, start_date, end_date)
        
        # Budget performance
        budget_performance = ReportService._analyze_budget_performance(user_id, start_date, end_date)
        
        # Top payees
        top_payees = ReportService._analyze_top_payees(transactions)
        
        # Generate insights
        insights = ReportService._generate_monthly_insights(summary, category_analysis, budget_performance)
        
        report = {
            'period': {
                'month': month,
                'year': year,
                'month_name': start_date.strftime('%B %Y'),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days_in_month': (end_date - start_date).days + 1
            },
            'summary': {
                'total_income': float(summary['total_income']),
                'total_expenses': float(summary['total_expenses']),
                'net_income': float(summary['net_amount']),
                'transaction_count': summary['transaction_count'],
                'average_daily_spending': float(summary['total_expenses'] / ((end_date - start_date).days + 1)),
                'savings_rate': (float(summary['net_amount']) / float(summary['total_income']) * 100) if summary['total_income'] > 0 else 0
            },
            'category_analysis': category_analysis,
            'daily_spending': daily_spending,
            'budget_performance': budget_performance,
            'top_payees': top_payees,
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Generated monthly report for user {user_id} - {month}/{year}")
        return report
    
    @staticmethod
    def generate_yearly_report(user_id, year=None):
        """Generate comprehensive yearly financial report"""
        if not year:
            year = date.today().year
        
        start_date, end_date = get_year_range(year)
        
        # Get all transactions for the year
        transactions = Transaction.query.filter_by(user_id=user_id)\
            .filter(Transaction.transaction_date >= start_date)\
            .filter(Transaction.transaction_date <= end_date).all()
        
        # Monthly breakdown
        monthly_breakdown = []
        for month in range(1, 13):
            month_start, month_end = get_month_range(year, month)
            month_transactions = [t for t in transactions 
                                if month_start <= t.transaction_date <= month_end]
            
            month_summary = get_transaction_summary(month_transactions)
            monthly_breakdown.append({
                'month': month,
                'month_name': month_start.strftime('%B'),
                'income': float(month_summary['total_income']),
                'expenses': float(month_summary['total_expenses']),
                'net': float(month_summary['net_amount']),
                'transaction_count': month_summary['transaction_count']
            })
        
        # Overall summary
        year_summary = get_transaction_summary(transactions)
        
        # Category trends
        category_trends = ReportService._analyze_yearly_category_trends(user_id, year)
        
        # Milestone progress
        milestone_progress = ReportService._analyze_milestone_progress(user_id, year)
        
        # Generate yearly insights
        insights = ReportService._generate_yearly_insights(year_summary, monthly_breakdown, category_trends)
        
        report = {
            'period': {
                'year': year,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_income': float(year_summary['total_income']),
                'total_expenses': float(year_summary['total_expenses']),
                'net_income': float(year_summary['net_amount']),
                'transaction_count': year_summary['transaction_count'],
                'average_monthly_income': float(year_summary['total_income'] / 12),
                'average_monthly_expenses': float(year_summary['total_expenses'] / 12),
                'savings_rate': (float(year_summary['net_amount']) / float(year_summary['total_income']) * 100) if year_summary['total_income'] > 0 else 0
            },
            'monthly_breakdown': monthly_breakdown,
            'category_trends': category_trends,
            'milestone_progress': milestone_progress,
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Generated yearly report for user {user_id} - {year}")
        return report
    
    @staticmethod
    def generate_category_report(user_id, category_id, months=12):
        """Generate detailed report for a specific category"""
        category = BudgetCategory.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            raise ValueError("Category not found")
        
        end_date = date.today()
        start_date = end_date.replace(day=1) - timedelta(days=30 * months)
        
        # Get transactions for this category
        transactions = Transaction.query.filter_by(user_id=user_id, category_id=category_id)\
            .filter(Transaction.transaction_date >= start_date)\
            .filter(Transaction.transaction_date <= end_date)\
            .order_by(desc(Transaction.transaction_date)).all()
        
        # Monthly breakdown
        monthly_data = []
        for i in range(months - 1, -1, -1):
            month_date = end_date.replace(day=1) - timedelta(days=30 * i)
            month_start, month_end = get_month_range(month_date.year, month_date.month)
            
            month_transactions = [t for t in transactions 
                                if month_start <= t.transaction_date <= month_end]
            
            total_amount = sum(t.amount for t in month_transactions)
            
            monthly_data.append({
                'month': month_date.strftime('%Y-%m'),
                'month_name': month_date.strftime('%B %Y'),
                'amount': float(total_amount),
                'transaction_count': len(month_transactions),
                'average_transaction': float(total_amount / len(month_transactions)) if month_transactions else 0,
                'budget_allocated': float(category.allocated_amount),
                'percentage_of_budget': (float(total_amount) / float(category.allocated_amount) * 100) if category.allocated_amount > 0 else 0
            })
        
        # Top payees for this category
        payee_analysis = {}
        for transaction in transactions:
            if transaction.payee:
                payee = transaction.payee
                if payee not in payee_analysis:
                    payee_analysis[payee] = {'amount': Decimal('0'), 'count': 0}
                payee_analysis[payee]['amount'] += transaction.amount
                payee_analysis[payee]['count'] += 1
        
        top_payees = sorted(
            [(payee, data) for payee, data in payee_analysis.items()],
            key=lambda x: x[1]['amount'],
            reverse=True
        )[:10]
        
        # Calculate trends
        recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
        older_months = monthly_data[:-3] if len(monthly_data) >= 6 else []
        
        trend_direction = 'stable'
        if older_months and recent_months:
            recent_avg = sum(m['amount'] for m in recent_months) / len(recent_months)
            older_avg = sum(m['amount'] for m in older_months) / len(older_months)
            
            if recent_avg > older_avg * 1.1:
                trend_direction = 'increasing'
            elif recent_avg < older_avg * 0.9:
                trend_direction = 'decreasing'
        
        total_spent = sum(t.amount for t in transactions)
        average_monthly = total_spent / months if months > 0 else 0
        
        report = {
            'category': {
                'id': category.id,
                'name': category.name,
                'type': category.category_type,
                'allocated_amount': float(category.allocated_amount),
                'color': category.color
            },
            'period': {
                'months': months,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_spent': float(total_spent),
                'transaction_count': len(transactions),
                'average_monthly': float(average_monthly),
                'average_transaction': float(total_spent / len(transactions)) if transactions else 0,
                'trend_direction': trend_direction
            },
            'monthly_data': monthly_data,
            'top_payees': [
                {
                    'payee': payee,
                    'amount': float(data['amount']),
                    'count': data['count'],
                    'percentage': (float(data['amount']) / float(total_spent) * 100) if total_spent > 0 else 0
                }
                for payee, data in top_payees
            ],
            'recent_transactions': [
                {
                    'date': t.transaction_date.isoformat(),
                    'description': t.description,
                    'amount': float(t.amount),
                    'payee': t.payee
                }
                for t in transactions[:10]  # Last 10 transactions
            ],
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Generated category report for {category.name} - user {user_id}")
        return report
    
    @staticmethod
    def _analyze_categories(transactions):
        """Analyze spending by category"""
        category_data = {}
        
        for transaction in transactions:
            if transaction.transaction_type == 'expense' and transaction.budget_category:
                cat_name = transaction.budget_category.name
                if cat_name not in category_data:
                    category_data[cat_name] = {
                        'amount': Decimal('0'),
                        'count': 0,
                        'color': transaction.budget_category.color
                    }
                
                category_data[cat_name]['amount'] += transaction.amount
                category_data[cat_name]['count'] += 1
        
        # Sort by amount and convert to list
        sorted_categories = sorted(
            [(name, data) for name, data in category_data.items()],
            key=lambda x: x[1]['amount'],
            reverse=True
        )
        
        total_expenses = sum(data['amount'] for _, data in sorted_categories)
        
        return [
            {
                'name': name,
                'amount': float(data['amount']),
                'count': data['count'],
                'color': data['color'],
                'percentage': (float(data['amount']) / float(total_expenses) * 100) if total_expenses > 0 else 0
            }
            for name, data in sorted_categories
        ]
    
    @staticmethod
    def _analyze_daily_spending(transactions, start_date, end_date):
        """Analyze daily spending patterns"""
        daily_data = {}
        
        # Initialize all days with 0
        current_date = start_date
        while current_date <= end_date:
            daily_data[current_date.isoformat()] = 0
            current_date += timedelta(days=1)
        
        # Fill in actual spending
        for transaction in transactions:
            if transaction.transaction_type == 'expense':
                date_key = transaction.transaction_date.isoformat()
                daily_data[date_key] += float(transaction.amount)
        
        # Convert to list and sort
        daily_spending = [
            {
                'date': date_str,
                'amount': amount,
                'day_of_week': datetime.fromisoformat(date_str).strftime('%A')
            }
            for date_str, amount in sorted(daily_data.items())
        ]
        
        return daily_spending
    
    @staticmethod
    def _analyze_budget_performance(user_id, start_date, end_date):
        """Analyze budget performance for the period"""
        categories = BudgetCategory.query.filter_by(user_id=user_id, category_type='expense').all()
        
        performance_data = []
        
        for category in categories:
            # Get spending in this category for the period
            spent_amount = db.session.query(func.sum(Transaction.amount))\
                .filter_by(user_id=user_id, category_id=category.id, transaction_type='expense')\
                .filter(Transaction.transaction_date >= start_date)\
                .filter(Transaction.transaction_date <= end_date)\
                .scalar() or Decimal('0')
            
            budget_utilization = (float(spent_amount) / float(category.allocated_amount) * 100) if category.allocated_amount > 0 else 0
            
            performance_data.append({
                'category': category.name,
                'allocated': float(category.allocated_amount),
                'spent': float(spent_amount),
                'remaining': float(category.allocated_amount - spent_amount),
                'utilization': round(budget_utilization, 1),
                'status': 'over' if budget_utilization > 100 else 'warning' if budget_utilization > 90 else 'good'
            })
        
        return sorted(performance_data, key=lambda x: x['utilization'], reverse=True)
    
    @staticmethod
    def _analyze_top_payees(transactions):
        """Analyze top payees by spending"""
        payee_data = {}
        
        for transaction in transactions:
            if transaction.transaction_type == 'expense' and transaction.payee:
                payee = transaction.payee
                if payee not in payee_data:
                    payee_data[payee] = {'amount': Decimal('0'), 'count': 0}
                
                payee_data[payee]['amount'] += transaction.amount
                payee_data[payee]['count'] += 1
        
        # Sort by amount
        sorted_payees = sorted(
            [(payee, data) for payee, data in payee_data.items()],
            key=lambda x: x[1]['amount'],
            reverse=True
        )[:10]  # Top 10
        
        return [
            {
                'payee': payee,
                'amount': float(data['amount']),
                'count': data['count'],
                'average_transaction': float(data['amount'] / data['count'])
            }
            for payee, data in sorted_payees
        ]
    
    @staticmethod
    def _analyze_yearly_category_trends(user_id, year):
        """Analyze category spending trends over the year"""
        start_date, end_date = get_year_range(year)
        
        categories = BudgetCategory.query.filter_by(user_id=user_id, category_type='expense').all()
        
        trends = []
        
        for category in categories:
            monthly_amounts = []
            
            for month in range(1, 13):
                month_start, month_end = get_month_range(year, month)
                
                amount = db.session.query(func.sum(Transaction.amount))\
                    .filter_by(user_id=user_id, category_id=category.id, transaction_type='expense')\
                    .filter(Transaction.transaction_date >= month_start)\
                    .filter(Transaction.transaction_date <= month_end)\
                    .scalar() or Decimal('0')
                
                monthly_amounts.append(float(amount))
            
            # Calculate trend
            first_half_avg = sum(monthly_amounts[:6]) / 6 if monthly_amounts[:6] else 0
            second_half_avg = sum(monthly_amounts[6:]) / 6 if monthly_amounts[6:] else 0
            
            trend_direction = 'stable'
            if second_half_avg > first_half_avg * 1.1:
                trend_direction = 'increasing'
            elif second_half_avg < first_half_avg * 0.9:
                trend_direction = 'decreasing'
            
            trends.append({
                'category': category.name,
                'color': category.color,
                'monthly_amounts': monthly_amounts,
                'total_year': sum(monthly_amounts),
                'average_monthly': sum(monthly_amounts) / 12,
                'trend_direction': trend_direction,
                'volatility': max(monthly_amounts) - min(monthly_amounts) if monthly_amounts else 0
            })
        
        return sorted(trends, key=lambda x: x['total_year'], reverse=True)
    
    @staticmethod
    def _analyze_milestone_progress(user_id, year):
        """Analyze milestone progress during the year"""
        start_date, end_date = get_year_range(year)
        
        milestones = Milestone.query.filter_by(user_id=user_id).all()
        
        progress_data = []
        
        for milestone in milestones:
            # Check if milestone was active during this year
            milestone_created = milestone.created_at.date() if milestone.created_at else start_date
            milestone_active_start = max(milestone_created, start_date)
            
            if milestone_active_start <= end_date:
                progress_data.append({
                    'name': milestone.name,
                    'category': milestone.category,
                    'target_amount': float(milestone.target_amount),
                    'current_amount': float(milestone.current_amount),
                    'progress_percentage': milestone.progress_percentage,
                    'completed': milestone.completed,
                    'completed_during_year': (milestone.completed_date and 
                                            start_date <= milestone.completed_date <= end_date) if milestone.completed_date else False
                })
        
        return progress_data
    
    @staticmethod
    def _generate_monthly_insights(summary, category_analysis, budget_performance):
        """Generate insights for monthly report"""
        insights = []
        
        # Savings rate insight
        savings_rate = (float(summary['net_amount']) / float(summary['total_income']) * 100) if summary['total_income'] > 0 else 0
        
        if savings_rate > 20:
            insights.append({
                'type': 'positive',
                'title': 'Excellent Savings Rate',
                'message': f'You saved {savings_rate:.1f}% of your income this month. Keep up the great work!'
            })
        elif savings_rate > 10:
            insights.append({
                'type': 'neutral',
                'title': 'Good Savings Rate',
                'message': f'You saved {savings_rate:.1f}% of your income. Consider increasing to 20% or more.'
            })
        elif savings_rate > 0:
            insights.append({
                'type': 'warning',
                'title': 'Low Savings Rate',
                'message': f'You only saved {savings_rate:.1f}% of your income. Try to reduce expenses or increase income.'
            })
        else:
            insights.append({
                'type': 'negative',
                'title': 'Negative Savings',
                'message': 'You spent more than you earned this month. Review your budget and expenses.'
            })
        
        # Top category insight
        if category_analysis:
            top_category = category_analysis[0]
            insights.append({
                'type': 'info',
                'title': 'Top Expense Category',
                'message': f'{top_category["name"]} was your largest expense at {format_currency(top_category["amount"])} ({top_category["percentage"]:.1f}% of total expenses).'
            })
        
        # Budget performance insight
        over_budget_categories = [cat for cat in budget_performance if cat['status'] == 'over']
        if over_budget_categories:
            insights.append({
                'type': 'negative',
                'title': 'Budget Exceeded',
                'message': f'You exceeded budget in {len(over_budget_categories)} categories. Review {over_budget_categories[0]["category"]} spending.'
            })
        
        return insights
    
    @staticmethod
    def _generate_yearly_insights(summary, monthly_breakdown, category_trends):
        """Generate insights for yearly report"""
        insights = []
        
        # Overall performance
        total_saved = float(summary['net_amount'])
        if total_saved > 0:
            insights.append({
                'type': 'positive',
                'title': 'Yearly Savings Achievement',
                'message': f'You saved {format_currency(total_saved)} this year. Great financial discipline!'
            })
        
        # Best and worst months
        if monthly_breakdown:
            best_month = max(monthly_breakdown, key=lambda x: x['net'])
            worst_month = min(monthly_breakdown, key=lambda x: x['net'])
            
            insights.append({
                'type': 'info',
                'title': 'Best Financial Month',
                'message': f'{best_month["month_name"]} was your best month with {format_currency(best_month["net"])} net income.'
            })
            
            if worst_month['net'] < 0:
                insights.append({
                    'type': 'warning',
                    'title': 'Challenging Month',
                    'message': f'{worst_month["month_name"]} was challenging with {format_currency(worst_month["net"])} net income.'
                })
        
        # Category trend insights
        increasing_categories = [cat for cat in category_trends if cat['trend_direction'] == 'increasing']
        if increasing_categories:
            top_increasing = increasing_categories[0]
            insights.append({
                'type': 'warning',
                'title': 'Increasing Expenses',
                'message': f'{top_increasing["category"]} spending increased significantly this year. Consider budgeting more carefully.'
            })
        
        return insights

# Create singleton instance
report_service = ReportService()