from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, BudgetCategory, Transaction
from utils import login_required_api, parse_currency, format_currency, get_budget_health_status
from decimal import Decimal
from sqlalchemy import func

budget_api_bp = Blueprint('budget_api', __name__)

@budget_api_bp.route('/categories', methods=['GET'])
@login_required_api
def get_categories():
    """Get all budget categories for the current user"""
    categories = BudgetCategory.query.filter_by(user_id=current_user.id)\
        .order_by(BudgetCategory.category_type, BudgetCategory.name).all()
    
    result = []
    for category in categories:
        # Update available amount based on transactions
        category.update_available_amount()
        
        result.append({
            'id': category.id,
            'name': category.name,
            'allocated_amount': float(category.allocated_amount),
            'available_amount': float(category.available_amount),
            'spent_amount': float(category.allocated_amount - category.available_amount),
            'category_type': category.category_type,
            'color': category.color,
            'health_status': get_budget_health_status(category.available_amount, category.allocated_amount),
            'created_at': category.created_at.isoformat() if category.created_at else None
        })
    
    db.session.commit()  # Save updated available amounts
    
    return jsonify({'categories': result})

@budget_api_bp.route('/categories', methods=['POST'])
@login_required_api
def create_category():
    """Create a new budget category"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name', '').strip()
    allocated_amount = data.get('allocated_amount', 0)
    category_type = data.get('category_type', 'expense')
    color = data.get('color', '#007bff')
    
    # Validation
    if not name:
        return jsonify({'error': 'Category name is required'}), 400
    
    if len(name) > 100:
        return jsonify({'error': 'Category name too long (max 100 characters)'}), 400
    
    # Check if category already exists
    existing = BudgetCategory.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({'error': 'Category with this name already exists'}), 400
    
    try:
        allocated_amount = parse_currency(allocated_amount)
        if allocated_amount < 0:
            return jsonify({'error': 'Allocated amount cannot be negative'}), 400
    except:
        return jsonify({'error': 'Invalid allocated amount'}), 400
    
    if category_type not in ['income', 'expense', 'saving']:
        return jsonify({'error': 'Invalid category type'}), 400
    
    # Validate color format
    if not color.startswith('#') or len(color) != 7:
        color = '#007bff'  # Default color
    
    try:
        category = BudgetCategory(
            user_id=current_user.id,
            name=name,
            allocated_amount=allocated_amount,
            available_amount=allocated_amount,
            category_type=category_type,
            color=color
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category created successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'allocated_amount': float(category.allocated_amount),
                'available_amount': float(category.available_amount),
                'category_type': category.category_type,
                'color': category.color
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create category'}), 500

@budget_api_bp.route('/categories/<int:category_id>', methods=['GET'])
@login_required_api
def get_category(category_id):
    """Get a specific budget category"""
    category = BudgetCategory.query.filter_by(id=category_id, user_id=current_user.id).first()
    
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    # Update available amount
    category.update_available_amount()
    db.session.commit()
    
    return jsonify({
        'id': category.id,
        'name': category.name,
        'allocated_amount': float(category.allocated_amount),
        'available_amount': float(category.available_amount),
        'spent_amount': float(category.allocated_amount - category.available_amount),
        'category_type': category.category_type,
        'color': category.color,
        'health_status': get_budget_health_status(category.available_amount, category.allocated_amount),
        'transaction_count': len(category.transactions),
        'created_at': category.created_at.isoformat() if category.created_at else None
    })

@budget_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@login_required_api
def update_category(category_id):
    """Update a budget category"""
    category = BudgetCategory.query.filter_by(id=category_id, user_id=current_user.id).first()
    
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update fields if provided
    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Category name cannot be empty'}), 400
        
        # Check for duplicate name (excluding current category)
        existing = BudgetCategory.query.filter_by(user_id=current_user.id, name=name)\
            .filter(BudgetCategory.id != category_id).first()
        if existing:
            return jsonify({'error': 'Category with this name already exists'}), 400
        
        category.name = name
    
    if 'allocated_amount' in data:
        try:
            allocated_amount = parse_currency(data['allocated_amount'])
            if allocated_amount < 0:
                return jsonify({'error': 'Allocated amount cannot be negative'}), 400
            
            # Calculate the difference to adjust available amount
            difference = allocated_amount - category.allocated_amount
            category.allocated_amount = allocated_amount
            category.available_amount += difference
            
        except:
            return jsonify({'error': 'Invalid allocated amount'}), 400
    
    if 'category_type' in data:
        if data['category_type'] not in ['income', 'expense', 'saving']:
            return jsonify({'error': 'Invalid category type'}), 400
        category.category_type = data['category_type']
    
    if 'color' in data:
        color = data['color']
        if color and (not color.startswith('#') or len(color) != 7):
            return jsonify({'error': 'Invalid color format'}), 400
        category.color = color or '#007bff'
    
    try:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category updated successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'allocated_amount': float(category.allocated_amount),
                'available_amount': float(category.available_amount),
                'category_type': category.category_type,
                'color': category.color
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update category'}), 500

@budget_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@login_required_api
def delete_category(category_id):
    """Delete a budget category"""
    category = BudgetCategory.query.filter_by(id=category_id, user_id=current_user.id).first()
    
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    # Check if category has transactions
    transaction_count = Transaction.query.filter_by(category_id=category_id).count()
    
    if transaction_count > 0:
        return jsonify({
            'error': f'Cannot delete category with {transaction_count} associated transactions'
        }), 400
    
    try:
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete category'}), 500

@budget_api_bp.route('/summary', methods=['GET'])
@login_required_api
def budget_summary():
    """Get budget summary statistics"""
    categories = BudgetCategory.query.filter_by(user_id=current_user.id).all()
    
    # Calculate totals by category type
    totals = {
        'income': {'allocated': Decimal('0'), 'available': Decimal('0')},
        'expense': {'allocated': Decimal('0'), 'available': Decimal('0')},
        'saving': {'allocated': Decimal('0'), 'available': Decimal('0')}
    }
    
    category_health = {'danger': 0, 'warning': 0, 'success': 0}
    
    for category in categories:
        category.update_available_amount()
        
        cat_type = category.category_type
        totals[cat_type]['allocated'] += category.allocated_amount
        totals[cat_type]['available'] += category.available_amount
        
        # Count health status for expense categories
        if cat_type == 'expense':
            health = get_budget_health_status(category.available_amount, category.allocated_amount)
            category_health[health] += 1
    
    db.session.commit()
    
    # Calculate overall budget health
    total_expense_allocated = totals['expense']['allocated']
    total_expense_available = totals['expense']['available']
    total_expense_spent = total_expense_allocated - total_expense_available
    
    budget_utilization = 0
    if total_expense_allocated > 0:
        budget_utilization = (float(total_expense_spent) / float(total_expense_allocated)) * 100
    
    return jsonify({
        'totals': {
            'income': {
                'allocated': float(totals['income']['allocated']),
                'available': float(totals['income']['available'])
            },
            'expense': {
                'allocated': float(totals['expense']['allocated']),
                'available': float(totals['expense']['available']),
                'spent': float(total_expense_spent)
            },
            'saving': {
                'allocated': float(totals['saving']['allocated']),
                'available': float(totals['saving']['available'])
            }
        },
        'budget_utilization': round(budget_utilization, 1),
        'category_health': category_health,
        'net_budget': float(totals['income']['allocated'] - totals['expense']['allocated'] - totals['saving']['allocated'])
    })

@budget_api_bp.route('/transfer', methods=['POST'])
@login_required_api
def transfer_budget():
    """Transfer budget amount between categories"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    from_category_id = data.get('from_category_id')
    to_category_id = data.get('to_category_id')
    amount = data.get('amount', 0)
    
    if not from_category_id or not to_category_id:
        return jsonify({'error': 'Both source and destination categories are required'}), 400
    
    if from_category_id == to_category_id:
        return jsonify({'error': 'Cannot transfer to the same category'}), 400
    
    try:
        amount = parse_currency(amount)
        if amount <= 0:
            return jsonify({'error': 'Transfer amount must be positive'}), 400
    except:
        return jsonify({'error': 'Invalid transfer amount'}), 400
    
    # Get categories
    from_category = BudgetCategory.query.filter_by(id=from_category_id, user_id=current_user.id).first()
    to_category = BudgetCategory.query.filter_by(id=to_category_id, user_id=current_user.id).first()
    
    if not from_category or not to_category:
        return jsonify({'error': 'One or both categories not found'}), 404
    
    # Update available amounts
    from_category.update_available_amount()
    to_category.update_available_amount()
    
    # Check if source category has enough available budget
    if from_category.available_amount < amount:
        return jsonify({
            'error': f'Insufficient budget in {from_category.name}. Available: {format_currency(from_category.available_amount)}'
        }), 400
    
    try:
        # Perform the transfer
        from_category.available_amount -= amount
        from_category.allocated_amount -= amount
        
        to_category.available_amount += amount
        to_category.allocated_amount += amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully transferred {format_currency(amount)} from {from_category.name} to {to_category.name}',
            'from_category': {
                'id': from_category.id,
                'available_amount': float(from_category.available_amount),
                'allocated_amount': float(from_category.allocated_amount)
            },
            'to_category': {
                'id': to_category.id,
                'available_amount': float(to_category.available_amount),
                'allocated_amount': float(to_category.allocated_amount)
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to transfer budget'}), 500