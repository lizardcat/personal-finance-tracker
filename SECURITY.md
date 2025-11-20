# Security Policy

## Overview

This document outlines the security measures implemented in the Personal Finance Tracker application and provides guidance for secure deployment and operation.

## Security Features Implemented

### Phase 1: Critical Security Fixes (COMPLETED)

#### 1. Open Redirect Protection
- **Location**: `api/auth.py:47-53`
- **Implementation**: URL validation using `urllib.parse` to prevent open redirect attacks
- **Protection**: Only allows relative URLs without external hosts or schemes
- **Risk Mitigated**: Phishing attacks and credential theft

#### 2. Secret Key Enforcement
- **Location**: `config.py:7-9, 52-55`
- **Implementation**:
  - Production config requires SECRET_KEY environment variable
  - No fallback to default values in production
  - Development and testing configs allow fallback for convenience
- **Risk Mitigated**: Session hijacking, CSRF bypass

#### 3. Rate Limiting
- **Location**: `app.py:22-28`, `api/auth.py:15-16, 79, 282, 301`
- **Implementation**: Flask-Limiter with memory storage
- **Limits Applied**:
  - Login: 5 attempts per 15 minutes
  - Registration: 3 attempts per hour
  - Username check: 10 per minute
  - Email check: 10 per minute
  - Global: 200 per day, 50 per hour
- **Risk Mitigated**: Brute force attacks, account enumeration, DoS

#### 4. File Path Traversal Protection
- **Location**: `api/reports.py:558-573`
- **Implementation**:
  - Uses `werkzeug.security.safe_join` for path sanitization
  - Validates file paths stay within reports directory
  - Extracts only filename from stored path
- **Risk Mitigated**: Arbitrary file read, unauthorized access to system files

#### 5. HTTPS Enforcement (Production)
- **Location**: `app.py:60-71`
- **Implementation**: Flask-Talisman with strict HTTPS enforcement
- **Features**:
  - Force HTTPS redirection
  - HSTS headers (max-age: 1 year)
  - Content Security Policy
- **Risk Mitigated**: Man-in-the-middle attacks, credential interception

#### 6. Strong Password Requirements
- **Location**: `utils.py:86-116`, `api/auth.py:111-114, 221-224`
- **Requirements**:
  - Minimum 12 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
  - At least one special character
- **Risk Mitigated**: Account compromise via weak passwords

#### 7. Security Headers
- **Location**: `app.py:107-117`
- **Headers Implemented**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: SAMEORIGIN`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security` (production only)
- **Risk Mitigated**: Clickjacking, MIME sniffing, XSS attacks

#### 8. Database Connection Pooling
- **Location**: `config.py:65-70`
- **Configuration**:
  - Pool size: 10 connections
  - Pool recycle: 3600 seconds
  - Pool pre-ping: enabled
  - Max overflow: 20 connections
- **Risk Mitigated**: Connection exhaustion, performance degradation

## Security Best Practices

### Environment Variables

**CRITICAL**: Always set these environment variables in production:

```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Set in environment
SECRET_KEY=<generated-secret-key>
DATABASE_URL=postgresql://user:password@host:port/database
FLASK_ENV=production
```

### Deployment Checklist

Before deploying to production:

- [ ] Set strong SECRET_KEY environment variable
- [ ] Configure DATABASE_URL with PostgreSQL
- [ ] Set FLASK_ENV=production
- [ ] Enable HTTPS on your hosting platform
- [ ] Review and update Content Security Policy if needed
- [ ] Set up database backups
- [ ] Configure monitoring and logging
- [ ] Review rate limiting thresholds for your use case
- [ ] Test all authentication flows
- [ ] Verify HTTPS enforcement is working

### Password Security

- Passwords are hashed using Werkzeug's `generate_password_hash` (bcrypt)
- Strong password policy enforced for all new passwords
- Password validation on registration and profile updates
- No password strength downgrade allowed

### Session Security

- Secure cookies enabled in production
- HTTP-only cookies prevent XSS access
- 7-day remember-me duration (configurable)
- Session cookies are secure in production (HTTPS only)

### API Security

- Rate limiting on all authentication endpoints
- User-specific data isolation (queries filtered by user_id)
- Login required decorators on protected endpoints
- CSRF protection available (Flask-WTF)

## Vulnerability Reporting

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to the project maintainers
3. Include detailed steps to reproduce
4. Allow reasonable time for fixes before public disclosure

## Known Limitations

### Current Implementation

1. **Rate Limiting Storage**: Using in-memory storage
   - **Limitation**: Resets on application restart
   - **Recommendation**: Use Redis for production
   - **Fix**: Update `storage_uri` in `app.py:26` to Redis URL

2. **No Multi-Factor Authentication**: Single-factor authentication only
   - **Status**: Planned for Phase 4
   - **Workaround**: Use very strong passwords

3. **No Data Encryption at Rest**: Database stores data in plaintext
   - **Status**: Planned for Phase 4
   - **Recommendation**: Use database-level encryption (PostgreSQL pgcrypto)

4. **No Audit Logging**: Financial transactions not audited
   - **Status**: Planned for Phase 2
   - **Workaround**: Enable database query logging

## Security Updates

### Version History

- **v1.1.0** (Current): Phase 1 security fixes implemented
  - Open redirect protection
  - Secret key enforcement
  - Rate limiting
  - File path traversal protection
  - HTTPS enforcement
  - Strong password requirements
  - Security headers
  - Database connection pooling

## Compliance

### Data Protection

- User passwords are hashed (never stored in plaintext)
- Session tokens are cryptographically secure
- File access is restricted to user-owned resources

### Recommendations for GDPR Compliance

If serving EU users:

1. Implement data export functionality
2. Add account deletion capability
3. Create privacy policy and cookie notice
4. Implement consent management
5. Add data retention policies
6. Enable user data portability

## Security Maintenance

### Regular Tasks

- [ ] Update dependencies monthly (check for security patches)
- [ ] Review access logs for suspicious activity
- [ ] Rotate SECRET_KEY annually or after security incidents
- [ ] Test backup restoration procedures quarterly
- [ ] Review and update rate limiting thresholds
- [ ] Conduct security audits before major releases

### Dependency Updates

Current security-sensitive dependencies:

- Flask: 2.3.2
- Werkzeug: 2.3.6
- SQLAlchemy: 2.0.18
- Flask-Login: 0.6.2
- gunicorn: 21.2.0 (updated in Phase 1)
- Pillow: 10.4.0 (updated in Phase 1)

Run `pip list --outdated` regularly to check for updates.

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Considerations](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)

## Contact

For security-related questions or concerns, contact the project maintainers.

---

**Last Updated**: 2025-11-18
**Version**: 1.1.0
