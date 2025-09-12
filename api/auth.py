from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from utils import validate_email
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        if request.is_json:
            # Handle JSON API request
            data = request.get_json()
            username_or_email = data.get('username', '').strip()
            password = data.get('password', '')
            remember_me = data.get('remember_me', False)
        else:
            # Handle form request
            username_or_email = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember_me = bool(request.form.get('remember_me'))
        
        if not username_or_email or not password:
            error_msg = 'Username/email and password are required'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth.html')
        
        # Find user by username or email
        user = None
        if validate_email(username_or_email):
            user = User.query.filter_by(email=username_or_email).first()
        else:
            user = User.query.filter_by(username=username_or_email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            next_page = request.args.get('next')
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'redirect': next_page or url_for('main.dashboard')
                })
            
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            error_msg = 'Invalid username/email or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
    
    return render_template('auth.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        if request.is_json:
            # Handle JSON API request
            data = request.get_json()
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
        else:
            # Handle form request
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long')
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('Username can only contain letters, numbers, and underscores')
        
        if not email or not validate_email(email):
            errors.append('Please enter a valid email address')
        
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long')
        
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                errors.append('Username already exists')
            if existing_user.email == email:
                errors.append('Email already exists')
        
        if errors:
            if request.is_json:
                return jsonify({'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('auth.html', 
                                 username=username, 
                                 email=email,
                                 show_register=True)
        
        # Create new user
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # Log in the new user
            login_user(user)
            
            success_msg = f'Welcome {username}! Your account has been created successfully.'
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': success_msg,
                    'redirect': url_for('main.dashboard')
                })
            
            flash(success_msg, 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = 'An error occurred during registration. Please try again.'
            
            if request.is_json:
                return jsonify({'error': error_msg}), 500
            
            flash(error_msg, 'error')
    
    return render_template('auth.html', show_register=True)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email', '').strip()
            current_password = data.get('current_password', '')
            new_password = data.get('new_password', '')
            monthly_income = data.get('monthly_income', 0)
            default_currency = data.get('default_currency', 'USD')
        else:
            email = request.form.get('email', '').strip()
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            monthly_income = request.form.get('monthly_income', 0)
            default_currency = request.form.get('default_currency', 'USD')
        
        errors = []
        
        # Validate email
        if email and email != current_user.email:
            if not validate_email(email):
                errors.append('Please enter a valid email address')
            elif User.query.filter_by(email=email).first():
                errors.append('Email already exists')
        
        # Validate password change
        if new_password:
            if not current_password:
                errors.append('Current password is required to change password')
            elif not current_user.check_password(current_password):
                errors.append('Current password is incorrect')
            elif len(new_password) < 6:
                errors.append('New password must be at least 6 characters long')
        
        # Validate monthly income
        try:
            monthly_income = float(monthly_income) if monthly_income else 0
            if monthly_income < 0:
                errors.append('Monthly income cannot be negative')
        except ValueError:
            errors.append('Invalid monthly income amount')
        
        if errors:
            if request.is_json:
                return jsonify({'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('settings.html', user=current_user)
        
        # Update user profile
        try:
            if email and email != current_user.email:
                current_user.email = email
            
            if new_password:
                current_user.set_password(new_password)
            
            current_user.monthly_income = monthly_income
            current_user.default_currency = default_currency
            
            db.session.commit()
            
            success_msg = 'Profile updated successfully'
            
            if request.is_json:
                return jsonify({'success': True, 'message': success_msg})
            
            flash(success_msg, 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = 'An error occurred while updating your profile'
            
            if request.is_json:
                return jsonify({'error': error_msg}), 500
            
            flash(error_msg, 'error')
    
    return render_template('settings.html', user=current_user)

@auth_bp.route('/api/user')
@login_required
def user_info():
    """Get current user information"""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'default_currency': current_user.default_currency,
        'monthly_income': float(current_user.monthly_income) if current_user.monthly_income else 0,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None
    })

@auth_bp.route('/api/check-username')
def check_username():
    """Check if username is available"""
    username = request.args.get('username', '').strip()
    
    if not username or len(username) < 3:
        return jsonify({'available': False, 'message': 'Username too short'})
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'available': False, 'message': 'Invalid characters'})
    
    exists = User.query.filter_by(username=username).first() is not None
    
    return jsonify({
        'available': not exists,
        'message': 'Username already taken' if exists else 'Username available'
    })

@auth_bp.route('/api/check-email')
def check_email():
    """Check if email is available"""
    email = request.args.get('email', '').strip()
    
    if not email or not validate_email(email):
        return jsonify({'available': False, 'message': 'Invalid email address'})
    
    # Exclude current user's email if logged in
    query = User.query.filter_by(email=email)
    if current_user.is_authenticated:
        query = query.filter(User.id != current_user.id)
    
    exists = query.first() is not None
    
    return jsonify({
        'available': not exists,
        'message': 'Email already exists' if exists else 'Email available'
    })