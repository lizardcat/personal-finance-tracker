"""
Tests for authentication functionality
"""
import pytest
from models import User


@pytest.mark.auth
@pytest.mark.unit
class TestUserRegistration:
    """Test user registration"""

    def test_register_new_user_success(self, client, db_session):
        """Test successful user registration"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'NewPass123!@#',
            'confirm_password': 'NewPass123!@#'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Welcome newuser!' in response.data or b'dashboard' in response.data.lower()

        # Verify user exists in database
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'newuser@example.com'

    def test_register_duplicate_username(self, client, db_session, test_user):
        """Test registration with duplicate username"""
        response = client.post('/auth/register', data={
            'username': 'testuser',  # Already exists
            'email': 'different@example.com',
            'password': 'NewPass123!@#',
            'confirm_password': 'NewPass123!@#'
        })

        assert response.status_code == 200
        assert b'Username already exists' in response.data

    def test_register_duplicate_email(self, client, db_session, test_user):
        """Test registration with duplicate email"""
        response = client.post('/auth/register', data={
            'username': 'differentuser',
            'email': 'test@example.com',  # Already exists
            'password': 'NewPass123!@#',
            'confirm_password': 'NewPass123!@#'
        })

        assert response.status_code == 200
        assert b'Email already exists' in response.data

    def test_register_weak_password(self, client, db_session):
        """Test registration with weak password"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'weak',  # Too short, missing requirements
            'confirm_password': 'weak'
        })

        assert response.status_code == 200
        assert b'Password must be at least 12 characters' in response.data

    def test_register_password_mismatch(self, client, db_session):
        """Test registration with mismatched passwords"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'Password123!@#',
            'confirm_password': 'Different123!@#'
        })

        assert response.status_code == 200
        assert b'Passwords do not match' in response.data

    def test_register_invalid_username(self, client, db_session):
        """Test registration with invalid username"""
        response = client.post('/auth/register', data={
            'username': 'ab',  # Too short
            'email': 'newuser@example.com',
            'password': 'Password123!@#',
            'confirm_password': 'Password123!@#'
        })

        assert response.status_code == 200
        assert b'Username must be at least 3 characters' in response.data

    def test_register_invalid_email(self, client, db_session):
        """Test registration with invalid email"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'not-an-email',  # Invalid format
            'password': 'Password123!@#',
            'confirm_password': 'Password123!@#'
        })

        assert response.status_code == 200
        assert b'valid email' in response.data.lower()


