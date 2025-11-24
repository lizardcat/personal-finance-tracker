"""
Email service for sending transactional emails via SendGrid
"""
from flask import current_app, render_template_string
from flask_mail import Message, Mail
import logging

logger = logging.getLogger(__name__)

def send_email(to, subject, html_body, text_body=None):
    """
    Send an email using Flask-Mail (configured for SendGrid)

    Args:
        to: Recipient email address (string or list)
        subject: Email subject
        html_body: HTML content of the email
        text_body: Plain text fallback (optional)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        from app import mail

        msg = Message(
            subject=subject,
            recipients=[to] if isinstance(to, str) else to,
            html=html_body,
            body=text_body or html_body
        )

        mail.send(msg)
        logger.info(f"Email sent successfully to {to}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to}: {str(e)}")
        return False


def send_welcome_email(user):
    """
    Send welcome email to newly registered user

    Args:
        user: User object with username and email

    Returns:
        bool: True if sent successfully
    """
    subject = "Welcome to Finance Tracker! 🎉"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }}
            .content {{
                background: #f9fafb;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .feature {{
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #667eea;
            }}
            .footer {{
                text-align: center;
                color: #6b7280;
                font-size: 14px;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="margin: 0;">Welcome to Finance Tracker!</h1>
            <p style="margin: 10px 0 0 0;">Your journey to financial freedom starts now</p>
        </div>

        <div class="content">
            <h2>Hi {user.username}! 👋</h2>

            <p>Thank you for joining Finance Tracker! We're excited to help you take control of your finances and achieve your financial goals.</p>

            <h3>🎁 What's Included:</h3>

            <div class="feature">
                <strong>📊 5 Starter Budget Templates</strong><br>
                We've created professional budget templates for you to get started quickly. Choose from Student, Family, Freelancer, and more!
            </div>

            <div class="feature">
                <strong>💱 Multi-Currency Support</strong><br>
                Track expenses in multiple currencies with automatic conversion. Perfect for international transactions!
            </div>

            <div class="feature">
                <strong>📈 Smart Analytics</strong><br>
                Visualize your spending patterns, track budget performance, and achieve your financial milestones.
            </div>

            <div class="feature">
                <strong>🎯 YNAB Principles</strong><br>
                Built on proven budgeting principles: Give Every Shilling a Job, Embrace True Expenses, Roll With the Punches.
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{current_app.config.get('APP_URL', 'https://your-app-url.railway.app')}" class="button">
                    Start Budgeting Now →
                </a>
            </div>

            <h3>🚀 Quick Start Guide:</h3>
            <ol>
                <li><strong>Choose a Budget Template</strong> - Go to Budget → Templates and apply one that fits your needs</li>
                <li><strong>Add Your Income</strong> - Record your monthly income to allocate</li>
                <li><strong>Set Your Categories</strong> - Customize budget categories and amounts</li>
                <li><strong>Track Transactions</strong> - Start recording your daily expenses</li>
                <li><strong>Review & Adjust</strong> - Check your dashboard and adjust as needed</li>
            </ol>

            <p>Need help? Have questions? Just reply to this email - we're here to help!</p>

            <p>Happy budgeting! 💰</p>

            <p>
                Best regards,<br>
                <strong>The Finance Tracker Team</strong>
            </p>
        </div>

        <div class="footer">
            <p>You're receiving this email because you registered for Finance Tracker.</p>
            <p>© 2024 Finance Tracker. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Welcome to Finance Tracker, {user.username}!

    Thank you for joining! We're excited to help you take control of your finances.

    What's Included:
    - 5 Starter Budget Templates
    - Multi-Currency Support
    - Smart Analytics
    - YNAB Budgeting Principles

    Quick Start:
    1. Choose a Budget Template
    2. Add Your Income
    3. Set Your Categories
    4. Track Transactions
    5. Review & Adjust

    Get started: {current_app.config.get('APP_URL', 'https://your-app-url.railway.app')}

    Need help? Reply to this email!

    Best regards,
    The Finance Tracker Team
    """

    return send_email(user.email, subject, html_body, text_body)


def send_password_reset_email(user, reset_url):
    """
    Send password reset email

    Args:
        user: User object
        reset_url: Password reset URL with token

    Returns:
        bool: True if sent successfully
    """
    subject = "Password Reset Request"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .button {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .warning {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h2>Password Reset Request</h2>

        <p>Hi {user.username},</p>

        <p>We received a request to reset your password. Click the button below to create a new password:</p>

        <div style="text-align: center;">
            <a href="{reset_url}" class="button">Reset Password</a>
        </div>

        <p>Or copy and paste this link into your browser:</p>
        <p style="background: #f3f4f6; padding: 10px; word-break: break-all;">{reset_url}</p>

        <div class="warning">
            <strong>⚠️ Security Notice:</strong>
            <ul style="margin: 5px 0;">
                <li>This link expires in 1 hour</li>
                <li>If you didn't request this, please ignore this email</li>
                <li>Your password won't change until you create a new one</li>
            </ul>
        </div>

        <p>Best regards,<br>Finance Tracker Team</p>
    </body>
    </html>
    """

    text_body = f"""
    Password Reset Request

    Hi {user.username},

    We received a request to reset your password. Click the link below to create a new password:

    {reset_url}

    This link expires in 1 hour.

    If you didn't request this, please ignore this email. Your password won't change until you create a new one.

    Best regards,
    Finance Tracker Team
    """

    return send_email(user.email, subject, html_body, text_body)
