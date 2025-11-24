from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from functools import wraps
from flask import jsonify, session, redirect, url_for, flash
from flask_login import current_user
import re
import os

def get_currency_symbol(currency='KES'):
    """Get the symbol for a currency code"""
    from config import Config
    return Config.CURRENCY_SYMBOLS.get(currency, currency)

def format_currency(amount, currency=None, use_symbol=True):
    """Format currency amount for display

    Args:
        amount: The amount to format
        currency: Currency code (e.g. 'KES', 'USD'). If None, uses current user's default currency
        use_symbol: If True, use currency symbol (KSh); if False, use code (KES)
    """
    if amount is None:
        amount = Decimal('0.00')

    # Convert to Decimal for precise calculations
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    # Round to 2 decimal places
    amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Format the number with commas
    formatted_amount = f"{amount:,.2f}"

    # If no currency specified, use current user's default currency
    if currency is None:
        from flask_login import current_user
        if current_user and current_user.is_authenticated and hasattr(current_user, 'default_currency'):
            currency = current_user.default_currency or 'KES'
        else:
            currency = 'KES'  # Fallback for non-authenticated users

    # Use symbol or code based on preference
    if use_symbol:
        symbol = get_currency_symbol(currency)
        return f"{symbol} {formatted_amount}"
    else:
        return f"{formatted_amount} {currency}"

def convert_currency(amount, from_currency, to_currency):
    """Convert amount from one currency to another using exchange rates

    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code

    Returns:
        Converted amount as Decimal
    """
    if from_currency == to_currency:
        return amount if isinstance(amount, Decimal) else Decimal(str(amount))

    try:
        from services.exchange_rate_service import exchange_rate_service
        converted = exchange_rate_service.convert_amount(
            amount if isinstance(amount, Decimal) else Decimal(str(amount)),
            from_currency,
            to_currency
        )
        return converted
    except Exception as e:
        # If conversion fails, return original amount
        print(f"Currency conversion error: {e}")
        return amount if isinstance(amount, Decimal) else Decimal(str(amount))

def format_currency_with_original(amount, original_currency, display_currency, show_original=True):
    """Format currency with optional original currency display

    Args:
        amount: The amount in original currency
        original_currency: The currency the amount is in
        display_currency: The currency to display/convert to
        show_original: Whether to show original amount if different

    Returns:
        Formatted string like "KSh 15,000" or "KSh 15,000 ($100 USD)"
    """
    if original_currency == display_currency:
        return format_currency(amount, display_currency)

    # Convert to display currency
    converted_amount = convert_currency(amount, original_currency, display_currency)
    converted_str = format_currency(converted_amount, display_currency)

    # Optionally show original
    if show_original:
        original_str = format_currency(amount, original_currency)
        return f"{converted_str} ({original_str})"
    else:
        return converted_str

def parse_currency(amount_str):
    """Parse currency string to Decimal"""
    if not amount_str:
        return Decimal('0.00')
    
    # Remove currency symbols and spaces
    cleaned = re.sub(r'[^\d.-]', '', str(amount_str))
    
    try:
        return Decimal(cleaned).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except:
        return Decimal('0.00')

def calculate_percentage(part, total):
    """Calculate percentage with error handling"""
    if not total or total <= 0:
        return 0
    return round((float(part) / float(total)) * 100, 1)

def get_month_range(year=None, month=None):
    """Get the first and last day of a month"""
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    first_day = date(year, month, 1)
    
    # Get last day of month
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    return first_day, last_day

def get_year_range(year=None):
    """Get the first and last day of a year"""
    if not year:
        year = datetime.now().year
    
    first_day = date(year, 1, 1)
    last_day = date(year, 12, 31)
    
    return first_day, last_day

def days_until_date(target_date):
    """Calculate days until a target date"""
    if not target_date:
        return None
    
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    
    today = date.today()
    delta = target_date - today
    return delta.days

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password_strength(password):
    """
    Validate password strength for financial application.
    Returns (is_valid, error_message)

    Requirements:
    - At least 8 characters
    - Contains at least 3 of the following 4 types:
      * Uppercase letter
      * Lowercase letter
      * Digit
      * Special character
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Count how many character types are present
    has_uppercase = bool(re.search(r'[A-Z]', password))
    has_lowercase = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', password))

    types_count = sum([has_uppercase, has_lowercase, has_digit, has_special])

    if types_count < 3:
        return False, "Password must contain at least 3 of the following: uppercase letter, lowercase letter, number, or special character"

    return True, ""

def sanitize_filename(filename):
    """Sanitize filename for safe file operations"""
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized

def login_required_api(f):
    """Decorator for API endpoints that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # For now, we'll use a simple admin check
        # In a real app, you'd have an is_admin field in the User model
        if current_user.username != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def ensure_directory_exists(directory_path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
    return directory_path

def get_budget_health_status(available_amount, allocated_amount):
    """Determine budget health status based on available vs allocated amounts"""
    if allocated_amount <= 0:
        return 'warning'  # No budget allocated
    
    percentage = (float(available_amount) / float(allocated_amount)) * 100
    
    if percentage < 10:
        return 'danger'  # Less than 10% remaining
    elif percentage < 25:
        return 'warning'  # Less than 25% remaining
    else:
        return 'success'  # Healthy budget

def calculate_monthly_average(transactions, months=6):
    """Calculate average monthly spending from transactions"""
    if not transactions:
        return Decimal('0.00')
    
    total = sum(t.amount for t in transactions if t.transaction_type == 'expense')
    return (total / months).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def get_transaction_summary(transactions):
    """Generate summary statistics for a list of transactions"""
    if not transactions:
        return {
            'total_income': Decimal('0.00'),
            'total_expenses': Decimal('0.00'),
            'net_amount': Decimal('0.00'),
            'transaction_count': 0
        }
    
    total_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
    total_expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')
    
    return {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_amount': total_income - total_expenses,
        'transaction_count': len(transactions)
    }

def generate_color_palette(count):
    """Generate a color palette for charts"""
    colors = [
        '#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8',
        '#6f42c1', '#e83e8c', '#fd7e14', '#20c997', '#6c757d'
    ]
    
    if count <= len(colors):
        return colors[:count]
    
    # Generate additional colors if needed
    extended_colors = colors[:]
    for i in range(count - len(colors)):
        # Simple color generation based on index
        hue = (i * 137.5) % 360  # Golden angle for good distribution
        extended_colors.append(f'hsl({hue}, 70%, 50%)')
    
    return extended_colors[:count]