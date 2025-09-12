from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Milestone
from utils import login_required_api, parse_currency, format_currency
from decimal import Decimal
from datetime import datetime, date

milestones_api_bp = Blueprint('milestones_api', __name__)

@milestones_api_bp.route('/', methods=['GET'])
@login_required_api
def get_milestones():
    """Get all milestones for the current user"""
    status_filter = request.args.get('status')  # 'completed', 'active', 'overdue'
    category_filter = request.args.get('category')
    
    query = Milestone.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if status_filter == 'completed':
        query = query.filter_by(completed=True)
    elif status_filter == 'active':
        query = query.filter_by(completed=False)
    elif status_filter == 'overdue':
        query = query.filter(
            Milestone.completed == False,
            Milestone.target_date < date.today()
        )
    
    if category_filter:
        query = query.filter_by(category=category_filter)
    
    milestones = query.order_by(Milestone.target_date.asc().nullslast(), 
                               Milestone.created_at.desc()).all()
    
    result = []
    for milestone in milestones:
        result.append({
            'id': milestone.id,
            'name': milestone.name,
            'description': milestone.description,
            'target_amount': float(milestone.target_amount),
            'current_amount': float(milestone.current_amount),
            'progress_percentage': milestone.progress_percentage,
            'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
            'completed': milestone.completed,
            'completed_date': milestone.completed_date.isoformat() if milestone.completed_date else None,
            'category': milestone.category,
            'is_overdue': milestone.is_overdue,
            'days_remaining': (milestone.target_date - date.today()).days if milestone.target_date and not milestone.completed else None,
            'created_at': milestone.created_at.isoformat() if milestone.created_at else None
        })
    
    return jsonify({'milestones': result})

