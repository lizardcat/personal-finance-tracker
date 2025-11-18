"""
Tests for Transactions API
"""
import pytest
from decimal import Decimal
from datetime import date
from models import Transaction


@pytest.mark.api
class TestTransactionsAPI:
    """Test transaction API endpoints"""

    def test_get_transactions_requires_auth(self, client, db_session):
        """Test that getting transactions requires authentication"""
        response = client.get('/api/transactions/')

        assert response.status_code == 302  # Redirect to login
        assert 'login' in response.location

    def test_get_transactions_success(self, client, db_session, test_user, test_transaction):
        """Test getting transactions for authenticated user"""
        # Login first
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get('/api/transactions/')

        assert response.status_code == 200

    def test_create_transaction_success(self, client, db_session, test_user, test_category):
        """Test creating a new transaction"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.post('/api/transactions/', json={
            'amount': '75.50',
            'currency': 'USD',
            'description': 'Test purchase',
            'transaction_type': 'expense',
            'category_id': test_category.id,
            'transaction_date': date.today().isoformat(),
            'account': 'checking'
        })

        assert response.status_code == 200 or response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'transaction' in data

        # Verify transaction exists
        transaction = Transaction.query.filter_by(description='Test purchase').first()
        assert transaction is not None
        assert transaction.amount == Decimal('75.50')

    def test_create_transaction_invalid_amount(self, client, db_session, test_user):
        """Test creating transaction with invalid amount"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.post('/api/transactions/', json={
            'amount': 'invalid',
            'description': 'Test',
            'transaction_type': 'expense'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_transaction_missing_description(self, client, db_session, test_user):
        """Test creating transaction without description"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.post('/api/transactions/', json={
            'amount': '50.00',
            'transaction_type': 'expense'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'description' in data['error'].lower()

    def test_update_transaction_success(self, client, db_session, test_user, test_transaction):
        """Test updating a transaction"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.put(f'/api/transactions/{test_transaction.id}', json={
            'amount': '60.00',
            'description': 'Updated description'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify update
        transaction = Transaction.query.get(test_transaction.id)
        assert transaction.amount == Decimal('60.00')
        assert transaction.description == 'Updated description'

    def test_update_nonexistent_transaction(self, client, db_session, test_user):
        """Test updating non-existent transaction"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.put('/api/transactions/99999', json={
            'amount': '60.00'
        })

        assert response.status_code == 404

    def test_update_other_user_transaction(self, client, db_session, test_user, second_user, test_transaction):
        """Test user cannot update another user's transaction"""
        # Login as second user
        with client.session_transaction() as sess:
            sess['_user_id'] = str(second_user.id)

        response = client.put(f'/api/transactions/{test_transaction.id}', json={
            'amount': '999.00'
        })

        assert response.status_code == 404  # Not found (user isolation)

        # Verify transaction wasn't updated
        transaction = Transaction.query.get(test_transaction.id)
        assert transaction.amount == Decimal('50.00')  # Original amount

    def test_delete_transaction_success(self, client, db_session, test_user, test_transaction):
        """Test deleting a transaction"""
        transaction_id = test_transaction.id

        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.delete(f'/api/transactions/{transaction_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify deletion
        transaction = Transaction.query.get(transaction_id)
        assert transaction is None

    def test_delete_nonexistent_transaction(self, client, db_session, test_user):
        """Test deleting non-existent transaction"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.delete('/api/transactions/99999')

        assert response.status_code == 404

    def test_transaction_filtering_by_type(self, client, db_session, test_user, test_category):
        """Test filtering transactions by type"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        # Create income and expense transactions
        income = Transaction(
            user_id=test_user.id,
            amount=Decimal('1000.00'),
            description='Salary',
            transaction_type='income'
        )
        expense = Transaction(
            user_id=test_user.id,
            category_id=test_category.id,
            amount=Decimal('50.00'),
            description='Purchase',
            transaction_type='expense'
        )
        db_session.session.add_all([income, expense])
        db_session.session.commit()

        # Filter by income
        response = client.get('/api/transactions/?type=income')
        assert response.status_code == 200

        # Filter by expense
        response = client.get('/api/transactions/?type=expense')
        assert response.status_code == 200


@pytest.mark.api
@pytest.mark.integration
class TestTransactionCategoryIntegration:
    """Test transaction and category integration"""

    def test_transaction_updates_category_balance(self, client, db_session, test_user, test_category):
        """Test that creating expense transaction updates category balance"""
        initial_available = test_category.available_amount

        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        # Create expense transaction
        response = client.post('/api/transactions/', json={
            'amount': '100.00',
            'description': 'Test expense',
            'transaction_type': 'expense',
            'category_id': test_category.id
        })

        assert response.status_code == 200 or response.status_code == 201

        # Check category balance was updated
        db_session.session.refresh(test_category)
        assert test_category.available_amount == initial_available - Decimal('100.00')

    def test_deleting_transaction_restores_category_balance(self, client, db_session, test_user, test_transaction, test_category):
        """Test that deleting expense transaction restores category balance"""
        # Get current balance
        current_balance = test_category.available_amount
        transaction_amount = test_transaction.amount

        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        # Delete transaction
        response = client.delete(f'/api/transactions/{test_transaction.id}')
        assert response.status_code == 200

        # Check category balance was restored
        db_session.session.refresh(test_category)
        expected_balance = current_balance + transaction_amount
        assert test_category.available_amount == expected_balance
