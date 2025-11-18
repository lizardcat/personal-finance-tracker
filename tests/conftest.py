"""
Pytest configuration and fixtures for testing
"""
import pytest
import os
from datetime import date, datetime
from decimal import Decimal

# Set test environment before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'

from app import create_app
from models import db, User, BudgetCategory, Transaction, Milestone
from config import TestingConfig


@pytest.fixture(scope='session')
def app():
    """Create and configure a test app instance"""
    app = create_app('testing')

    # Ensure we're using testing config
    assert app.config['TESTING'] is True
    assert 'memory' in app.config['SQLALCHEMY_DATABASE_URI']

    yield app


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """
    Create a new database session for a test.
    Rollback all changes after the test.
    """
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        username='testuser',
        email='test@example.com'
    )
    user.set_password('Test123!@#Password')
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def second_user(db_session):
    """Create a second test user for isolation tests"""
    user = User(
        username='testuser2',
        email='test2@example.com'
    )
    user.set_password('Test456!@#Password')
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(test_user.id)
    return client


@pytest.fixture
def test_category(db_session, test_user):
    """Create a test budget category"""
    category = BudgetCategory(
        user_id=test_user.id,
        name='Groceries',
        allocated_amount=Decimal('500.00'),
        available_amount=Decimal('500.00'),
        category_type='expense',
        color='#28a745'
    )
    db_session.session.add(category)
    db_session.session.commit()
    return category


@pytest.fixture
def test_transaction(db_session, test_user, test_category):
    """Create a test transaction"""
    transaction = Transaction(
        user_id=test_user.id,
        category_id=test_category.id,
        amount=Decimal('50.00'),
        currency='USD',
        description='Test grocery purchase',
        transaction_type='expense',
        transaction_date=date.today(),
        account='checking'
    )
    db_session.session.add(transaction)

    # Update category available amount
    test_category.available_amount -= transaction.amount

    db_session.session.commit()
    return transaction


@pytest.fixture
def test_milestone(db_session, test_user):
    """Create a test milestone"""
    milestone = Milestone(
        user_id=test_user.id,
        name='Emergency Fund',
        description='Build 6-month emergency fund',
        target_amount=Decimal('10000.00'),
        current_amount=Decimal('2500.00'),
        target_date=date(2025, 12, 31),
        category='saving'
    )
    db_session.session.add(milestone)
    db_session.session.commit()
    return milestone


@pytest.fixture
def auth_headers(test_user):
    """Create auth headers for API requests"""
    return {
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_categories_data():
    """Sample budget categories data for testing"""
    return [
        {
            'name': 'Rent',
            'allocated_amount': '1200.00',
            'category_type': 'expense',
            'color': '#dc3545'
        },
        {
            'name': 'Utilities',
            'allocated_amount': '150.00',
            'category_type': 'expense',
            'color': '#ffc107'
        },
        {
            'name': 'Salary',
            'allocated_amount': '5000.00',
            'category_type': 'income',
            'color': '#28a745'
        }
    ]


@pytest.fixture
def sample_transactions_data():
    """Sample transactions data for testing"""
    return [
        {
            'amount': '25.50',
            'currency': 'USD',
            'description': 'Coffee shop',
            'transaction_type': 'expense',
            'transaction_date': date.today().isoformat(),
            'account': 'checking'
        },
        {
            'amount': '100.00',
            'currency': 'USD',
            'description': 'Freelance work',
            'transaction_type': 'income',
            'transaction_date': date.today().isoformat(),
            'account': 'checking'
        }
    ]


# Helper functions for tests

def login_user(client, username='testuser', password='Test123!@#Password'):
    """Helper to login a user"""
    return client.post('/auth/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)


def logout_user(client):
    """Helper to logout a user"""
    return client.get('/auth/logout', follow_redirects=True)


def create_test_user(db_session, username='testuser', email='test@example.com', password='Test123!@#Password'):
    """Helper to create a test user"""
    user = User(username=username, email=email)
    user.set_password(password)
    db_session.session.add(user)
    db_session.session.commit()
    return user