@milestones_api_bp.route('/', methods=['POST'])
@login_required_api
def create_milestone():
    """Create a new milestone"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    target_amount = data.get('target_amount')
    current_amount = data.get('current_amount', 0)
    target_date = data.get('target_date')
    category = data.get('category', 'saving')
    
    # Validation
    if not name:
        return jsonify({'error': 'Milestone name is required'}), 400
    
    if len(name) > 100:
        return jsonify({'error': 'Milestone name too long (max 100 characters)'}), 400
    
    try:
        target_amount = parse_currency(target_amount)
        if target_amount <= 0:
            return jsonify({'error': 'Target amount must be positive'}), 400
    except:
        return jsonify({'error': 'Invalid target amount'}), 400
    
    try:
        current_amount = parse_currency(current_amount)
        if current_amount < 0:
            return jsonify({'error': 'Current amount cannot be negative'}), 400
    except:
        return jsonify({'error': 'Invalid current amount'}), 400
    
    if current_amount > target_amount:
        return jsonify({'error': 'Current amount cannot exceed target amount'}), 400
    
    if target_date:
        try:
            target_date = datetime.fromisoformat(target_date).date()
            if target_date <= date.today():
                return jsonify({'error': 'Target date must be in the future'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid target date format'}), 400
    
    if category not in ['saving', 'debt', 'investment']:
        return jsonify({'error': 'Invalid category'}), 400
    
    # Check for duplicate names
    existing = Milestone.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({'error': 'Milestone with this name already exists'}), 400
    
    try:
        milestone = Milestone(
            user_id=current_user.id,
            name=name,
            description=description or None,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            category=category
        )
        
        db.session.add(milestone)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Milestone created successfully',
            'milestone': {
                'id': milestone.id,
                'name': milestone.name,
                'description': milestone.description,
                'target_amount': float(milestone.target_amount),
                'current_amount': float(milestone.current_amount),
                'progress_percentage': milestone.progress_percentage,
                'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
                'category': milestone.category
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create milestone'}), 500

@milestones_api_bp.route('/<int:milestone_id>', methods=['GET'])
@login_required_api
def get_milestone(milestone_id):
    """Get a specific milestone"""
    milestone = Milestone.query.filter_by(id=milestone_id, user_id=current_user.id).first()
    
    if not milestone:
        return jsonify({'error': 'Milestone not found'}), 404
    
    return jsonify({
        'id': milestone.id,
        'name': milestone.name,
        'description': milestone.description,
        'target_amount': float(milestone.target_amount),
        'current_amount': float(milestone.current_amount),
        'progress_percentage': milestone.progress_percentage,
        'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
        'completed': milestone.completed,
        'completed_date': milestone.completed_date.isoformat() if milestone.completed_date else None,
        'category': milestone.category,
        'is_overdue': milestone.is_overdue,
        'days_remaining': (milestone.target_date - date.today()).days if milestone.target_date and not milestone.completed else None,
        'created_at': milestone.created_at.isoformat() if milestone.created_at else None
    })

@milestones_api_bp.route('/<int:milestone_id>', methods=['PUT'])
@login_required_api
def update_milestone(milestone_id):
    """Update a milestone"""
    milestone = Milestone.query.filter_by(id=milestone_id, user_id=current_user.id).first()
    
    if not milestone:
        return jsonify({'error': 'Milestone not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update fields if provided
    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Milestone name cannot be empty'}), 400
        
        # Check for duplicate name (excluding current milestone)
        existing = Milestone.query.filter_by(user_id=current_user.id, name=name)\
            .filter(Milestone.id != milestone_id).first()
        if existing:
            return jsonify({'error': 'Milestone with this name already exists'}), 400
        
        milestone.name = name
    
    if 'description' in data:
        milestone.description = data['description'].strip() or None
    
    if 'target_amount' in data:
        try:
            target_amount = parse_currency(data['target_amount'])
            if target_amount <= 0:
                return jsonify({'error': 'Target amount must be positive'}), 400
            
            if target_amount < milestone.current_amount:
                return jsonify({'error': 'Target amount cannot be less than current amount'}), 400
            
            milestone.target_amount = target_amount
        except:
            return jsonify({'error': 'Invalid target amount'}), 400
    
    if 'current_amount' in data:
        try:
            current_amount = parse_currency(data['current_amount'])
            if current_amount < 0:
                return jsonify({'error': 'Current amount cannot be negative'}), 400
            
            if current_amount > milestone.target_amount:
                return jsonify({'error': 'Current amount cannot exceed target amount'}), 400
            
            milestone.current_amount = current_amount
            
            # Auto-complete if current amount reaches target
            if current_amount >= milestone.target_amount and not milestone.completed:
                milestone.completed = True
                milestone.completed_date = date.today()
            elif current_amount < milestone.target_amount and milestone.completed:
                milestone.completed = False
                milestone.completed_date = None
                
        except:
            return jsonify({'error': 'Invalid current amount'}), 400
    
    if 'target_date' in data:
        if data['target_date']:
            try:
                target_date = datetime.fromisoformat(data['target_date']).date()
                if target_date <= date.today() and not milestone.completed:
                    return jsonify({'error': 'Target date must be in the future for active milestones'}), 400
                milestone.target_date = target_date
            except ValueError:
                return jsonify({'error': 'Invalid target date format'}), 400
        else:
            milestone.target_date = None
    
    if 'category' in data:
        if data['category'] not in ['saving', 'debt', 'investment']:
            return jsonify({'error': 'Invalid category'}), 400
        milestone.category = data['category']
    
    if 'completed' in data:
        completed = bool(data['completed'])
        if completed and not milestone.completed:
            milestone.completed = True
            milestone.completed_date = date.today()
        elif not completed and milestone.completed:
            milestone.completed = False
            milestone.completed_date = None
    
    try:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Milestone updated successfully',
            'milestone': {
                'id': milestone.id,
                'name': milestone.name,
                'target_amount': float(milestone.target_amount),
                'current_amount': float(milestone.current_amount),
                'progress_percentage': milestone.progress_percentage,
                'completed': milestone.completed,
                'target_date': milestone.target_date.isoformat() if milestone.target_date else None
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update milestone'}), 500

@milestones_api_bp.route('/<int:milestone_id>', methods=['DELETE'])
@login_required_api
def delete_milestone(milestone_id):
    """Delete a milestone"""
    milestone = Milestone.query.filter_by(id=milestone_id, user_id=current_user.id).first()
    
    if not milestone:
        return jsonify({'error': 'Milestone not found'}), 404
    
    try:
        db.session.delete(milestone)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Milestone deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete milestone'}), 500

@milestones_api_bp.route('/<int:milestone_id>/add-progress', methods=['POST'])
@login_required_api
def add_progress(milestone_id):
    """Add progress to a milestone"""
    milestone = Milestone.query.filter_by(id=milestone_id, user_id=current_user.id).first()
    
    if not milestone:
        return jsonify({'error': 'Milestone not found'}), 404
    
    if milestone.completed:
        return jsonify({'error': 'Cannot add progress to completed milestone'}), 400
    
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'error': 'Amount is required'}), 400
    
    try:
        amount = parse_currency(data['amount'])
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
    except:
        return jsonify({'error': 'Invalid amount'}), 400
    
    new_current_amount = milestone.current_amount + amount
    
    if new_current_amount > milestone.target_amount:
        return jsonify({
            'error': f'Adding {format_currency(amount)} would exceed target amount by {format_currency(new_current_amount - milestone.target_amount)}'
        }), 400
    
    try:
        milestone.current_amount = new_current_amount
        
        # Check if milestone is now completed
        if milestone.current_amount >= milestone.target_amount:
            milestone.completed = True
            milestone.completed_date = date.today()
        
        db.session.commit()
        
        message = f'Added {format_currency(amount)} to {milestone.name}'
        if milestone.completed:
            message += '. Congratulations! Milestone completed!'
        
        return jsonify({
            'success': True,
            'message': message,
            'milestone': {
                'id': milestone.id,
                'current_amount': float(milestone.current_amount),
                'progress_percentage': milestone.progress_percentage,
                'completed': milestone.completed,
                'completed_date': milestone.completed_date.isoformat() if milestone.completed_date else None
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update milestone progress'}), 500

@milestones_api_bp.route('/<int:milestone_id>/complete', methods=['POST'])
@login_required_api
def complete_milestone(milestone_id):
    """Mark a milestone as completed"""
    milestone = Milestone.query.filter_by(id=milestone_id, user_id=current_user.id).first()
    
    if not milestone:
        return jsonify({'error': 'Milestone not found'}), 404
    
    if milestone.completed:
        return jsonify({'error': 'Milestone is already completed'}), 400
    
    try:
        milestone.completed = True
        milestone.completed_date = date.today()
        
        # Optionally set current amount to target amount
        data = request.get_json()
        if data and data.get('set_target_amount', False):
            milestone.current_amount = milestone.target_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Milestone "{milestone.name}" marked as completed!',
            'milestone': {
                'id': milestone.id,
                'completed': milestone.completed,
                'completed_date': milestone.completed_date.isoformat(),
                'current_amount': float(milestone.current_amount),
                'progress_percentage': milestone.progress_percentage
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to complete milestone'}), 500

@milestones_api_bp.route('/summary', methods=['GET'])
@login_required_api
def milestones_summary():
    """Get milestone summary statistics"""
    milestones = Milestone.query.filter_by(user_id=current_user.id).all()
    
    total_count = len(milestones)
    completed_count = sum(1 for m in milestones if m.completed)
    active_count = total_count - completed_count
    overdue_count = sum(1 for m in milestones if m.is_overdue)
    
    # Calculate totals by category
    category_totals = {}
    for milestone in milestones:
        cat = milestone.category
        if cat not in category_totals:
            category_totals[cat] = {
                'count': 0,
                'target_total': Decimal('0'),
                'current_total': Decimal('0'),
                'completed_count': 0
            }
        
        category_totals[cat]['count'] += 1
        category_totals[cat]['target_total'] += milestone.target_amount
        category_totals[cat]['current_total'] += milestone.current_amount
        if milestone.completed:
            category_totals[cat]['completed_count'] += 1
    
    # Convert to serializable format
    categories = {}
    for cat, data in category_totals.items():
        categories[cat] = {
            'count': data['count'],
            'target_total': float(data['target_total']),
            'current_total': float(data['current_total']),
            'completed_count': data['completed_count'],
            'progress_percentage': (float(data['current_total']) / float(data['target_total']) * 100) if data['target_total'] > 0 else 0
        }
    
    # Overall progress
    total_target = sum(m.target_amount for m in milestones)
    total_current = sum(m.current_amount for m in milestones)
    overall_progress = (float(total_current) / float(total_target) * 100) if total_target > 0 else 0
    
    return jsonify({
        'totals': {
            'count': total_count,
            'completed': completed_count,
            'active': active_count,
            'overdue': overdue_count,
            'target_amount': float(total_target),
            'current_amount': float(total_current),
            'overall_progress': round(overall_progress, 1)
        },
        'categories': categories,
        'completion_rate': round((completed_count / total_count * 100) if total_count > 0 else 0, 1)
    })