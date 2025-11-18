from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from models import db, Transaction, BudgetCategory
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class RecurringTransactionService:
    """Service for managing and processing recurring transactions"""

    def __init__(self):
        self.period_mapping = {
            'daily': {'days': 1},
            'weekly': {'weeks': 1},
            'biweekly': {'weeks': 2},
            'monthly': {'months': 1},
            'quarterly': {'months': 3},
            'yearly': {'years': 1}
        }

    def get_next_occurrence_date(self, last_date, period):
        """Calculate the next occurrence date based on period"""
        if period not in self.period_mapping:
            raise ValueError(f"Invalid recurring period: {period}")

        delta_params = self.period_mapping[period]

        # Use relativedelta for month/year-based periods to handle month-end dates properly
        if 'months' in delta_params or 'years' in delta_params:
            return last_date + relativedelta(**delta_params)
        else:
            return last_date + timedelta(**delta_params)

    def should_create_occurrence(self, last_date, period, current_date=None):
        """Check if a new occurrence should be created"""
        if current_date is None:
            current_date = date.today()

        next_date = self.get_next_occurrence_date(last_date, period)
        return next_date <= current_date

    def create_recurring_occurrence(self, template_transaction):
        """Create a new transaction instance from a recurring template"""
        # Calculate next occurrence date
        next_date = self.get_next_occurrence_date(
            template_transaction.transaction_date,
            template_transaction.recurring_period
        )

        # Create new transaction
        new_transaction = Transaction(
            user_id=template_transaction.user_id,
            category_id=template_transaction.category_id,
            amount=template_transaction.amount,
            currency=template_transaction.currency,
            description=f"{template_transaction.description} (Auto-generated)",
            transaction_type=template_transaction.transaction_type,
            transaction_date=next_date,
            payee=template_transaction.payee,
            account=template_transaction.account,
            tags=template_transaction.tags,
            recurring=False,  # The generated transaction is not recurring
            recurring_period=None
        )

        db.session.add(new_transaction)

        # Update the template transaction's date to the next occurrence
        template_transaction.transaction_date = next_date

        return new_transaction

    def process_all_recurring_transactions(self, dry_run=False):
        """Process all recurring transactions and create occurrences as needed

        Args:
            dry_run: If True, don't actually create transactions, just report what would be created

        Returns:
            dict with statistics about processing
        """
        today = date.today()

        # Get all recurring transactions
        recurring_transactions = Transaction.query.filter_by(recurring=True).all()

        created_count = 0
        skipped_count = 0
        error_count = 0
        created_transactions = []

        for template in recurring_transactions:
            try:
                # Check if we should create a new occurrence
                if self.should_create_occurrence(template.transaction_date, template.recurring_period, today):

                    # Calculate how many occurrences we've missed
                    occurrences_to_create = 0
                    check_date = template.transaction_date

                    while self.should_create_occurrence(check_date, template.recurring_period, today):
                        occurrences_to_create += 1
                        check_date = self.get_next_occurrence_date(check_date, template.recurring_period)

                        # Safety limit: don't create more than 365 occurrences at once
                        if occurrences_to_create > 365:
                            logger.warning(f"Too many occurrences ({occurrences_to_create}) for transaction {template.id}. Limiting to 365.")
                            occurrences_to_create = 365
                            break

                    # Create all missed occurrences
                    for _ in range(occurrences_to_create):
                        if not dry_run:
                            new_transaction = self.create_recurring_occurrence(template)
                            created_transactions.append({
                                'id': new_transaction.id,
                                'description': new_transaction.description,
                                'amount': float(new_transaction.amount),
                                'date': new_transaction.transaction_date.isoformat()
                            })
                            created_count += 1
                        else:
                            # In dry run, just calculate what would be created
                            next_date = self.get_next_occurrence_date(
                                template.transaction_date,
                                template.recurring_period
                            )
                            created_transactions.append({
                                'description': f"{template.description} (Auto-generated)",
                                'amount': float(template.amount),
                                'date': next_date.isoformat(),
                                'template_id': template.id
                            })
                            created_count += 1
                            template.transaction_date = next_date  # Update for next iteration

                    if not dry_run:
                        db.session.commit()
                        logger.info(f"Created {occurrences_to_create} occurrences for recurring transaction {template.id}")
                else:
                    skipped_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing recurring transaction {template.id}: {str(e)}", exc_info=True)
                if not dry_run:
                    db.session.rollback()

        return {
            'total_recurring': len(recurring_transactions),
            'created': created_count,
            'skipped': skipped_count,
            'errors': error_count,
            'created_transactions': created_transactions,
            'dry_run': dry_run
        }

    def get_recurring_transaction_summary(self, user_id):
        """Get summary of recurring transactions for a user"""
        recurring_transactions = Transaction.query.filter_by(
            user_id=user_id,
            recurring=True
        ).all()

        summary = {
            'total': len(recurring_transactions),
            'by_period': {},
            'by_type': {},
            'total_monthly_impact': Decimal('0')
        }

        for trans in recurring_transactions:
            # Count by period
            period = trans.recurring_period
            if period not in summary['by_period']:
                summary['by_period'][period] = 0
            summary['by_period'][period] += 1

            # Count by type
            trans_type = trans.transaction_type
            if trans_type not in summary['by_type']:
                summary['by_type'][trans_type] = 0
            summary['by_type'][trans_type] += 1

            # Calculate monthly impact
            monthly_multiplier = self.get_monthly_multiplier(period)
            summary['total_monthly_impact'] += trans.amount * Decimal(str(monthly_multiplier))

        return summary

    def get_monthly_multiplier(self, period):
        """Get how many times a period occurs in a month (approximately)"""
        multipliers = {
            'daily': 30,
            'weekly': 4.33,
            'biweekly': 2.17,
            'monthly': 1,
            'quarterly': 0.33,
            'yearly': 0.083
        }
        return multipliers.get(period, 1)

    def get_upcoming_occurrences(self, user_id, days_ahead=30):
        """Get upcoming recurring transaction occurrences for a user

        Args:
            user_id: User ID
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming occurrences with dates
        """
        end_date = date.today() + timedelta(days=days_ahead)

        recurring_transactions = Transaction.query.filter_by(
            user_id=user_id,
            recurring=True
        ).all()

        upcoming = []

        for template in recurring_transactions:
            check_date = template.transaction_date

            # Calculate all occurrences within the date range
            while check_date <= end_date:
                if check_date >= date.today():
                    upcoming.append({
                        'template_id': template.id,
                        'description': template.description,
                        'amount': float(template.amount),
                        'transaction_type': template.transaction_type,
                        'date': check_date.isoformat(),
                        'period': template.recurring_period,
                        'category': template.budget_category.name if template.budget_category else None,
                        'days_until': (check_date - date.today()).days
                    })

                check_date = self.get_next_occurrence_date(check_date, template.recurring_period)

        # Sort by date
        upcoming.sort(key=lambda x: x['date'])

        return upcoming

# Create singleton instance
recurring_service = RecurringTransactionService()
