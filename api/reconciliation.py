from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, AccountReconciliation, ReconciliationItem, Transaction
from utils import login_required_api, parse_currency
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import desc

reconciliation_api_bp = Blueprint('reconciliation_api', __name__)

@reconciliation_api_bp.route('/', methods=['GET'])
@login_required_api
def get_reconciliations():
    """Get all reconciliations for the current user"""
    account_filter = request.args.get('account')

    query = AccountReconciliation.query.filter_by(user_id=current_user.id)

    if account_filter:
        query = query.filter_by(account=account_filter)

    reconciliations = query.order_by(desc(AccountReconciliation.statement_date)).all()

    result = []
    for recon in reconciliations:
        result.append({
            'id': recon.id,
            'account': recon.account,
            'statement_date': recon.statement_date.isoformat(),
            'statement_balance': float(recon.statement_balance),
            'book_balance': float(recon.book_balance) if recon.book_balance else 0,
            'difference': float(recon.difference) if recon.difference else 0,
            'reconciled': recon.reconciled,
            'reconciled_at': recon.reconciled_at.isoformat() if recon.reconciled_at else None,
            'created_at': recon.created_at.isoformat() if recon.created_at else None,
            'items_count': len(recon.items),
            'cleared_count': sum(1 for item in recon.items if item.cleared)
        })

    return jsonify({'reconciliations': result})

@reconciliation_api_bp.route('/<int:reconciliation_id>', methods=['GET'])
@login_required_api
def get_reconciliation(reconciliation_id):
    """Get a specific reconciliation with its items"""
    recon = AccountReconciliation.query.filter_by(
        id=reconciliation_id,
        user_id=current_user.id
    ).first()

    if not recon:
        return jsonify({'error': 'Reconciliation not found'}), 404

    items = []
    for item in recon.items:
        trans = item.transaction
        items.append({
            'id': item.id,
            'transaction_id': item.transaction_id,
            'cleared': item.cleared,
            'notes': item.notes,
            'transaction': {
                'description': trans.description,
                'amount': float(trans.amount),
                'transaction_type': trans.transaction_type,
                'transaction_date': trans.transaction_date.isoformat() if trans.transaction_date else None,
                'payee': trans.payee,
                'category': trans.budget_category.name if trans.budget_category else None
            }
        })

    return jsonify({
        'id': recon.id,
        'account': recon.account,
        'statement_date': recon.statement_date.isoformat(),
        'statement_balance': float(recon.statement_balance),
        'book_balance': float(recon.book_balance) if recon.book_balance else 0,
        'difference': float(recon.difference) if recon.difference else 0,
        'reconciled': recon.reconciled,
        'reconciled_at': recon.reconciled_at.isoformat() if recon.reconciled_at else None,
        'notes': recon.notes,
        'items': items
    })

@reconciliation_api_bp.route('/', methods=['POST'])
@login_required_api
def create_reconciliation():
    """Create a new reconciliation"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    account = data.get('account')
    statement_date = data.get('statement_date')
    statement_balance = data.get('statement_balance')

    # Validation
    if not account or not statement_date or statement_balance is None:
        return jsonify({'error': 'Account, statement date, and balance are required'}), 400

    if account not in ['checking', 'savings', 'credit', 'cash']:
        return jsonify({'error': 'Invalid account type'}), 400

    try:
        statement_date = datetime.fromisoformat(statement_date).date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    try:
        statement_balance = parse_currency(statement_balance)
    except:
        return jsonify({'error': 'Invalid statement balance'}), 400

    try:
        # Create reconciliation
        recon = AccountReconciliation(
            user_id=current_user.id,
            account=account,
            statement_date=statement_date,
            statement_balance=statement_balance,
            book_balance=Decimal('0'),
            difference=statement_balance,
            notes=data.get('notes', '')
        )

        db.session.add(recon)
        db.session.flush()

        # Get unreconciled transactions for this account
        # Transactions up to and including the statement date
        transactions = Transaction.query.filter_by(
            user_id=current_user.id,
            account=account
        ).filter(
            Transaction.transaction_date <= statement_date
        ).all()

        # Add all transactions as reconciliation items
        for trans in transactions:
            item = ReconciliationItem(
                reconciliation_id=recon.id,
                transaction_id=trans.id,
                cleared=False
            )
            db.session.add(item)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Reconciliation created for {account}',
            'reconciliation': {
                'id': recon.id,
                'account': recon.account,
                'statement_date': recon.statement_date.isoformat(),
                'transactions_count': len(transactions)
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating reconciliation: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to create reconciliation'}), 500

@reconciliation_api_bp.route('/<int:reconciliation_id>/items/<int:item_id>/toggle', methods=['POST'])
@login_required_api
def toggle_reconciliation_item(reconciliation_id, item_id):
    """Toggle cleared status of a reconciliation item"""
    recon = AccountReconciliation.query.filter_by(
        id=reconciliation_id,
        user_id=current_user.id
    ).first()

    if not recon:
        return jsonify({'error': 'Reconciliation not found'}), 404

    if recon.reconciled:
        return jsonify({'error': 'Cannot modify completed reconciliation'}), 400

    item = ReconciliationItem.query.filter_by(
        id=item_id,
        reconciliation_id=reconciliation_id
    ).first()

    if not item:
        return jsonify({'error': 'Item not found'}), 404

    try:
        # Toggle cleared status
        item.cleared = not item.cleared

        # Recalculate balances
        recon.calculate_balances()

        db.session.commit()

        return jsonify({
            'success': True,
            'cleared': item.cleared,
            'book_balance': float(recon.book_balance),
            'difference': float(recon.difference),
            'reconciled': recon.reconciled
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error toggling item: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to update item'}), 500

@reconciliation_api_bp.route('/<int:reconciliation_id>/complete', methods=['POST'])
@login_required_api
def complete_reconciliation(reconciliation_id):
    """Mark reconciliation as complete"""
    recon = AccountReconciliation.query.filter_by(
        id=reconciliation_id,
        user_id=current_user.id
    ).first()

    if not recon:
        return jsonify({'error': 'Reconciliation not found'}), 404

    if recon.reconciled:
        return jsonify({'error': 'Reconciliation already completed'}), 400

    try:
        # Recalculate balances one more time
        recon.calculate_balances()

        # Check if balanced
        if recon.difference != 0:
            return jsonify({
                'error': f'Cannot complete: Difference of ${float(recon.difference):.2f} remains. Please review cleared items.',
                'difference': float(recon.difference)
            }), 400

        # Mark as reconciled
        recon.reconciled = True
        recon.reconciled_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Reconciliation completed successfully!',
            'reconciliation': {
                'id': recon.id,
                'reconciled': True,
                'reconciled_at': recon.reconciled_at.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error completing reconciliation: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to complete reconciliation'}), 500

@reconciliation_api_bp.route('/<int:reconciliation_id>', methods=['DELETE'])
@login_required_api
def delete_reconciliation(reconciliation_id):
    """Delete a reconciliation"""
    recon = AccountReconciliation.query.filter_by(
        id=reconciliation_id,
        user_id=current_user.id
    ).first()

    if not recon:
        return jsonify({'error': 'Reconciliation not found'}), 404

    try:
        db.session.delete(recon)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Reconciliation deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting reconciliation: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to delete reconciliation'}), 500
