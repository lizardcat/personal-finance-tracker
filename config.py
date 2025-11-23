import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set")

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///finance_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database pool configuration - CRITICAL for preventing memory leaks
    # Apply to all environments to prevent connection exhaustion
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,           # Maximum number of connections to keep open
        'pool_recycle': 3600,      # Recycle connections after 1 hour (prevents stale connections)
        'pool_pre_ping': True,     # Verify connections are alive before using them
        'max_overflow': 20         # Maximum overflow connections beyond pool_size
    }

    # Flask-Login settings
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 7  # 7 days
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Exchange rate API
    EXCHANGE_API_KEY = os.environ.get('EXCHANGE_API_KEY')
    EXCHANGE_API_URL = 'https://api.exchangerate-api.com/v4/latest/'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    
    # Report settings
    REPORTS_FOLDER = 'reports'
    
    # Default currencies
    DEFAULT_CURRENCIES = [
        'USD',  # US Dollar
        'EUR',  # Euro
        'GBP',  # British Pound
        'KES',  # Kenyan Shilling
        'TSH',  # Tanzanian Shilling
        'CAD',  # Canadian Dollar
        'AUD',  # Australian Dollar
        'JPY',  # Japanese Yen
        'CNY',  # Chinese Yuan
        'INR',  # Indian Rupee
        'ZAR',  # South African Rand
        'NGN',  # Nigerian Naira
        'GHS',  # Ghanaian Cedi
        'UGX',  # Ugandan Shilling
        'CHF',  # Swiss Franc
        'SEK',  # Swedish Krona
        'NOK',  # Norwegian Krone
        'DKK',  # Danish Krone
        'NZD',  # New Zealand Dollar
        'SGD',  # Singapore Dollar
        'HKD',  # Hong Kong Dollar
        'MXN',  # Mexican Peso
        'BRL',  # Brazilian Real
        'AED',  # UAE Dirham
        'SAR',  # Saudi Riyal
    ]

    # Currency names for display
    CURRENCY_NAMES = {
        'USD': 'US Dollar',
        'EUR': 'Euro',
        'GBP': 'British Pound',
        'KES': 'Kenyan Shilling',
        'TSH': 'Tanzanian Shilling',
        'CAD': 'Canadian Dollar',
        'AUD': 'Australian Dollar',
        'JPY': 'Japanese Yen',
        'CNY': 'Chinese Yuan',
        'INR': 'Indian Rupee',
        'ZAR': 'South African Rand',
        'NGN': 'Nigerian Naira',
        'GHS': 'Ghanaian Cedi',
        'UGX': 'Ugandan Shilling',
        'CHF': 'Swiss Franc',
        'SEK': 'Swedish Krona',
        'NOK': 'Norwegian Krone',
        'DKK': 'Danish Krone',
        'NZD': 'New Zealand Dollar',
        'SGD': 'Singapore Dollar',
        'HKD': 'Hong Kong Dollar',
        'MXN': 'Mexican Peso',
        'BRL': 'Brazilian Real',
        'AED': 'UAE Dirham',
        'SAR': 'Saudi Riyal',
    }
    
    # Pagination
    TRANSACTIONS_PER_PAGE = 25
    REPORTS_PER_PAGE = 10

    # Email configuration (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@financetracker.com')

class DevelopmentConfig(Config):
    # Allow fallback SECRET_KEY for development only
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-only-for-development-do-not-use-in-production'

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///finance_tracker_dev.db'
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False

    # Use PostgreSQL in production (DATABASE_URL must be set via Railway env vars)
    # If not set, this will fail when connecting to the database with a clear error
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # Validate SECRET_KEY is set (required for sessions/cookies)
    if not SQLALCHEMY_DATABASE_URI:
        import sys
        print("WARNING: DATABASE_URL not set. Application will fail when connecting to database.", file=sys.stderr)

    # Security settings for production
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

    # Database pool configuration inherited from base Config class

class TestingConfig(Config):
    # Allow fallback SECRET_KEY for testing only
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'test-secret-key-only-for-testing'

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}