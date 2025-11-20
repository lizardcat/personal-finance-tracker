"""
Tests for database models
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from models import User, BudgetCategory, Transaction, Milestone, ExchangeRate


@pytest.mark.unit
class TestUserModel:
    """Test User model"""

    def test_create_user(self, db_session):
        """Test creating a user"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('Password123!@#')

        db_session.session.add(user)
        db_session.session.commit()

        assert user.id is not None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.password_hash != 'Password123!@#'

    def test_password_hashing(self, db_session):
        """Test password is hashed, not stored in plaintext"""
        user = User(username='testuser', email='test@example.com')
        password = 'Password123!@#'
        user.set_password(password)

        assert user.password_hash != password
        assert len(user.password_hash) > 20  # Hashed passwords are long

    def test_password_verification(self, db_session, test_user):
        """Test password verification"""
        assert test_user.check_password('Test123!@#Password') is True
        assert test_user.check_password('WrongPassword') is False

    def test_user_representation(self, db_session, test_user):
        """Test user __repr__ method"""
        assert repr(test_user) == '<User testuser>'

    def test_user_default_values(self, db_session):
        """Test user default values"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('Password123!@#')
        db_session.session.add(user)
        db_session.session.commit()

        assert user.default_currency == 'USD'
        assert user.monthly_income == 0
        assert user.created_at is not None


@pytest.mark.unit
class TestBudgetCategoryModel:
    """Test BudgetCategory model"""

    def test_create_category(self, db_session, test_user):
        """Test creating a budget category"""
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

        assert category.id is not None
        assert category.name == 'Groceries'
        assert category.allocated_amount == Decimal('500.00')
        assert category.category_type == 'expense'

    def test_category_default_values(self, db_session, test_user):
        """Test category default values"""
        category = BudgetCategory(
            user_id=test_user.id,
            name='Test Category'
        )
        db_session.session.add(category)
        db_session.session.commit()

        assert category.allocated_amount == 0
        assert category.available_amount == 0
        assert category.category_type == 'expense'
        assert category.color == '#007bff'
        assert category.created_at is not None

    def test_category_representation(self, db_session, test_category):
        """Test category __repr__ method"""
        assert repr(test_category) == '<BudgetCategory Groceries>'

    def test_update_available_amount(self, db_session, test_user, test_category):
        """Test updating available amount based on transactions"""
        # Create a transaction
        transaction = Transaction(
            user_id=test_user.id,
            category_id=test_category.id,
            amount=Decimal('50.00'),
            currency='USD',
            description='Test purchase',
            transaction_type='expense',
            transaction_date=date.today()
        )
        db_session.session.add(transaction)
        db_session.session.commit()

        # Update available amount
        test_category.update_available_amount()

        assert test_category.available_amount == Decimal('450.00')  # 500 - 50


@pytest.mark.unit
class TestTransactionModel:
    """Test Transaction model"""

    def test_create_transaction(self, db_session, test_user, test_category):
        """Test creating a transaction"""
        transaction = Transaction(
            user_id=test_user.id,
            category_id=test_category.id,
            amount=Decimal('75.50'),
            currency='USD',
            description='Test transaction',
            transaction_type='expense',
            transaction_date=date.today(),
            account='checking'
        )
        db_session.session.add(transaction)
        db_session.session.commit()

        assert transaction.id is not None
        assert transaction.amount == Decimal('75.50')
        assert transaction.description == 'Test transaction'

    def test_transaction_default_values(self, db_session, test_user):
        """Test transaction default values"""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal('100.00'),
            description='Test',
            transaction_type='expense'
        )
        db_session.session.add(transaction)
        db_session.session.commit()

        assert transaction.currency == 'USD'
        assert transaction.transaction_date == date.today()
        assert transaction.account == 'checking'
        assert transaction.recurring is False
        assert transaction.created_at is not None

    def test_transaction_representation(self, db_session, test_transaction):
        """Test transaction __repr__ method"""
        assert 'Test grocery purchase' in repr(test_transaction)
        assert '50.00' in repr(test_transaction)
        assert 'USD' in repr(test_transaction)

    def test_transaction_with_tags(self, db_session, test_user, test_category):
        """Test transaction with tags"""
        transaction = Transaction(
            user_id=test_user.id,
            category_id=test_category.id,
            amount=Decimal('25.00'),
            description='Tagged transaction',
            transaction_type='expense',
            tags='food,organic,healthy'
        )
        db_session.session.add(transaction)
        db_session.session.commit()

        assert transaction.tags == 'food,organic,healthy'

    def test_recurring_transaction(self, db_session, test_user, test_category):
        """Test recurring transaction"""
        transaction = Transaction(
            user_id=test_user.id,
            category_id=test_category.id,
            amount=Decimal('50.00'),
            description='Monthly subscription',
            transaction_type='expense',
            recurring=True,
            recurring_period='monthly'
        )
        db_session.session.add(transaction)
        db_session.session.commit()

        assert transaction.recurring is True
        assert transaction.recurring_period == 'monthly'


@pytest.mark.unit
class TestMilestoneModel:
    """Test Milestone model"""

    def test_create_milestone(self, db_session, test_user):
        """Test creating a milestone"""
        milestone = Milestone(
            user_id=test_user.id,
            name='Emergency Fund',
            description='Save for emergencies',
            target_amount=Decimal('5000.00'),
            current_amount=Decimal('1000.00'),
            target_date=date(2025, 12, 31),
            category='saving'
        )
        db_session.session.add(milestone)
        db_session.session.commit()

        assert milestone.id is not None
        assert milestone.name == 'Emergency Fund'
        assert milestone.target_amount == Decimal('5000.00')

    def test_milestone_progress_percentage(self, db_session, test_milestone):
        """Test milestone progress percentage calculation"""
        progress = test_milestone.progress_percentage

        # 2500 / 10000 = 25%
        assert progress == 25.0

    def test_milestone_100_percent_cap(self, db_session, test_user):
        """Test milestone progress caps at 100%"""
        milestone = Milestone(
            user_id=test_user.id,
            name='Test',
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('1500.00'),  # Over target
            category='saving'
        )
        db_session.session.add(milestone)
        db_session.session.commit()

        # Should cap at 100%
        assert milestone.progress_percentage == 100.0

    def test_milestone_is_overdue(self, db_session, test_user):
        """Test milestone overdue check"""
        from datetime import timedelta

        # Overdue milestone
        overdue = Milestone(
            user_id=test_user.id,
            name='Overdue',
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('500.00'),
            target_date=date.today() - timedelta(days=1),
            completed=False,
            category='saving'
        )
        db_session.session.add(overdue)

        # Future milestone
        future = Milestone(
            user_id=test_user.id,
            name='Future',
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('500.00'),
            target_date=date.today() + timedelta(days=30),
            completed=False,
            category='saving'
        )
        db_session.session.add(future)

        db_session.session.commit()

        assert overdue.is_overdue is True
        assert future.is_overdue is False

    def test_completed_milestone_not_overdue(self, db_session, test_user):
        """Test completed milestone is not considered overdue"""
        from datetime import timedelta

        milestone = Milestone(
            user_id=test_user.id,
            name='Completed',
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('1000.00'),
            target_date=date.today() - timedelta(days=1),
            completed=True,
            completed_date=date.today(),
            category='saving'
        )
        db_session.session.add(milestone)
        db_session.session.commit()

        assert milestone.is_overdue is False

    def test_milestone_representation(self, db_session, test_milestone):
        """Test milestone __repr__ method"""
        assert 'Emergency Fund' in repr(test_milestone)
        assert '2500' in repr(test_milestone)
        assert '10000' in repr(test_milestone)


@pytest.mark.unit
class TestExchangeRateModel:
    """Test ExchangeRate model"""

    def test_create_exchange_rate(self, db_session):
        """Test creating an exchange rate"""
        rate = ExchangeRate(
            base_currency='USD',
            target_currency='KES',
            rate=Decimal('150.25')
        )
        db_session.session.add(rate)
        db_session.session.commit()

        assert rate.id is not None
        assert rate.base_currency == 'USD'
        assert rate.target_currency == 'KES'
        assert rate.rate == Decimal('150.25')
        assert rate.updated_at is not None

    def test_exchange_rate_unique_constraint(self, db_session):
        """Test unique constraint on currency pair"""
        rate1 = ExchangeRate(
            base_currency='USD',
            target_currency='EUR',
            rate=Decimal('0.85')
        )
        db_session.session.add(rate1)
        db_session.session.commit()

        # Try to add duplicate
        rate2 = ExchangeRate(
            base_currency='USD',
            target_currency='EUR',
            rate=Decimal('0.86')
        )
        db_session.session.add(rate2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.session.commit()

    def test_exchange_rate_representation(self, db_session):
        """Test exchange rate __repr__ method"""
        rate = ExchangeRate(
            base_currency='USD',
            target_currency='GBP',
            rate=Decimal('0.75')
        )
        db_session.session.add(rate)
        db_session.session.commit()

        assert 'USD/GBP' in repr(rate)
        assert '0.75' in repr(rate)
