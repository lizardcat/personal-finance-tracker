from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, send_file
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from models import db, User, PasswordResetToken, Transaction, BudgetCategory, Milestone
from utils import validate_email, validate_password_strength
from logging_config import log_security_event
from limiter import limiter
from config import Config
from services.export_service import export_service
from database.backup_restore import backup_database
from database.budget_templates import create_starter_templates
import re
import os
from urllib.parse import urlparse, urljoin
from datetime import datetime
from threading import Thread

auth_bp = Blueprint('auth', __name__)

def send_async_email(app, msg):
    """Send email asynchronously in a background thread"""
    with app.app_context():
        try:
            from app import mail
            mail.send(msg)
            app.logger.info(f'Email sent successfully to {msg.recipients}')
        except Exception as e:
            app.logger.error(f'Failed to send email to {msg.recipients}: {str(e)}', exc_info=True)

def send_email_async(msg):
    """Send email in a background thread to avoid blocking the request"""
    app = current_app._get_current_object()
    thread = Thread(target=send_async_email, args=(app, msg))
    thread.daemon = True
    thread.start()

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes", methods=['POST'])
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

            # Log successful login
            log_security_event(
                'login_success',
                user_id=user.id,
                username=user.username,
                ip_address=request.remote_addr,
                details=f'Remember me: {remember_me}'
            )
            current_app.logger.info(f'User {user.username} logged in from IP {request.remote_addr}')

            # Validate next_page to prevent open redirect vulnerability
            if next_page:
                # Parse the URL to check if it's a relative URL (same host)
                parsed_url = urlparse(next_page)
                # Only allow relative URLs (no scheme, no netloc)
                if parsed_url.netloc or parsed_url.scheme:
                    next_page = None

            redirect_url = next_page if next_page else url_for('main.dashboard')

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'redirect': redirect_url
                })

            return redirect(redirect_url)
        else:
            # Log failed login attempt
            log_security_event(
                'login_failed',
                username=username_or_email,
                ip_address=request.remote_addr,
                details='Invalid credentials'
            )
            current_app.logger.warning(f'Failed login attempt for {username_or_email} from IP {request.remote_addr}')

            error_msg = 'Invalid username/email or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
    
    return render_template('auth.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per hour", methods=['POST'])
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

        # Validate password strength
        is_valid, password_error = validate_password_strength(password)
        if not is_valid:
            errors.append(password_error)

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

            # Create starter budget templates for the new user
            try:
                create_starter_templates(user.id)
                current_app.logger.info(f'Created starter budget templates for new user: {username}')
            except Exception as e:
                current_app.logger.warning(f'Failed to create starter templates for {username}: {e}')
                # Don't fail registration if template creation fails

            # Log in the new user
            login_user(user)

            # Log registration event
            log_security_event(
                'user_registered',
                user_id=user.id,
                username=username,
                ip_address=request.remote_addr,
                details=f'Email: {email}'
            )
            current_app.logger.info(f'New user registered: {username} from IP {request.remote_addr}')

            # Send welcome email asynchronously (if email is configured)
            try:
                # Check if mail is configured
                mail_username = current_app.config.get('MAIL_USERNAME')
                mail_server = current_app.config.get('MAIL_SERVER')

                if not mail_username or not mail_server:
                    current_app.logger.warning(
                        f'Email not configured - skipping welcome email for {email}. '
                        f'Set MAIL_USERNAME and MAIL_SERVER in .env to enable emails.'
                    )
                elif mail_username:
                    dashboard_url = url_for('main.dashboard', _external=True)
                    faq_url = url_for('main.faq', _external=True)

                    msg = Message(
                        subject='Welcome to Personal Finance Tracker!',
                        recipients=[email],
                        html=f'''
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <style>
                                body {{
                                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                    line-height: 1.6;
                                    color: #333;
                                    margin: 0;
                                    padding: 0;
                                    background-color: #f4f4f4;
                                }}
                                .container {{
                                    max-width: 600px;
                                    margin: 40px auto;
                                    background: white;
                                    border-radius: 12px;
                                    overflow: hidden;
                                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                                }}
                                .header {{
                                    background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                                    color: white;
                                    padding: 40px 30px;
                                    text-align: center;
                                }}
                                .header h1 {{
                                    margin: 0;
                                    font-size: 28px;
                                    font-weight: 500;
                                }}
                                .content {{
                                    padding: 40px 30px;
                                }}
                                .content h2 {{
                                    color: #10B981;
                                    font-size: 22px;
                                    margin-top: 0;
                                }}
                                .button {{
                                    display: inline-block;
                                    padding: 14px 32px;
                                    background: #10B981;
                                    color: white;
                                    text-decoration: none;
                                    border-radius: 8px;
                                    margin: 20px 0;
                                    font-weight: 500;
                                }}
                                .features {{
                                    background: #f9fafb;
                                    padding: 20px;
                                    border-radius: 8px;
                                    margin: 20px 0;
                                }}
                                .features h3 {{
                                    color: #059669;
                                    margin-top: 0;
                                    font-size: 18px;
                                }}
                                .features ul {{
                                    margin: 0;
                                    padding-left: 20px;
                                }}
                                .features li {{
                                    margin: 8px 0;
                                    color: #4b5563;
                                }}
                                .footer {{
                                    background: #f9fafb;
                                    padding: 20px 30px;
                                    text-align: center;
                                    color: #6b7280;
                                    font-size: 14px;
                                }}
                                .footer a {{
                                    color: #10B981;
                                    text-decoration: none;
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="header">
                                    <h1>🎉 Welcome to Personal Finance Tracker!</h1>
                                </div>

                                <div class="content">
                                    <h2>Hi {username}!</h2>

                                    <p>Thank you for joining Personal Finance Tracker. We're excited to help you take control of your finances using proven YNAB (You Need A Budget) principles.</p>

                                    <p style="text-align: center;">
                                        <a href="{dashboard_url}" class="button">Go to Your Dashboard</a>
                                    </p>

                                    <div class="features">
                                        <h3>🚀 Getting Started</h3>
                                        <ul>
                                            <li><strong>Set up your budget categories</strong> - Organize your spending into meaningful categories</li>
                                            <li><strong>Track your transactions</strong> - Record income and expenses as they happen</li>
                                            <li><strong>Set financial goals</strong> - Create milestones to track your progress</li>
                                            <li><strong>Learn YNAB principles</strong> - Master the four rules of budgeting</li>
                                        </ul>
                                    </div>

                                    <p><strong>New to YNAB?</strong> Check out our <a href="{faq_url}" style="color: #10B981;">YNAB Guide</a> to learn the four powerful rules that will transform your relationship with money.</p>

                                    <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                                        If you have any questions or need help getting started, don't hesitate to reach out!
                                    </p>

                                    <p style="margin-bottom: 0;">
                                        Happy budgeting!<br>
                                        <strong>The Finance Tracker Team</strong>
                                    </p>
                                </div>

                                <div class="footer">
                                    <p>© 2024 Personal Finance Tracker. Secure & Private.</p>
                                    <p style="margin: 8px 0 0 0;">
                                        Made with ❤️ by <a href="https://github.com/lizardcat" target="_blank">Alex Raza</a>
                                    </p>
                                </div>
                            </div>
                        </body>
                        </html>
                        ''',
                        body=f'''
Welcome to Personal Finance Tracker!

Hi {username},

Thank you for joining Personal Finance Tracker. We're excited to help you take control of your finances using proven YNAB (You Need A Budget) principles.

Getting Started:
- Set up your budget categories
- Track your transactions
- Set financial goals
- Learn YNAB principles

Visit your dashboard: {dashboard_url}
Learn about YNAB: {faq_url}

If you have any questions or need help getting started, don't hesitate to reach out!

Happy budgeting!
The Finance Tracker Team

---
© 2024 Personal Finance Tracker
Made with ❤️ by Alex Raza - https://github.com/lizardcat
                        '''
                    )

                    # Send email asynchronously to avoid blocking the worker
                    send_email_async(msg)
                    current_app.logger.info(f'Welcome email queued for sending to {email}')

            except Exception as email_error:
                # Don't fail registration if email fails - just log it
                current_app.logger.warning(f'Failed to queue welcome email to {email}: {str(email_error)}')

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
            current_app.logger.error(f'Registration error for {username}: {str(e)}', exc_info=True)
            error_msg = 'An error occurred during registration. Please try again.'

            if request.is_json:
                return jsonify({'error': error_msg}), 500

            flash(error_msg, 'error')
    
    return render_template('auth.html', show_register=True)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    # Log logout event before logging out
    log_security_event(
        'logout',
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.remote_addr
    )
    current_app.logger.info(f'User {current_user.username} logged out from IP {request.remote_addr}')

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
            else:
                # Validate new password strength
                is_valid, password_error = validate_password_strength(new_password)
                if not is_valid:
                    errors.append(password_error)
        
        # Validate monthly income
        try:
            monthly_income = float(monthly_income) if monthly_income else 0
            if monthly_income < 0:
                errors.append('Monthly income cannot be negative')
        except ValueError:
            errors.append('Invalid monthly income amount')

        # Validate currency
        if default_currency not in Config.DEFAULT_CURRENCIES:
            errors.append('Invalid currency')

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

            # Log profile update
            log_security_event(
                'profile_updated',
                user_id=current_user.id,
                username=current_user.username,
                ip_address=request.remote_addr,
                details=f'Password changed: {bool(new_password)}, Email changed: {email and email != current_user.email}'
            )
            current_app.logger.info(f'User {current_user.username} updated profile from IP {request.remote_addr}')

            success_msg = 'Profile updated successfully'

            if request.is_json:
                return jsonify({'success': True, 'message': success_msg})

            flash(success_msg, 'success')
            return redirect(url_for('auth.profile'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Profile update error for user {current_user.username}: {str(e)}', exc_info=True)
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
@limiter.limit("10 per minute")
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
@limiter.limit("10 per minute")
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

@auth_bp.route('/api/export-data')
@login_required
def export_user_data():
    """Export all user data as JSON backup"""
    try:
        # Export full backup
        result = export_service.export_full_backup(current_user.id)

        # Log export event
        log_security_event(
            'data_exported',
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            details=f'Exported {result["items_count"]["transactions"]} transactions, {result["items_count"]["categories"]} categories'
        )
        current_app.logger.info(f'User {current_user.username} exported data from IP {request.remote_addr}')

        # Send file as download
        return send_file(
            result['filepath'],
            as_attachment=True,
            download_name=result['filename'],
            mimetype='application/json'
        )

    except Exception as e:
        current_app.logger.error(f'Data export error for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to export data'}), 500

@auth_bp.route('/api/backup-data')
@login_required
def backup_user_data():
    """Create a database backup"""
    try:
        # Create backup directory
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{current_user.username}_{timestamp}.json"
        backup_path = os.path.join(backup_dir, backup_filename)

        # Create backup
        with current_app.app_context():
            result = backup_database(backup_path)

        if result:
            # Log backup event
            log_security_event(
                'database_backup_created',
                user_id=current_user.id,
                username=current_user.username,
                ip_address=request.remote_addr,
                details=f'Backup file: {backup_filename}'
            )
            current_app.logger.info(f'User {current_user.username} created backup from IP {request.remote_addr}')

            # Send file as download
            return send_file(
                result,
                as_attachment=True,
                download_name=backup_filename,
                mimetype='application/json'
            )
        else:
            return jsonify({'error': 'Failed to create backup'}), 500

    except Exception as e:
        current_app.logger.error(f'Backup error for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to create backup'}), 500

@auth_bp.route('/api/clear-data', methods=['POST'])
@login_required
@limiter.limit("3 per hour")
def clear_user_data():
    """Clear all user data (transactions, categories, milestones)"""
    try:
        # Verify confirmation
        data = request.get_json()
        confirmation = data.get('confirmation', '')

        if confirmation != 'DELETE ALL DATA':
            return jsonify({'error': 'Invalid confirmation text'}), 400

        # Delete user data
        Transaction.query.filter_by(user_id=current_user.id).delete()
        Milestone.query.filter_by(user_id=current_user.id).delete()
        BudgetCategory.query.filter_by(user_id=current_user.id).delete()

        db.session.commit()

        # Log data clear event
        log_security_event(
            'user_data_cleared',
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            details='All user data cleared'
        )
        current_app.logger.warning(f'User {current_user.username} cleared all data from IP {request.remote_addr}')

        return jsonify({
            'success': True,
            'message': 'All data cleared successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Clear data error for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to clear data'}), 500

@auth_bp.route('/api/change-password', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        errors = []

        # Validate current password
        if not current_password:
            errors.append('Current password is required')
        elif not current_user.check_password(current_password):
            errors.append('Current password is incorrect')

        # Validate new password
        if not new_password:
            errors.append('New password is required')
        elif new_password != confirm_password:
            errors.append('New passwords do not match')
        else:
            # Validate password strength
            is_valid, password_error = validate_password_strength(new_password)
            if not is_valid:
                errors.append(password_error)

        if errors:
            return jsonify({'errors': errors}), 400

        # Update password
        current_user.set_password(new_password)
        db.session.commit()

        # Log password change
        log_security_event(
            'password_changed',
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            details='Password changed successfully'
        )
        current_app.logger.info(f'User {current_user.username} changed password from IP {request.remote_addr}')

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Password change error for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to change password'}), 500

@auth_bp.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        monthly_income = data.get('monthly_income', 0)
        default_currency = data.get('default_currency', 'USD')

        errors = []

        # Validate email
        if email and email != current_user.email:
            if not validate_email(email):
                errors.append('Please enter a valid email address')
            elif User.query.filter_by(email=email).first():
                errors.append('Email already exists')

        # Validate monthly income
        try:
            monthly_income = float(monthly_income) if monthly_income else 0
            if monthly_income < 0:
                errors.append('Monthly income cannot be negative')
        except ValueError:
            errors.append('Invalid monthly income amount')

        # Validate currency
        if default_currency not in Config.DEFAULT_CURRENCIES:
            errors.append('Invalid currency')

        if errors:
            return jsonify({'errors': errors}), 400

        # Update profile
        if email and email != current_user.email:
            current_user.email = email

        current_user.monthly_income = monthly_income
        current_user.default_currency = default_currency

        db.session.commit()

        # Log profile update
        log_security_event(
            'profile_updated',
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            details=f'Email: {email}, Currency: {default_currency}, Monthly Income: {monthly_income}'
        )
        current_app.logger.info(f'User {current_user.username} updated profile from IP {request.remote_addr}')

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Profile update error for user {current_user.username}: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to update profile'}), 500

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per hour", methods=['POST'])
def forgot_password():
    """Password reset request - send reset email"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get('email', '').strip().lower()

            if not email:
                if request.is_json:
                    return jsonify({'error': 'Email is required'}), 400
                flash('Email is required', 'error')
                return render_template('forgot_password.html')

            # Find user by email (always return success to prevent email enumeration)
            user = User.query.filter_by(email=email).first()

            if user:
                # Delete any existing unused tokens for this user
                PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()

                # Create new reset token
                reset_token = PasswordResetToken.create_for_user(user, expiration_hours=1)
                db.session.add(reset_token)
                db.session.commit()

                # Send reset email asynchronously
                reset_url = url_for('auth.reset_password', token=reset_token.token, _external=True)

                msg = Message(
                    'Password Reset Request - Personal Finance Tracker',
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[user.email]
                )
                msg.html = f'''
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #10B981;">Password Reset Request</h2>
                        <p>Hello <strong>{user.username}</strong>,</p>
                        <p>You recently requested to reset your password for your Personal Finance Tracker account. Click the button below to reset it:</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_url}" style="background-color: #10B981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
                        </div>
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="background: #f5f5f5; padding: 10px; word-break: break-all;">{reset_url}</p>
                        <p><strong>This link will expire in 1 hour.</strong></p>
                        <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                        <p style="font-size: 12px; color: #666;">
                            Made with ❤️ by <a href="https://github.com/lizardcat" style="color: #10B981;">Alex Raza</a>
                        </p>
                    </div>
                </body>
                </html>
                '''

                # Send email asynchronously to avoid blocking the worker
                send_email_async(msg)

                # Log password reset request
                log_security_event(
                    'password_reset_requested',
                    user_id=user.id,
                    username=user.username,
                    ip_address=request.remote_addr,
                    details=f'Reset token sent to {email}'
                )
                current_app.logger.info(f'Password reset requested for {user.username} from IP {request.remote_addr}')

            # Always return success message (prevent email enumeration)
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'If that email exists in our system, we have sent a password reset link.'
                })

            flash('If that email exists in our system, we have sent a password reset link. Please check your inbox.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Password reset request error: {str(e)}', exc_info=True)
            if request.is_json:
                return jsonify({'error': 'Failed to process password reset request'}), 500
            flash('An error occurred. Please try again later.', 'error')
            return render_template('forgot_password.html')

    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=['POST'])
def reset_password(token):
    """Reset password with valid token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Verify token
    reset_token = PasswordResetToken.query.filter_by(token=token).first()

    if not reset_token or not reset_token.is_valid():
        if request.is_json:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        flash('This password reset link is invalid or has expired. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            new_password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')

            errors = []

            # Validate passwords
            if not new_password:
                errors.append('Password is required')
            elif new_password != confirm_password:
                errors.append('Passwords do not match')
            else:
                password_errors = validate_password_strength(new_password)
                errors.extend(password_errors)

            if errors:
                if request.is_json:
                    return jsonify({'errors': errors}), 400
                for error in errors:
                    flash(error, 'error')
                return render_template('reset_password.html', token=token)

            # Update password
            user = reset_token.user
            user.set_password(new_password)
            reset_token.mark_as_used()
            db.session.commit()

            # Log password reset
            log_security_event(
                'password_reset_completed',
                user_id=user.id,
                username=user.username,
                ip_address=request.remote_addr,
                details='Password reset successfully'
            )
            current_app.logger.info(f'Password reset completed for {user.username} from IP {request.remote_addr}')

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Password has been reset successfully. You can now log in.'
                })

            flash('Your password has been reset successfully! You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Password reset error: {str(e)}', exc_info=True)
            if request.is_json:
                return jsonify({'error': 'Failed to reset password'}), 500
            flash('An error occurred. Please try again.', 'error')
            return render_template('reset_password.html', token=token)

    return render_template('reset_password.html', token=token)