@pytest.mark.auth
@pytest.mark.unit
class TestUserLogin:
    """Test user login functionality"""

    def test_login_success_with_username(self, client, db_session, test_user):
        """Test successful login with username"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'Test123!@#Password'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'logout' in response.data.lower()

    def test_login_success_with_email(self, client, db_session, test_user):
        """Test successful login with email"""
        response = client.post('/auth/login', data={
            'username': 'test@example.com',  # Using email
            'password': 'Test123!@#Password'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'logout' in response.data.lower()

    def test_login_invalid_password(self, client, db_session, test_user):
        """Test login with wrong password"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'WrongPassword123!@#'
        })

        assert response.status_code == 200
        assert b'Invalid username/email or password' in response.data

    def test_login_nonexistent_user(self, client, db_session):
        """Test login with nonexistent user"""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'Password123!@#'
        })

        assert response.status_code == 200
        assert b'Invalid username/email or password' in response.data

    def test_login_missing_credentials(self, client, db_session):
        """Test login with missing credentials"""
        response = client.post('/auth/login', data={})

        assert response.status_code == 200 or response.status_code == 400
        assert b'required' in response.data.lower()

    def test_login_remember_me(self, client, db_session, test_user):
        """Test login with remember me option"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'Test123!@#Password',
            'remember_me': 'on'
        }, follow_redirects=True)

        assert response.status_code == 200


@pytest.mark.auth
@pytest.mark.unit
class TestUserLogout:
    """Test user logout functionality"""

    def test_logout_success(self, client, db_session, test_user):
        """Test successful logout"""
        # Login first
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'Test123!@#Password'
        })

        # Then logout
        response = client.get('/auth/logout', follow_redirects=True)

        assert response.status_code == 200
        assert b'logged out' in response.data.lower() or b'login' in response.data.lower()


@pytest.mark.auth
@pytest.mark.security
class TestOpenRedirectProtection:
    """Test open redirect vulnerability protection"""

    def test_login_redirect_safe_relative_url(self, client, db_session, test_user):
        """Test login redirects to safe relative URL"""
        response = client.post('/auth/login?next=/dashboard', data={
            'username': 'testuser',
            'password': 'Test123!@#Password'
        }, follow_redirects=False)

        # Should redirect to dashboard
        assert response.status_code == 302
        assert '/dashboard' in response.location

    def test_login_blocks_external_redirect(self, client, db_session, test_user):
        """Test login blocks external redirect (open redirect protection)"""
        response = client.post('/auth/login?next=//evil.com', data={
            'username': 'testuser',
            'password': 'Test123!@#Password'
        }, follow_redirects=False)

        # Should NOT redirect to evil.com, should go to dashboard
        assert response.status_code == 302
        assert 'evil.com' not in response.location
        assert 'dashboard' in response.location

    def test_login_blocks_absolute_url_redirect(self, client, db_session, test_user):
        """Test login blocks absolute URL redirect"""
        response = client.post('/auth/login?next=https://evil.com', data={
            'username': 'testuser',
            'password': 'Test123!@#Password'
        }, follow_redirects=False)

        # Should NOT redirect to evil.com
        assert response.status_code == 302
        assert 'evil.com' not in response.location


@pytest.mark.auth
@pytest.mark.api
class TestAuthAPI:
    """Test authentication API endpoints"""

    def test_check_username_available(self, client, db_session):
        """Test username availability check"""
        response = client.get('/auth/api/check-username?username=newuser')

        assert response.status_code == 200
        data = response.get_json()
        assert data['available'] is True

    def test_check_username_taken(self, client, db_session, test_user):
        """Test username taken check"""
        response = client.get('/auth/api/check-username?username=testuser')

        assert response.status_code == 200
        data = response.get_json()
        assert data['available'] is False

    def test_check_email_available(self, client, db_session):
        """Test email availability check"""
        response = client.get('/auth/api/check-email?email=new@example.com')

        assert response.status_code == 200
        data = response.get_json()
        assert data['available'] is True

    def test_check_email_taken(self, client, db_session, test_user):
        """Test email taken check"""
        response = client.get('/auth/api/check-email?email=test@example.com')

        assert response.status_code == 200
        data = response.get_json()
        assert data['available'] is False


@pytest.mark.auth
@pytest.mark.security
class TestRateLimiting:
    """Test rate limiting on auth endpoints"""

    def test_login_rate_limit(self, client, db_session, test_user):
        """Test rate limiting on login endpoint"""
        # Make multiple failed login attempts
        for i in range(6):  # Limit is 5 per 15 minutes
            response = client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'WrongPassword'
            })

            if i < 5:
                assert response.status_code in [200, 401]
            else:
                # Should be rate limited on 6th attempt
                assert response.status_code == 429
                break

    def test_registration_rate_limit(self, client, db_session):
        """Test rate limiting on registration endpoint"""
        # Make multiple registration attempts
        for i in range(4):  # Limit is 3 per hour
            response = client.post('/auth/register', data={
                'username': f'user{i}',
                'email': f'user{i}@example.com',
                'password': 'Password123!@#',
                'confirm_password': 'Password123!@#'
            })

            if i < 3:
                assert response.status_code == 200 or response.status_code == 302
            else:
                # Should be rate limited on 4th attempt
                assert response.status_code == 429
                break
