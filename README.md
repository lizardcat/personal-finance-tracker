# Personal Finance Tracker

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-blueviolet?style=for-the-badge)](https://student-finance-tracker.up.railway.app/)

A personal finance management app inspired by YNAB principles. Track your budget, expenses, and financial goals with multi-currency support.

Fair warning: this was mostly vibecoded. It works though.

## What It Does

Helps you manage your money with envelope-style budgeting. Allocate your income to categories, track spending, set financial milestones, and see where your money goes.

## Features

- **Budget Management**: Create categories and allocate money to them (YNAB-style)
- **Transaction Tracking**: Log income, expenses, and transfers with custom tags
- **Multi-Currency Support**: Handle multiple currencies with real-time exchange rates
- **Financial Milestones**: Set and track savings goals, debt payoff, or investment targets
- **Recurring Transactions**: Automate regular income or expenses
- **Account Reconciliation**: Match your accounts to real balances
- **Reports & Analytics**: View spending trends, category breakdowns, and monthly reports
- **Data Export**: Export your financial data in various formats
- **Mobile-Friendly**: Responsive UI that works on phones and tablets

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLAlchemy with PostgreSQL/SQLite
- **Frontend**: Bootstrap with vanilla JavaScript
- **Auth**: Flask-Login with session management
- **Email**: Flask-Mail for notifications
- **Security**: Rate limiting, HTTPS enforcement, CSP headers
- **Deployment**: Railway (with Gunicorn)

## Project Structure

```
├── api/                    # API endpoints
│   ├── auth.py            # Authentication
│   ├── budget.py          # Budget category management
│   ├── transactions.py    # Transaction CRUD
│   ├── milestones.py      # Financial goals
│   ├── reports.py         # Analytics and reports
│   ├── reconciliation.py  # Account reconciliation
│   └── exchange_rates.py  # Currency conversion
├── services/              # Business logic layer
│   ├── budget_service.py
│   ├── report_service.py
│   ├── exchange_rate_service.py
│   ├── milestone_service.py
│   ├── recurring_service.py
│   ├── export_service.py
│   └── email_service.py
├── database/              # Database utilities
│   ├── init_db.py
│   ├── migrations.py
│   ├── seed_data.py
│   ├── backup_restore.py
│   └── budget_templates.py
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── models.py              # SQLAlchemy models
├── app.py                 # Application factory
├── routes.py              # Main routes
└── config.py              # Configuration

```

## Local Setup

```bash
# Clone the repo
git clone https://github.com/lizardcat/personal-finance-tracker.git
cd personal-finance-tracker

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Initialize database
python database/init_db.py

# Run the app
python run.py
```

## Configuration

Set these environment variables:
- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: PostgreSQL connection string (defaults to SQLite for dev)
- `EXCHANGE_RATE_API_KEY`: API key for currency conversion (optional)
- `MAIL_*`: Email server settings for notifications (optional)

## Testing

```bash
pytest tests/
```

## License

MIT
