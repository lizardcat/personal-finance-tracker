# Test Suite

This directory contains the test suite for the Personal Finance Tracker application.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_models.py           # Database model tests
├── test_api_transactions.py # Transaction API tests
└── README.md               # This file
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_auth.py
```

### Run specific test class
```bash
pytest tests/test_auth.py::TestUserLogin
```

### Run specific test function
```bash
pytest tests/test_auth.py::TestUserLogin::test_login_success_with_username
```

### Run tests by marker
```bash
# Run only unit tests
pytest -m unit

# Run only API tests
pytest -m api

# Run only security tests
pytest -m security

# Run integration tests
pytest -m integration
```

## Test Markers

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests that test multiple components together
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.slow` - Tests that may take longer to run

## Coverage Reports

After running tests with coverage, view the HTML report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Writing New Tests

### Test File Naming
- Test files should be named `test_*.py` or `*_test.py`
- Place them in the `tests/` directory

### Test Function Naming
- Test functions should be named `test_*`
- Use descriptive names that explain what is being tested

### Using Fixtures
Common fixtures available from `conftest.py`:
- `app` - Flask application instance
- `client` - Test client for making requests
- `db_session` - Database session with automatic rollback
- `test_user` - Pre-created test user
- `authenticated_client` - Client with logged-in user
- `test_category` - Pre-created budget category
- `test_transaction` - Pre-created transaction
- `test_milestone` - Pre-created milestone

### Example Test

```python
import pytest

@pytest.mark.unit
def test_example(client, db_session, test_user):
    """Test description"""
    # Arrange
    data = {'key': 'value'}

    # Act
    response = client.post('/api/endpoint', json=data)

    # Assert
    assert response.status_code == 200
    assert response.get_json()['success'] is True
```

## CI/CD Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

See `.github/workflows/ci.yml` for CI/CD configuration.

## Test Coverage Goals

- **Target:** 80% code coverage
- **Critical paths:** 100% coverage for authentication and financial transactions
- **Current coverage:** Run `pytest --cov` to see current coverage

## Troubleshooting

### Tests fail with database errors
Make sure you're using the testing configuration:
```bash
export FLASK_ENV=testing
```

### Import errors
Install test dependencies:
```bash
pip install -r requirements.txt
```

### Rate limiting issues in tests
Rate limits are disabled in testing configuration by default.

## Best Practices

1. **Isolation:** Each test should be independent
2. **Clean up:** Use fixtures with automatic cleanup
3. **Descriptive names:** Test names should describe what they test
4. **One assertion per test:** Keep tests focused
5. **Arrange-Act-Assert:** Follow the AAA pattern
6. **Mock external dependencies:** Don't make real API calls in tests
7. **Test edge cases:** Test both success and failure scenarios
