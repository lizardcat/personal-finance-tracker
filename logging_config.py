"""
Logging configuration for Personal Finance Tracker
Provides structured logging with file rotation and different levels
"""
import logging
from datetime import datetime


def setup_logging(app):
    """
    Configure application logging for Railway serverless environment
    All logs go to stdout/stderr for Railway's log collection

    Args:
        app: Flask application instance
    """
    # Determine log level based on environment
    if app.config.get('DEBUG'):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Set up formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] in %(module)s (%(pathname)s:%(lineno)d): %(message)s'
    )

    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s]: %(message)s'
    )

    # Main console handler for all logs
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(log_level)

    # Error console handler (stderr)
    error_handler = logging.StreamHandler()
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)

    # Configure root logger
    app.logger.setLevel(log_level)

    # Remove default handlers
    app.logger.handlers.clear()

    # Add console handlers
    app.logger.addHandler(console_handler)
    app.logger.addHandler(error_handler)

    # Create separate loggers for specific purposes
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(console_handler)

    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    audit_logger.addHandler(console_handler)

    # Log application startup
    app.logger.info('=' * 80)
    app.logger.info(f'Finance Tracker Application Starting (Railway Serverless Mode)')
    app.logger.info(f'Environment: {app.config.get("ENV", "unknown")}')
    app.logger.info(f'Debug Mode: {app.config.get("DEBUG", False)}')
    app.logger.info(f'Database: {app.config.get("SQLALCHEMY_DATABASE_URI", "").split("://")[0] if app.config.get("SQLALCHEMY_DATABASE_URI") else "unknown"}')
    app.logger.info('=' * 80)

    # Log security configuration
    security_logger.info('Security configuration loaded')
    security_logger.info(f'HTTPS enforcement: {app.config.get("ENV") == "production"}')
    security_logger.info(f'Rate limiting: Enabled')

    return app.logger


def log_security_event(event_type, user_id=None, username=None, ip_address=None, details=None):
    """
    Log security-related events (login, logout, failed attempts, etc.)

    Args:
        event_type: Type of security event (login, logout, failed_login, etc.)
        user_id: User ID if applicable
        username: Username if applicable
        ip_address: IP address of request
        details: Additional details about the event
    """
    security_logger = logging.getLogger('security')

    log_parts = [f'Event: {event_type}']
    if username:
        log_parts.append(f'User: {username}')
    if user_id:
        log_parts.append(f'UserID: {user_id}')
    if ip_address:
        log_parts.append(f'IP: {ip_address}')
    if details:
        log_parts.append(f'Details: {details}')

    security_logger.info(' | '.join(log_parts))


def log_audit_event(action, user_id, username, entity_type, entity_id,
                    old_value=None, new_value=None, ip_address=None):
    """
    Log audit trail for financial transactions and critical operations

    Args:
        action: Action performed (CREATE, UPDATE, DELETE)
        user_id: User ID performing the action
        username: Username performing the action
        entity_type: Type of entity (Transaction, Budget, Milestone)
        entity_id: ID of the entity
        old_value: Previous value (for updates/deletes)
        new_value: New value (for creates/updates)
        ip_address: IP address of request
    """
    audit_logger = logging.getLogger('audit')

    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'user_id': user_id,
        'username': username,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'ip_address': ip_address
    }

    if old_value:
        log_data['old_value'] = str(old_value)
    if new_value:
        log_data['new_value'] = str(new_value)

    # Format as structured log entry
    log_parts = [f'{k}={v}' for k, v in log_data.items() if v is not None]
    audit_logger.info(' | '.join(log_parts))


def log_error(error, context=None, user_id=None):
    """
    Log application errors with context

    Args:
        error: Exception or error message
        context: Additional context about where/why error occurred
        user_id: User ID if applicable
    """
    logger = logging.getLogger('finance_tracker')

    error_msg = f'Error: {str(error)}'
    if context:
        error_msg += f' | Context: {context}'
    if user_id:
        error_msg += f' | UserID: {user_id}'

    if isinstance(error, Exception):
        logger.exception(error_msg)
    else:
        logger.error(error_msg)
