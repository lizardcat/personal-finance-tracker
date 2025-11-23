from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Transaction, BudgetCategory
from utils import login_required_api, parse_currency, format_currency
from logging_config import log_audit_event
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError

transactions_api_bp = Blueprint('transactions_api', __name__)

@transactions_api_bp.route('/', methods=['GET'])
@login_required_api
def get_transactions():
    """Get transactions for the current user with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)  # Max 100 per page
    
    # Filters
    category_id = request.args.get('category_id', type=int)
    transaction_type = request.args.get('type')
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    
    if transaction_type and transaction_type in ['income', 'expense', 'transfer']:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            (Transaction.description.ilike(search_term)) |
            (Transaction.payee.ilike(search_term))
        )
    
    if start_date:
        try:
            start_date = datetime.fromisoformat(start_date).date()
            query = query.filter(Transaction.transaction_date >= start_date)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format'}), 400
    
    if end_date:
        try:
            end_date = datetime.fromisoformat(end_date).date()
            query = query.filter(Transaction.transaction_date <= end_date)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format'}), 400
    
    # Execute query with pagination
    transactions = query.order_by(desc(Transaction.transaction_date), desc(Transaction.created_at))\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    # Format results
    result = []
    for transaction in transactions.items:
        result.append({
            'id': transaction.id,
            'amount': float(transaction.amount),
            'currency': transaction.currency,
            'description': transaction.description,
            'transaction_type': transaction.transaction_type,
            'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            'payee': transaction.payee,
            'account': transaction.account,
            'tags': transaction.tags,
            'recurring': transaction.recurring,
            'recurring_period': transaction.recurring_period,
            'category': {
                'id': transaction.budget_category.id,
                'name': transaction.budget_category.name,
                'color': transaction.budget_category.color
            } if transaction.budget_category else None,
            'created_at': transaction.created_at.isoformat() if transaction.created_at else None
        })
    
    return jsonify({
        'transactions': result,
        'pagination': {
            'page': transactions.page,
            'pages': transactions.pages,
            'per_page': transactions.per_page,
            'total': transactions.total,
            'has_next': transactions.has_next,
            'has_prev': transactions.has_prev
        }
    })

@transactions_api_bp.route('/', methods=['POST'])
@login_required_api
def create_transaction():
    """Create a new transaction"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Required fields
    amount = data.get('amount')
    description = data.get('description', '').strip()
    transaction_type = data.get('transaction_type')
    
    # Optional fields
    category_id = data.get('category_id')
    currency = data.get('currency', current_user.default_currency or 'USD')
    transaction_date = data.get('transaction_date')
    payee = data.get('payee', '').strip()
    account = data.get('account', 'checking')
    tags = data.get('tags', '').strip()
    recurring = data.get('recurring', False)
    recurring_period = data.get('recurring_period')
    
    # Validation
    if not description:
        return jsonify({'error': 'Description is required'}), 400
    
    if not transaction_type or transaction_type not in ['income', 'expense', 'transfer']:
        return jsonify({'error': 'Valid transaction type is required (income, expense, transfer)'}), 400
    
    try:
        amount = parse_currency(amount)
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
    except (ValueError, InvalidOperation, TypeError) as e:
        current_app.logger.warning(f'Invalid amount provided by user {current_user.username}: {e}')
        return jsonify({'error': 'Invalid amount format'}), 400
    
    # Validate category if provided
    category = None
    if category_id:
        category = BudgetCategory.query.filter_by(id=category_id, user_id=current_user.id).first()
        if not category:
            return jsonify({'error': 'Category not found'}), 404
    
    # Parse transaction date
    if transaction_date:
        try:
            transaction_date = datetime.fromisoformat(transaction_date).date()
        except ValueError:
            return jsonify({'error': 'Invalid transaction date format'}), 400
    else:
        transaction_date = date.today()
    
    # Validate recurring fields
    if recurring and not recurring_period:
        return jsonify({'error': 'Recurring period is required for recurring transactions'}), 400
    
    if recurring_period and recurring_period not in ['daily', 'weekly', 'monthly', 'yearly']:
        return jsonify({'error': 'Invalid recurring period'}), 400
    
    try:
        # Capture exchange rate for historical accuracy
        exchange_rate = None
        if currency != current_user.default_currency:
            try:
                from services.exchange_rate_service import exchange_rate_service
                exchange_rate = exchange_rate_service.get_rate(currency, current_user.default_currency)
            except Exception as e:
                current_app.logger.warning(f'Could not fetch exchange rate for {currency} to {current_user.default_currency}: {e}')

        # Create transaction
        transaction = Transaction(
            user_id=current_user.id,
            category_id=category_id,
            amount=amount,
            currency=currency,
            exchange_rate_to_user_currency=exchange_rate,
            description=description,
            transaction_type=transaction_type,
            transaction_date=transaction_date,
            payee=payee or None,
            account=account,
            tags=tags or None,
            recurring=recurring,
            recurring_period=recurring_period
        )
        
        db.session.add(transaction)
        
        # Update budget category if it's an expense
        if category and transaction_type == 'expense':
            category.available_amount -= amount

        db.session.commit()

        # Log audit event for transaction creation
        log_audit_event(
            action='CREATE',
            user_id=current_user.id,
            username=current_user.username,
            entity_type='Transaction',
            entity_id=transaction.id,
            new_value=f'{transaction_type}: {amount} {currency} - {description}',
            ip_address=request.remote_addr
        )
        current_app.logger.info(f'Transaction created: ID={transaction.id}, User={current_user.username}, Amount={amount}, Type={transaction_type}')

        return jsonify({
            'success': True,
            'message': 'Transaction created successfully',
            'transaction': {
                'id': transaction.id,
                'amount': float(transaction.amount),
                'currency': transaction.currency,
                'description': transaction.description,
                'transaction_type': transaction.transaction_type,
                'transaction_date': transaction.transaction_date.isoformat(),
                'payee': transaction.payee,
                'account': transaction.account,
                'category': {
                    'id': category.id,
                    'name': category.name
                } if category else None
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create transaction'}), 500

@transactions_api_bp.route('/<int:transaction_id>', methods=['GET'])
@login_required_api
def get_transaction(transaction_id):
    """Get a specific transaction"""
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    return jsonify({
        'id': transaction.id,
        'amount': float(transaction.amount),
        'currency': transaction.currency,
        'description': transaction.description,
        'transaction_type': transaction.transaction_type,
        'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
        'payee': transaction.payee,
        'account': transaction.account,
        'tags': transaction.tags,
        'recurring': transaction.recurring,
        'recurring_period': transaction.recurring_period,
        'category': {
            'id': transaction.budget_category.id,
            'name': transaction.budget_category.name,
            'color': transaction.budget_category.color,
            'type': transaction.budget_category.category_type
        } if transaction.budget_category else None,
        'created_at': transaction.created_at.isoformat() if transaction.created_at else None
    })

@transactions_api_bp.route('/<int:transaction_id>', methods=['PUT'])
@login_required_api
def update_transaction(transaction_id):
    """Update a transaction"""
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Store original values for budget adjustment and audit logging
    original_amount = transaction.amount
    original_category_id = transaction.category_id
    original_type = transaction.transaction_type
    original_description = transaction.description
    
    # Update fields if provided
    if 'amount' in data:
        try:
            amount = parse_currency(data['amount'])
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
            transaction.amount = amount
        except (ValueError, InvalidOperation, TypeError) as e:
            current_app.logger.warning(f'Invalid amount provided by user {current_user.username}: {e}')
            return jsonify({'error': 'Invalid amount format'}), 400
    
    if 'description' in data:
        description = data['description'].strip()
        if not description:
            return jsonify({'error': 'Description cannot be empty'}), 400
        transaction.description = description
    
    if 'transaction_type' in data:
        if data['transaction_type'] not in ['income', 'expense', 'transfer']:
            return jsonify({'error': 'Invalid transaction type'}), 400
        transaction.transaction_type = data['transaction_type']
    
    if 'category_id' in data:
        if data['category_id']:
            category = BudgetCategory.query.filter_by(id=data['category_id'], user_id=current_user.id).first()
            if not category:
                return jsonify({'error': 'Category not found'}), 404
            transaction.category_id = data['category_id']
        else:
            transaction.category_id = None
    
    if 'currency' in data:
        transaction.currency = data['currency'] or current_user.default_currency
    
    if 'transaction_date' in data:
        try:
            transaction.transaction_date = datetime.fromisoformat(data['transaction_date']).date()
        except ValueError:
            return jsonify({'error': 'Invalid transaction date format'}), 400
    
    if 'payee' in data:
        transaction.payee = data['payee'].strip() or None
    
    if 'account' in data:
        transaction.account = data['account'] or 'checking'
    
    if 'tags' in data:
        transaction.tags = data['tags'].strip() or None
    
    if 'recurring' in data:
        transaction.recurring = bool(data['recurring'])
    
    if 'recurring_period' in data:
        if data['recurring_period'] and data['recurring_period'] not in ['daily', 'weekly', 'monthly', 'yearly']:
            return jsonify({'error': 'Invalid recurring period'}), 400
        transaction.recurring_period = data['recurring_period']
    
    try:
        # Adjust budget categories
        # Revert original impact
        if original_category_id and original_type == 'expense':
            original_category = BudgetCategory.query.get(original_category_id)
            if original_category:
                original_category.available_amount += original_amount
        
        # Apply new impact
        if transaction.category_id and transaction.transaction_type == 'expense':
            new_category = BudgetCategory.query.get(transaction.category_id)
            if new_category:
                new_category.available_amount -= transaction.amount
        
        db.session.commit()

        # Log audit event for transaction update
        log_audit_event(
            action='UPDATE',
            user_id=current_user.id,
            username=current_user.username,
            entity_type='Transaction',
            entity_id=transaction.id,
            old_value=f'{original_type}: {original_amount} - {original_description}',
            new_value=f'{transaction.transaction_type}: {transaction.amount} {transaction.currency} - {transaction.description}',
            ip_address=request.remote_addr
        )
        current_app.logger.info(f'Transaction updated: ID={transaction.id}, User={current_user.username}')

        return jsonify({
            'success': True,
            'message': 'Transaction updated successfully',
            'transaction': {
                'id': transaction.id,
                'amount': float(transaction.amount),
                'description': transaction.description,
                'transaction_type': transaction.transaction_type,
                'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None
            }
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f'Database error updating transaction {transaction_id} for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Database error occurred while updating transaction'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Unexpected error updating transaction {transaction_id} for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to update transaction'}), 500

@transactions_api_bp.route('/<int:transaction_id>', methods=['DELETE'])
@login_required_api
def delete_transaction(transaction_id):
    """Delete a transaction"""
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Store transaction details before deletion for audit log
    trans_details = f'{transaction.transaction_type}: {transaction.amount} {transaction.currency} - {transaction.description}'

    try:
        # Adjust budget category if needed
        if transaction.category_id and transaction.transaction_type == 'expense':
            category = BudgetCategory.query.get(transaction.category_id)
            if category:
                category.available_amount += transaction.amount

        db.session.delete(transaction)
        db.session.commit()

        # Log audit event for transaction deletion
        log_audit_event(
            action='DELETE',
            user_id=current_user.id,
            username=current_user.username,
            entity_type='Transaction',
            entity_id=transaction_id,
            old_value=trans_details,
            ip_address=request.remote_addr
        )
        current_app.logger.info(f'Transaction deleted: ID={transaction_id}, User={current_user.username}')

        return jsonify({
            'success': True,
            'message': 'Transaction deleted successfully'
        })
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f'Database error deleting transaction {transaction_id} for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Database error occurred while deleting transaction'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Unexpected error deleting transaction {transaction_id} for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to delete transaction'}), 500

@transactions_api_bp.route('/summary', methods=['GET'])
@login_required_api
def transaction_summary():
    """Get transaction summary statistics"""
    # Date range filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    if start_date:
        try:
            start_date = datetime.fromisoformat(start_date).date()
            query = query.filter(Transaction.transaction_date >= start_date)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format'}), 400
    
    if end_date:
        try:
            end_date = datetime.fromisoformat(end_date).date()
            query = query.filter(Transaction.transaction_date <= end_date)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format'}), 400
    
    # Calculate totals
    income_total = query.filter_by(transaction_type='income').with_entities(func.sum(Transaction.amount)).scalar() or Decimal('0')
    expense_total = query.filter_by(transaction_type='expense').with_entities(func.sum(Transaction.amount)).scalar() or Decimal('0')
    transfer_total = query.filter_by(transaction_type='transfer').with_entities(func.sum(Transaction.amount)).scalar() or Decimal('0')
    
    # Transaction counts
    income_count = query.filter_by(transaction_type='income').count()
    expense_count = query.filter_by(transaction_type='expense').count()
    transfer_count = query.filter_by(transaction_type='transfer').count()
    
    # Category breakdown for expenses
    category_breakdown = db.session.query(
        BudgetCategory.name,
        BudgetCategory.color,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'expense'
    )
    
    if start_date:
        category_breakdown = category_breakdown.filter(Transaction.transaction_date >= start_date)
    if end_date:
        category_breakdown = category_breakdown.filter(Transaction.transaction_date <= end_date)
    
    category_breakdown = category_breakdown.group_by(BudgetCategory.id).all()
    
    categories = []
    for cat_name, cat_color, total, count in category_breakdown:
        categories.append({
            'name': cat_name,
            'color': cat_color,
            'total': float(total),
            'count': count
        })
    
    return jsonify({
        'totals': {
            'income': float(income_total),
            'expenses': float(expense_total),
            'transfers': float(transfer_total),
            'net': float(income_total - expense_total)
        },
        'counts': {
            'income': income_count,
            'expenses': expense_count,
            'transfers': transfer_count,
            'total': income_count + expense_count + transfer_count
        },
        'category_breakdown': categories,
        'period': {
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        }
    })

@transactions_api_bp.route('/bulk', methods=['POST'])
@login_required_api
def create_bulk_transactions():
    """Create multiple transactions at once"""
    data = request.get_json()
    
    if not data or 'transactions' not in data:
        return jsonify({'error': 'No transaction data provided'}), 400
    
    transactions_data = data['transactions']
    if not isinstance(transactions_data, list):
        return jsonify({'error': 'Transactions must be a list'}), 400
    
    if len(transactions_data) > 100:  # Limit bulk operations
        return jsonify({'error': 'Maximum 100 transactions per bulk operation'}), 400
    
    created_transactions = []
    errors = []
    
    for i, trans_data in enumerate(transactions_data):
        try:
            # Validate required fields
            if not trans_data.get('amount') or not trans_data.get('description') or not trans_data.get('transaction_type'):
                errors.append(f'Transaction {i+1}: Missing required fields')
                continue
            
            amount = parse_currency(trans_data['amount'])
            if amount <= 0:
                errors.append(f'Transaction {i+1}: Invalid amount')
                continue
            
            # Create transaction
            transaction = Transaction(
                user_id=current_user.id,
                category_id=trans_data.get('category_id'),
                amount=amount,
                currency=trans_data.get('currency', current_user.default_currency),
                description=trans_data['description'].strip(),
                transaction_type=trans_data['transaction_type'],
                transaction_date=datetime.fromisoformat(trans_data['transaction_date']).date() if trans_data.get('transaction_date') else date.today(),
                payee=trans_data.get('payee', '').strip() or None,
                account=trans_data.get('account', 'checking'),
                tags=trans_data.get('tags', '').strip() or None
            )
            
            db.session.add(transaction)
            created_transactions.append(transaction)
            
        except Exception as e:
            errors.append(f'Transaction {i+1}: {str(e)}')
    
    if errors and not created_transactions:
        return jsonify({'errors': errors}), 400
    
    try:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {len(created_transactions)} transactions',
            'created_count': len(created_transactions),
            'errors': errors if errors else None
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create transactions'}), 500

@transactions_api_bp.route('/recurring', methods=['GET'])
@login_required_api
def get_recurring_transactions():
    """Get all recurring transactions for the current user"""
    recurring_transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        recurring=True
    ).order_by(desc(Transaction.created_at)).all()

    result = []
    for trans in recurring_transactions:
        result.append({
            'id': trans.id,
            'amount': float(trans.amount),
            'currency': trans.currency,
            'description': trans.description,
            'transaction_type': trans.transaction_type,
            'transaction_date': trans.transaction_date.isoformat() if trans.transaction_date else None,
            'payee': trans.payee,
            'account': trans.account,
            'tags': trans.tags,
            'recurring_period': trans.recurring_period,
            'category': {
                'id': trans.budget_category.id,
                'name': trans.budget_category.name,
                'color': trans.budget_category.color
            } if trans.budget_category else None,
            'created_at': trans.created_at.isoformat() if trans.created_at else None
        })

    return jsonify({'recurring_transactions': result})

@transactions_api_bp.route('/recurring/summary', methods=['GET'])
@login_required_api
def get_recurring_summary():
    """Get summary of recurring transactions"""
    from services.recurring_service import recurring_service

    summary = recurring_service.get_recurring_transaction_summary(current_user.id)

    return jsonify({
        'total': summary['total'],
        'by_period': summary['by_period'],
        'by_type': summary['by_type'],
        'total_monthly_impact': float(summary['total_monthly_impact'])
    })

@transactions_api_bp.route('/recurring/upcoming', methods=['GET'])
@login_required_api
def get_upcoming_recurring():
    """Get upcoming recurring transaction occurrences"""
    days_ahead = request.args.get('days', 30, type=int)
    days_ahead = min(days_ahead, 365)  # Max 1 year

    from services.recurring_service import recurring_service

    upcoming = recurring_service.get_upcoming_occurrences(current_user.id, days_ahead)

    return jsonify({'upcoming_occurrences': upcoming})

@transactions_api_bp.route('/recurring/process', methods=['POST'])
@login_required_api
def process_recurring_transactions():
    """Process recurring transactions for the current user (create due occurrences)"""
    dry_run = request.args.get('dry_run', 'false').lower() == 'true'

    from services.recurring_service import recurring_service

    # Get only the user's recurring transactions
    user_recurring = Transaction.query.filter_by(
        user_id=current_user.id,
        recurring=True
    ).all()

    created_count = 0
    created_transactions = []
    errors = []

    try:
        for template in user_recurring:
            if recurring_service.should_create_occurrence(
                template.transaction_date,
                template.recurring_period
            ):
                if not dry_run:
                    new_trans = recurring_service.create_recurring_occurrence(template)
                    created_transactions.append({
                        'id': new_trans.id,
                        'description': new_trans.description,
                        'amount': float(new_trans.amount),
                        'date': new_trans.transaction_date.isoformat()
                    })
                    created_count += 1
                else:
                    # Dry run - just report what would be created
                    next_date = recurring_service.get_next_occurrence_date(
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

        if not dry_run:
            db.session.commit()

            # Log audit event
            log_audit_event(
                'recurring_transactions_processed',
                user_id=current_user.id,
                details=f'Created {created_count} recurring transaction occurrences'
            )
            current_app.logger.info(f'Processed recurring transactions for user {current_user.id}: {created_count} created')

        return jsonify({
            'success': True,
            'message': f'{"Would create" if dry_run else "Created"} {created_count} transactions',
            'created_count': created_count,
            'created_transactions': created_transactions,
            'dry_run': dry_run
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error processing recurring transactions: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to process recurring transactions'}), 500

@transactions_api_bp.route('/recurring/<int:transaction_id>/stop', methods=['POST'])
@login_required_api
def stop_recurring_transaction(transaction_id):
    """Stop a recurring transaction (mark as non-recurring)"""
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id,
        recurring=True
    ).first()

    if not transaction:
        return jsonify({'error': 'Recurring transaction not found'}), 404

    try:
        transaction.recurring = False
        transaction.recurring_period = None

        db.session.commit()

        # Log audit event
        log_audit_event(
            'recurring_transaction_stopped',
            user_id=current_user.id,
            details=f'Stopped recurring transaction: {transaction.description}'
        )

        return jsonify({
            'success': True,
            'message': f'Stopped recurring transaction: {transaction.description}'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error stopping recurring transaction: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to stop recurring transaction'}), 500