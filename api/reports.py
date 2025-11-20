from flask import Blueprint, request, jsonify, send_file, current_app, abort
from flask_login import login_required, current_user
from models import db, Transaction, BudgetCategory, Milestone, Report
from utils import login_required_api, get_month_range, get_year_range, format_currency, ensure_directory_exists
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc, extract
from werkzeug.security import safe_join
import json
import os

reports_api_bp = Blueprint('reports_api', __name__)

@reports_api_bp.route('/financial-summary', methods=['GET'])
@login_required_api
def financial_summary():
    """Get comprehensive financial summary"""
    # Date range parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    period = request.args.get('period', 'month')  # month, year, custom
    
    # Set default date range based on period
    today = date.today()
    if period == 'year':
        start_date, end_date = get_year_range(today.year)
    elif period == 'month':
        start_date, end_date = get_month_range(today.year, today.month)
    else:
        # Custom period
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date).date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format'}), 400
        else:
            start_date, _ = get_month_range(today.year, today.month)
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date).date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format'}), 400
        else:
            end_date = today
    
    # Get transactions in date range
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .filter(Transaction.transaction_date >= start_date)\
        .filter(Transaction.transaction_date <= end_date).all()
    
    # Calculate totals
    income_total = sum(t.amount for t in transactions if t.transaction_type == 'income')
    expense_total = sum(t.amount for t in transactions if t.transaction_type == 'expense')
    transfer_total = sum(t.amount for t in transactions if t.transaction_type == 'transfer')
    net_income = income_total - expense_total
    
    # Category breakdown
    category_breakdown = {}
    for transaction in transactions:
        if transaction.budget_category and transaction.transaction_type == 'expense':
            cat_name = transaction.budget_category.name
            if cat_name not in category_breakdown:
                category_breakdown[cat_name] = {
                    'amount': Decimal('0'),
                    'count': 0,
                    'color': transaction.budget_category.color,
                    'budget_allocated': transaction.budget_category.allocated_amount,
                    'percentage_of_budget': 0
                }
            
            category_breakdown[cat_name]['amount'] += transaction.amount
            category_breakdown[cat_name]['count'] += 1
    
    # Calculate percentage of budget for each category
    for cat_name, data in category_breakdown.items():
        if data['budget_allocated'] > 0:
            data['percentage_of_budget'] = round(
                (float(data['amount']) / float(data['budget_allocated'])) * 100, 1
            )
    
    # Monthly comparison (last 6 months for trend)
    monthly_trend = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        month_start, month_end = get_month_range(month_date.year, month_date.month)
        
        month_transactions = Transaction.query.filter_by(user_id=current_user.id)\
            .filter(Transaction.transaction_date >= month_start)\
            .filter(Transaction.transaction_date <= month_end).all()
        
        month_income = sum(t.amount for t in month_transactions if t.transaction_type == 'income')
        month_expenses = sum(t.amount for t in month_transactions if t.transaction_type == 'expense')
        
        monthly_trend.append({
            'month': month_date.strftime('%Y-%m'),
            'month_name': month_date.strftime('%B %Y'),
            'income': float(month_income),
            'expenses': float(month_expenses),
            'net': float(month_income - month_expenses),
            'transaction_count': len(month_transactions)
        })
    
    # Top spending categories
    top_categories = sorted(
        [(name, data) for name, data in category_breakdown.items()],
        key=lambda x: x[1]['amount'],
        reverse=True
    )[:5]
    
    return jsonify({
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': (end_date - start_date).days + 1
        },
        'totals': {
            'income': float(income_total),
            'expenses': float(expense_total),
            'transfers': float(transfer_total),
            'net_income': float(net_income),
            'transaction_count': len(transactions)
        },
        'category_breakdown': {
            name: {
                'amount': float(data['amount']),
                'count': data['count'],
                'color': data['color'],
                'budget_allocated': float(data['budget_allocated']),
                'percentage_of_budget': data['percentage_of_budget']
            }
            for name, data in category_breakdown.items()
        },
        'monthly_trend': monthly_trend,
        'top_categories': [
            {
                'name': name,
                'amount': float(data['amount']),
                'percentage_of_total': round((float(data['amount']) / float(expense_total)) * 100, 1) if expense_total > 0 else 0
            }
            for name, data in top_categories
        ]
    })

