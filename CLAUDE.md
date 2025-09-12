# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a Flask-based personal finance tracker built around YNAB (You Need A Budget) principles. The application follows a modular structure with clear separation of concerns.

### Core Structure
- **Flask Application**: Main app entry point in `app.py`
- **API Layer**: RESTful endpoints in `/api/` directory for auth, budget, transactions, reports, and milestones
- **Service Layer**: Business logic in `/services/` for budget management, exchange rates, exports, milestones, and reports
- **Data Layer**: SQLAlchemy models in `models.py`, database initialization and migrations in `/database/`
- **Frontend**: Jinja2 templates in `/templates/` with Bootstrap-based UI and chart components
- **Static Assets**: CSS, JS, and other assets in `/static/`

### Key Features
- Multi-currency support with exchange rate integration (USD/KES)
- YNAB-style budget management (Give Every Shilling a Job principle)
- Transaction tracking and categorization
- Financial reporting and milestone tracking
- Data export capabilities
- User authentication system

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database.init_db import init_db; init_db()"

# Run database migrations
python scripts/migrate.py

# Seed sample data (if needed)
python -c "from database.seed_data import seed_data; seed_data()"
```

### Running the Application
```bash
# Development server
python app.py

# Production deployment uses Procfile for platforms like Railway/Heroku
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test files
python -m pytest tests/test_budget.py
python -m pytest tests/test_api.py
```

### Database Operations
```bash
# Create database backup
python -c "from database.backup_restore import backup_database; backup_database()"

# Restore from backup
python -c "from database.backup_restore import restore_database; restore_database('backup_file.sql')"
```

## Development Notes

### Template System
- Base template (`templates/base.html`) provides common layout and Bootstrap styling
- Component templates in `/templates/components/` for reusable UI elements (charts, forms, modals)
- Main application pages use template inheritance

### API Design
- RESTful API structure with separate modules for each domain
- Authentication handling in `api/auth.py`
- Financial data operations split across budget, transactions, reports, and milestones

### Database Management
- Enhanced initialization with `database/enhanced_init_db.py`
- Migration system in `database/migrations.py`
- Backup/restore functionality for data protection

### Currency Handling
- Multi-currency support with exchange rate service
- Primary currencies: USD and KES (Kenyan Shillings)
- Real-time exchange rate updates via external API

### Budget Philosophy
Implements YNAB principles:
1. Give Every Shilling a Job - Allocate all income to categories
2. Embrace Your True Expenses - Plan for irregular expenses
3. Roll With the Punches - Adjust budget as needed
4. Age Your Money - Build financial buffer

## Deployment
- Configured for Railway deployment with `railway.json`
- Uses `runtime.txt` for Python version specification
- Environment variables managed through `.env` files