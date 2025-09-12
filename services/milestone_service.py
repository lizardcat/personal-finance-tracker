from models import db, Milestone, Transaction
from decimal import Decimal
from datetime import date, datetime, timedelta
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

class MilestoneService:
    """Service for milestone-related operations"""
    
    @staticmethod
    def create_milestone(user_id, name, target_amount, description=None, target_date=None, category='saving'):
        """Create a new milestone"""
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Milestone name is required")
        
        if target_amount <= 0:
            raise ValueError("Target amount must be positive")
        
        # Check for duplicate names
        existing = Milestone.query.filter_by(user_id=user_id, name=name.strip()).first()
        if existing:
            raise ValueError("Milestone with this name already exists")
        
        if target_date and target_date <= date.today():
            raise ValueError("Target date must be in the future")
        
        milestone = Milestone(
            user_id=user_id,
            name=name.strip(),
            description=description.strip() if description else None,
            target_amount=Decimal(str(target_amount)),
            current_amount=Decimal('0'),
            target_date=target_date,
            category=category
        )
        
        db.session.add(milestone)
        db.session.commit()
        
        logger.info(f"Created milestone '{name}' for user {user_id}")
        return milestone
    
    @staticmethod
    def add_progress(milestone_id, amount, user_id, note=None):
        """Add progress to a milestone"""
        milestone = Milestone.query.filter_by(id=milestone_id, user_id=user_id).first()
        
        if not milestone:
            raise ValueError("Milestone not found")
        
        if milestone.completed:
            raise ValueError("Cannot add progress to completed milestone")
        
        if amount <= 0:
            raise ValueError("Progress amount must be positive")
        
        new_amount = milestone.current_amount + Decimal(str(amount))
        
        if new_amount > milestone.target_amount:
            raise ValueError("Progress amount would exceed target amount")
        
        milestone.current_amount = new_amount
        
        # Check if milestone is now completed
        if milestone.current_amount >= milestone.target_amount:
            milestone.completed = True
            milestone.completed_date = date.today()
        
        db.session.commit()
        
        logger.info(f"Added {amount} progress to milestone '{milestone.name}' for user {user_id}")
        return milestone
    
    @staticmethod
    def complete_milestone(milestone_id, user_id, set_target_amount=False):
        """Mark a milestone as completed"""
        milestone = Milestone.query.filter_by(id=milestone_id, user_id=user_id).first()
        
        if not milestone:
            raise ValueError("Milestone not found")
        
        if milestone.completed:
            raise ValueError("Milestone is already completed")
        
        milestone.completed = True
        milestone.completed_date = date.today()
        
        # Optionally set current amount to target amount
        if set_target_amount:
            milestone.current_amount = milestone.target_amount
        
        db.session.commit()
        
        logger.info(f"Completed milestone '{milestone.name}' for user {user_id}")
        return milestone
    
    @staticmethod
    def get_milestone_recommendations(user_id):
        """Get milestone recommendations based on user's financial data"""
        # Get user's average monthly income and expenses
        recent_transactions = Transaction.query.filter_by(user_id=user_id)\
            .filter(Transaction.transaction_date >= date.today() - timedelta(days=90))\
            .all()
        
        monthly_income = sum(t.amount for t in recent_transactions if t.transaction_type == 'income') / 3
        monthly_expenses = sum(t.amount for t in recent_transactions if t.transaction_type == 'expense') / 3
        monthly_surplus = monthly_income - monthly_expenses
        
        recommendations = []
        
        # Emergency Fund Recommendation
        if monthly_expenses > 0:
            emergency_fund_target = monthly_expenses * 6  # 6 months of expenses
            existing_emergency = Milestone.query.filter_by(
                user_id=user_id,
                name="Emergency Fund"
            ).first()
            
            if not existing_emergency:
                months_to_save = max(12, int(emergency_fund_target / max(monthly_surplus * 0.2, 100)))
                recommendations.append({
                    'name': 'Emergency Fund',
                    'description': 'Build an emergency fund to cover 6 months of expenses',
                    'target_amount': float(emergency_fund_target),
                    'category': 'saving',
                    'priority': 'high',
                    'recommended_monthly': float(emergency_fund_target / months_to_save),
                    'target_date': date.today() + timedelta(days=30 * months_to_save)
                })
        
        # Vacation Fund Recommendation
        if monthly_surplus > 0:
            vacation_target = Decimal('2000')  # Default vacation budget
            existing_vacation = Milestone.query.filter_by(
                user_id=user_id,
                category='saving'
            ).filter(Milestone.name.ilike('%vacation%')).first()
            
            if not existing_vacation:
                months_to_save = max(8, int(vacation_target / max(monthly_surplus * 0.1, 50)))
                recommendations.append({
                    'name': 'Vacation Fund',
                    'description': 'Save for your next vacation or travel adventure',
                    'target_amount': float(vacation_target),
                    'category': 'saving',
                    'priority': 'medium',
                    'recommended_monthly': float(vacation_target / months_to_save),
                    'target_date': date.today() + timedelta(days=30 * months_to_save)
                })
        
        # Down Payment Fund (if income is substantial)
        if monthly_income > 3000:
            down_payment_target = Decimal('20000')  # Example down payment
            existing_house = Milestone.query.filter_by(user_id=user_id)\
                .filter(Milestone.name.ilike('%house%') | Milestone.name.ilike('%down payment%')).first()
            
            if not existing_house:
                months_to_save = max(36, int(down_payment_target / max(monthly_surplus * 0.3, 200)))
                recommendations.append({
                    'name': 'House Down Payment',
                    'description': 'Save for a down payment on your future home',
                    'target_amount': float(down_payment_target),
                    'category': 'saving',
                    'priority': 'medium',
                    'recommended_monthly': float(down_payment_target / months_to_save),
                    'target_date': date.today() + timedelta(days=30 * months_to_save)
                })
        
        return recommendations
    
    @staticmethod
    def get_milestone_insights(milestone_id, user_id):
        """Get insights and analytics for a specific milestone"""
        milestone = Milestone.query.filter_by(id=milestone_id, user_id=user_id).first()
        
        if not milestone:
            raise ValueError("Milestone not found")
        
        insights = {
            'milestone': milestone,
            'progress_percentage': milestone.progress_percentage,
            'amount_remaining': float(milestone.target_amount - milestone.current_amount),
            'on_track': True,
            'recommended_monthly': 0,
            'projected_completion': None,
            'days_remaining': None,
            'status': 'active'
        }
        
        if milestone.completed:
            insights['status'] = 'completed'
            return insights
        
        if milestone.is_overdue:
            insights['status'] = 'overdue'
        
        # Calculate days remaining
        if milestone.target_date:
            days_remaining = (milestone.target_date - date.today()).days
            insights['days_remaining'] = days_remaining
            
            # Calculate if on track
            if days_remaining > 0:
                amount_remaining = milestone.target_amount - milestone.current_amount
                required_daily_savings = amount_remaining / days_remaining
                
                # Get recent saving rate
                recent_transactions = Transaction.query.filter_by(
                    user_id=user_id,
                    transaction_type='transfer'
                ).filter(
                    Transaction.transaction_date >= date.today() - timedelta(days=30)
                ).all()
                
                recent_monthly_savings = sum(t.amount for t in recent_transactions)
                daily_savings_rate = recent_monthly_savings / 30 if recent_monthly_savings else 0
                
                insights['on_track'] = daily_savings_rate >= required_daily_savings * 0.8  # 80% buffer
                insights['recommended_monthly'] = float(required_daily_savings * 30)
                
                if daily_savings_rate > 0:
                    days_to_completion = amount_remaining / daily_savings_rate
                    insights['projected_completion'] = (date.today() + timedelta(days=int(days_to_completion))).isoformat()
        
        return insights
    
    @staticmethod
    def get_user_milestone_summary(user_id):
        """Get comprehensive milestone summary for a user"""
        milestones = Milestone.query.filter_by(user_id=user_id).all()
        
        summary = {
            'total_milestones': len(milestones),
            'completed_milestones': 0,
            'active_milestones': 0,
            'overdue_milestones': 0,
            'total_target_amount': Decimal('0'),
            'total_current_amount': Decimal('0'),
            'overall_progress': 0,
            'categories': {},
            'upcoming_deadlines': []
        }
        
        for milestone in milestones:
            summary['total_target_amount'] += milestone.target_amount
            summary['total_current_amount'] += milestone.current_amount
            
            if milestone.completed:
                summary['completed_milestones'] += 1
            elif milestone.is_overdue:
                summary['overdue_milestones'] += 1
            else:
                summary['active_milestones'] += 1
            
            # Category breakdown
            category = milestone.category
            if category not in summary['categories']:
                summary['categories'][category] = {
                    'count': 0,
                    'completed': 0,
                    'target_total': Decimal('0'),
                    'current_total': Decimal('0')
                }
            
            cat_data = summary['categories'][category]
            cat_data['count'] += 1
            cat_data['target_total'] += milestone.target_amount
            cat_data['current_total'] += milestone.current_amount
            
            if milestone.completed:
                cat_data['completed'] += 1
            
            # Upcoming deadlines (next 90 days)
            if milestone.target_date and not milestone.completed:
                days_remaining = (milestone.target_date - date.today()).days
                if 0 <= days_remaining <= 90:
                    summary['upcoming_deadlines'].append({
                        'id': milestone.id,
                        'name': milestone.name,
                        'target_date': milestone.target_date.isoformat(),
                        'days_remaining': days_remaining,
                        'progress_percentage': milestone.progress_percentage,
                        'amount_remaining': float(milestone.target_amount - milestone.current_amount)
                    })
        
        # Calculate overall progress
        if summary['total_target_amount'] > 0:
            summary['overall_progress'] = float(
                (summary['total_current_amount'] / summary['total_target_amount']) * 100
            )
        
        # Convert category data to serializable format
        for category, data in summary['categories'].items():
            data['target_total'] = float(data['target_total'])
            data['current_total'] = float(data['current_total'])
            data['progress'] = (data['current_total'] / data['target_total'] * 100) if data['target_total'] > 0 else 0
        
        # Convert totals to float
        summary['total_target_amount'] = float(summary['total_target_amount'])
        summary['total_current_amount'] = float(summary['total_current_amount'])
        
        # Sort upcoming deadlines by date
        summary['upcoming_deadlines'].sort(key=lambda x: x['days_remaining'])
        
        return summary
    
    @staticmethod
    def suggest_milestone_adjustments(milestone_id, user_id):
        """Suggest adjustments to milestone based on progress"""
        milestone = Milestone.query.filter_by(id=milestone_id, user_id=user_id).first()
        
        if not milestone or milestone.completed:
            return []
        
        suggestions = []
        
        # Check if milestone is significantly behind schedule
        if milestone.target_date:
            days_remaining = (milestone.target_date - date.today()).days
            progress_percentage = milestone.progress_percentage
            
            # Calculate expected progress based on time
            total_days = (milestone.target_date - milestone.created_at.date()).days if milestone.created_at else 365
            days_elapsed = total_days - days_remaining
            expected_progress = (days_elapsed / total_days) * 100 if total_days > 0 else 0
            
            if progress_percentage < expected_progress * 0.5:  # Less than 50% of expected progress
                suggestions.append({
                    'type': 'increase_contribution',
                    'message': 'Consider increasing your monthly contribution to stay on track',
                    'recommended_monthly': float((milestone.target_amount - milestone.current_amount) / max(1, days_remaining / 30))
                })
                
                suggestions.append({
                    'type': 'extend_deadline',
                    'message': 'Consider extending the target date to make the goal more achievable',
                    'recommended_date': (milestone.target_date + timedelta(days=180)).isoformat()
                })
            
            elif progress_percentage > expected_progress * 1.5:  # More than 150% of expected progress
                suggestions.append({
                    'type': 'advance_deadline',
                    'message': 'Great progress! You might achieve this goal earlier than planned',
                    'projected_completion': (date.today() + timedelta(days=int((milestone.target_amount - milestone.current_amount) / (milestone.current_amount / max(1, days_elapsed)) * 30))).isoformat()
                })
        
        return suggestions

# Create singleton instance
milestone_service = MilestoneService()