@reports_api_bp.route('/budget-performance', methods=['GET'])
@login_required_api
def budget_performance():
    """Get budget performance report"""
    # Get current month by default
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)
    
    start_date, end_date = get_month_range(year, month)
    
    # Get all budget categories
    categories = BudgetCategory.query.filter_by(user_id=current_user.id).all()
    
    performance_data = []
    
    for category in categories:
        if category.category_type != 'expense':
            continue  # Only analyze expense categories
        
        # Get spending in this category for the period
        spent_amount = db.session.query(func.sum(Transaction.amount))\
            .filter_by(user_id=current_user.id, category_id=category.id, transaction_type='expense')\
            .filter(Transaction.transaction_date >= start_date)\
            .filter(Transaction.transaction_date <= end_date)\
            .scalar() or Decimal('0')
        
        remaining_budget = category.allocated_amount - spent_amount
        budget_utilization = (float(spent_amount) / float(category.allocated_amount) * 100) if category.allocated_amount > 0 else 0
        
        # Determine status
        status = 'success'  # Under budget
        if budget_utilization >= 100:
            status = 'danger'  # Over budget
        elif budget_utilization >= 75:
            status = 'warning'  # Close to budget limit
        
        performance_data.append({
            'category_id': category.id,
            'category_name': category.name,
            'color': category.color,
            'allocated_amount': float(category.allocated_amount),
            'spent_amount': float(spent_amount),
            'remaining_budget': float(remaining_budget),
            'budget_utilization': round(budget_utilization, 1),
            'status': status,
            'over_budget': budget_utilization > 100,
            'over_budget_amount': float(spent_amount - category.allocated_amount) if spent_amount > category.allocated_amount else 0
        })
    
    # Summary statistics
    total_allocated = sum(item['allocated_amount'] for item in performance_data)
    total_spent = sum(item['spent_amount'] for item in performance_data)
    overall_utilization = (total_spent / total_allocated * 100) if total_allocated > 0 else 0
    
    categories_over_budget = sum(1 for item in performance_data if item['over_budget'])
    categories_warning = sum(1 for item in performance_data if item['status'] == 'warning')
    categories_success = sum(1 for item in performance_data if item['status'] == 'success')
    
    return jsonify({
        'period': {
            'month': month,
            'year': year,
            'month_name': start_date.strftime('%B %Y'),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'summary': {
            'total_allocated': total_allocated,
            'total_spent': total_spent,
            'remaining_budget': total_allocated - total_spent,
            'overall_utilization': round(overall_utilization, 1),
            'categories_total': len(performance_data),
            'categories_over_budget': categories_over_budget,
            'categories_warning': categories_warning,
            'categories_success': categories_success
        },
        'categories': sorted(performance_data, key=lambda x: x['budget_utilization'], reverse=True)
    })

@reports_api_bp.route('/spending-trends', methods=['GET'])
@login_required_api
def spending_trends():
    """Get spending trends over time"""
    period = request.args.get('period', 'monthly')  # daily, weekly, monthly, yearly
    months_back = request.args.get('months_back', 12, type=int)
    category_id = request.args.get('category_id', type=int)
    
    end_date = date.today()
    start_date = end_date.replace(day=1) - timedelta(days=30 * months_back)
    
    query = Transaction.query.filter_by(user_id=current_user.id, transaction_type='expense')\
        .filter(Transaction.transaction_date >= start_date)\
        .filter(Transaction.transaction_date <= end_date)
    
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    
    transactions = query.all()
    
    # Group transactions by period
    trends = {}
    
    if period == 'monthly':
        for transaction in transactions:
            month_key = transaction.transaction_date.strftime('%Y-%m')
            if month_key not in trends:
                trends[month_key] = {
                    'period': transaction.transaction_date.strftime('%B %Y'),
                    'amount': Decimal('0'),
                    'count': 0,
                    'start_date': transaction.transaction_date.replace(day=1).isoformat()
                }
            trends[month_key]['amount'] += transaction.amount
            trends[month_key]['count'] += 1
    
    elif period == 'weekly':
        for transaction in transactions:
            # Get Monday of the week
            monday = transaction.transaction_date - timedelta(days=transaction.transaction_date.weekday())
            week_key = monday.isoformat()
            if week_key not in trends:
                trends[week_key] = {
                    'period': f"Week of {monday.strftime('%B %d, %Y')}",
                    'amount': Decimal('0'),
                    'count': 0,
                    'start_date': monday.isoformat()
                }
            trends[week_key]['amount'] += transaction.amount
            trends[week_key]['count'] += 1
    
    elif period == 'daily':
        # Limit to last 30 days for daily view
        start_date = end_date - timedelta(days=30)
        for transaction in transactions:
            if transaction.transaction_date >= start_date:
                day_key = transaction.transaction_date.isoformat()
                if day_key not in trends:
                    trends[day_key] = {
                        'period': transaction.transaction_date.strftime('%B %d, %Y'),
                        'amount': Decimal('0'),
                        'count': 0,
                        'start_date': day_key
                    }
                trends[day_key]['amount'] += transaction.amount
                trends[day_key]['count'] += 1
    
    # Convert to list and sort
    trend_list = []
    for key, data in trends.items():
        trend_list.append({
            'period': data['period'],
            'amount': float(data['amount']),
            'count': data['count'],
            'start_date': data['start_date'],
            'average_per_transaction': float(data['amount'] / data['count']) if data['count'] > 0 else 0
        })
    
    trend_list.sort(key=lambda x: x['start_date'])
    
    # Calculate statistics
    amounts = [item['amount'] for item in trend_list]
    avg_spending = sum(amounts) / len(amounts) if amounts else 0
    max_spending = max(amounts) if amounts else 0
    min_spending = min(amounts) if amounts else 0
    
    # Calculate trend direction (comparing first half to second half)
    if len(amounts) >= 4:
        first_half_avg = sum(amounts[:len(amounts)//2]) / (len(amounts)//2)
        second_half_avg = sum(amounts[len(amounts)//2:]) / (len(amounts) - len(amounts)//2)
        trend_direction = 'increasing' if second_half_avg > first_half_avg else 'decreasing'
        trend_percentage = abs((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
    else:
        trend_direction = 'stable'
        trend_percentage = 0
    
    return jsonify({
        'period_type': period,
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'category_filter': category_id,
        'trends': trend_list,
        'statistics': {
            'average_spending': round(avg_spending, 2),
            'max_spending': max_spending,
            'min_spending': min_spending,
            'total_periods': len(trend_list),
            'trend_direction': trend_direction,
            'trend_percentage': round(trend_percentage, 1)
        }
    })

@reports_api_bp.route('/milestone-progress', methods=['GET'])
@login_required_api
def milestone_progress():
    """Get milestone progress report"""
    milestones = Milestone.query.filter_by(user_id=current_user.id)\
        .order_by(Milestone.target_date.asc().nullslast()).all()
    
    milestone_data = []
    total_target = Decimal('0')
    total_current = Decimal('0')
    
    for milestone in milestones:
        days_remaining = None
        if milestone.target_date and not milestone.completed:
            days_remaining = (milestone.target_date - date.today()).days
        
        milestone_data.append({
            'id': milestone.id,
            'name': milestone.name,
            'category': milestone.category,
            'target_amount': float(milestone.target_amount),
            'current_amount': float(milestone.current_amount),
            'progress_percentage': milestone.progress_percentage,
            'completed': milestone.completed,
            'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
            'completed_date': milestone.completed_date.isoformat() if milestone.completed_date else None,
            'days_remaining': days_remaining,
            'is_overdue': milestone.is_overdue,
            'monthly_target': 0,  # Will calculate below
            'on_track': True  # Will calculate below
        })
        
        total_target += milestone.target_amount
        total_current += milestone.current_amount
        
        # Calculate monthly target if target date is set
        if milestone.target_date and not milestone.completed:
            months_remaining = max(1, (milestone.target_date.year - date.today().year) * 12 + 
                                 milestone.target_date.month - date.today().month)
            remaining_amount = milestone.target_amount - milestone.current_amount
            milestone_data[-1]['monthly_target'] = float(remaining_amount / months_remaining)
            
            # Check if on track (simple heuristic: current progress vs time progress)
            time_progress = 1 - (months_remaining / 12)  # Assuming 1-year goals
            milestone_progress = milestone.progress_percentage / 100
            milestone_data[-1]['on_track'] = milestone_progress >= time_progress * 0.8  # 80% buffer
    
    # Category summary
    category_summary = {}
    for milestone in milestone_data:
        cat = milestone['category']
        if cat not in category_summary:
            category_summary[cat] = {
                'count': 0,
                'completed_count': 0,
                'total_target': 0,
                'total_current': 0,
                'average_progress': 0
            }
        
        summary = category_summary[cat]
        summary['count'] += 1
        summary['total_target'] += milestone['target_amount']
        summary['total_current'] += milestone['current_amount']
        if milestone['completed']:
            summary['completed_count'] += 1
    
    # Calculate average progress for each category
    for cat, summary in category_summary.items():
        if summary['total_target'] > 0:
            summary['average_progress'] = round(
                (summary['total_current'] / summary['total_target']) * 100, 1
            )
        summary['completion_rate'] = round(
            (summary['completed_count'] / summary['count']) * 100, 1
        ) if summary['count'] > 0 else 0
    
    return jsonify({
        'milestones': milestone_data,
        'summary': {
            'total_milestones': len(milestone_data),
            'completed_milestones': sum(1 for m in milestone_data if m['completed']),
            'overdue_milestones': sum(1 for m in milestone_data if m['is_overdue']),
            'total_target_amount': float(total_target),
            'total_current_amount': float(total_current),
            'overall_progress': round((float(total_current) / float(total_target)) * 100, 1) if total_target > 0 else 0,
            'milestones_on_track': sum(1 for m in milestone_data if m['on_track'] and not m['completed'])
        },
        'category_summary': category_summary
    })

@reports_api_bp.route('/export', methods=['POST'])
@login_required_api
def export_report():
    """Export report data to various formats"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    report_type = data.get('report_type')  # financial-summary, budget-performance, etc.
    export_format = data.get('format', 'json')  # json, csv, xlsx
    parameters = data.get('parameters', {})
    
    if not report_type:
        return jsonify({'error': 'Report type is required'}), 400
    
    if export_format not in ['json', 'csv', 'xlsx']:
        return jsonify({'error': 'Invalid export format'}), 400
    
    try:
        # Generate report data based on type
        if report_type == 'financial-summary':
            # Use existing endpoint logic
            report_data = financial_summary().get_json()
        elif report_type == 'budget-performance':
            report_data = budget_performance().get_json()
        elif report_type == 'spending-trends':
            report_data = spending_trends().get_json()
        elif report_type == 'milestone-progress':
            report_data = milestone_progress().get_json()
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # Create reports directory
        reports_dir = ensure_directory_exists('reports')
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_type}_{current_user.username}_{timestamp}"
        
        if export_format == 'json':
            filepath = os.path.join(reports_dir, f"{filename}.json")
            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
        
        elif export_format == 'csv':
            import csv
            filepath = os.path.join(reports_dir, f"{filename}.csv")
            
            # Convert report data to CSV format (simplified)
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                if report_type == 'financial-summary' and 'category_breakdown' in report_data:
                    writer.writerow(['Category', 'Amount', 'Count', 'Budget Allocated', 'Percentage of Budget'])
                    for cat_name, cat_data in report_data['category_breakdown'].items():
                        writer.writerow([
                            cat_name,
                            cat_data['amount'],
                            cat_data['count'],
                            cat_data['budget_allocated'],
                            cat_data['percentage_of_budget']
                        ])
        
        elif export_format == 'xlsx':
            # This would require openpyxl
            return jsonify({'error': 'XLSX export not implemented yet'}), 501
        
        # Save report record
        report_record = Report(
            user_id=current_user.id,
            name=f"{report_type.replace('-', ' ').title()} Report",
            report_type=report_type,
            parameters=parameters,
            file_path=filepath
        )
        
        db.session.add(report_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Report exported successfully',
            'report_id': report_record.id,
            'filename': os.path.basename(filepath),
            'format': export_format
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@reports_api_bp.route('/saved', methods=['GET'])
@login_required_api
def get_saved_reports():
    """Get list of saved reports"""
    reports = Report.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Report.generated_at)).all()
    
    report_list = []
    for report in reports:
        # Check if file still exists
        file_exists = os.path.exists(report.file_path) if report.file_path else False
        
        report_list.append({
            'id': report.id,
            'name': report.name,
            'report_type': report.report_type,
            'generated_at': report.generated_at.isoformat() if report.generated_at else None,
            'parameters': report.parameters,
            'file_exists': file_exists,
            'filename': os.path.basename(report.file_path) if report.file_path else None
        })
    
    return jsonify({'reports': report_list})

@reports_api_bp.route('/download/<int:report_id>')
@login_required_api
def download_report(report_id):
    """Download a saved report file"""
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    if not report.file_path:
        return jsonify({'error': 'Report file not found'}), 404

    # Sanitize file path to prevent path traversal attacks
    # Get absolute path to reports directory
    reports_dir = os.path.abspath(current_app.config.get('REPORTS_FOLDER', 'reports'))

    # Extract just the filename from the stored path
    filename = os.path.basename(report.file_path)

    # Use safe_join to ensure the path stays within reports directory
    safe_path = safe_join(reports_dir, filename)

    if not safe_path or not os.path.exists(safe_path):
        return jsonify({'error': 'Report file not found'}), 404

    # Verify the file is actually within the reports directory
    if not os.path.abspath(safe_path).startswith(reports_dir):
        return jsonify({'error': 'Invalid file path'}), 403

    try:
        return send_file(safe_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500