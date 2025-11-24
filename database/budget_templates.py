"""
Pre-defined budget templates for users to get started quickly
"""
from models import db, BudgetTemplate, BudgetTemplateItem, User
from decimal import Decimal

def create_starter_templates(user_id):
    """Create starter budget templates for a new user"""

    templates = [
        {
            'name': '50/30/20 Budget (KES)',
            'description': 'Popular budgeting rule: 50% needs, 30% wants, 20% savings. Based on KES 100,000 monthly income.',
            'is_default': True,
            'categories': [
                # Needs (50%)
                {'name': 'Housing', 'amount': Decimal('30000'), 'type': 'expense', 'color': '#FF6B6B'},
                {'name': 'Utilities', 'amount': Decimal('5000'), 'type': 'expense', 'color': '#4ECDC4'},
                {'name': 'Groceries', 'amount': Decimal('10000'), 'type': 'expense', 'color': '#45B7D1'},
                {'name': 'Transportation', 'amount': Decimal('5000'), 'type': 'expense', 'color': '#96CEB4'},

                # Wants (30%)
                {'name': 'Entertainment', 'amount': Decimal('8000'), 'type': 'expense', 'color': '#FFEAA7'},
                {'name': 'Dining Out', 'amount': Decimal('7000'), 'type': 'expense', 'color': '#DFE6E9'},
                {'name': 'Shopping', 'amount': Decimal('10000'), 'type': 'expense', 'color': '#A29BFE'},
                {'name': 'Personal Care', 'amount': Decimal('5000'), 'type': 'expense', 'color': '#FD79A8'},

                # Savings (20%)
                {'name': 'Emergency Fund', 'amount': Decimal('10000'), 'type': 'savings', 'color': '#00B894'},
                {'name': 'Investments', 'amount': Decimal('5000'), 'type': 'savings', 'color': '#00CEC9'},
                {'name': 'Future Goals', 'amount': Decimal('5000'), 'type': 'savings', 'color': '#6C5CE7'},
            ]
        },
        {
            'name': 'Student Budget (KES)',
            'description': 'Simple budget for students. Based on KES 30,000 monthly allowance.',
            'is_default': False,
            'categories': [
                {'name': 'Rent/Accommodation', 'amount': Decimal('12000'), 'type': 'expense', 'color': '#FF6B6B'},
                {'name': 'Food & Groceries', 'amount': Decimal('8000'), 'type': 'expense', 'color': '#45B7D1'},
                {'name': 'Transportation', 'amount': Decimal('3000'), 'type': 'expense', 'color': '#96CEB4'},
                {'name': 'Books & Supplies', 'amount': Decimal('2000'), 'type': 'expense', 'color': '#A29BFE'},
                {'name': 'Internet & Phone', 'amount': Decimal('2000'), 'type': 'expense', 'color': '#4ECDC4'},
                {'name': 'Entertainment', 'amount': Decimal('2000'), 'type': 'expense', 'color': '#FFEAA7'},
                {'name': 'Savings', 'amount': Decimal('1000'), 'type': 'savings', 'color': '#00B894'},
            ]
        },
        {
            'name': 'Family Budget (KES)',
            'description': 'Comprehensive family budget. Based on KES 200,000 monthly income.',
            'is_default': False,
            'categories': [
                {'name': 'Housing/Rent', 'amount': Decimal('50000'), 'type': 'expense', 'color': '#FF6B6B'},
                {'name': 'Utilities', 'amount': Decimal('10000'), 'type': 'expense', 'color': '#4ECDC4'},
                {'name': 'Groceries', 'amount': Decimal('30000'), 'type': 'expense', 'color': '#45B7D1'},
                {'name': 'Transportation', 'amount': Decimal('15000'), 'type': 'expense', 'color': '#96CEB4'},
                {'name': 'Education/School Fees', 'amount': Decimal('20000'), 'type': 'expense', 'color': '#A29BFE'},
                {'name': 'Healthcare', 'amount': Decimal('10000'), 'type': 'expense', 'color': '#FD79A8'},
                {'name': 'Insurance', 'amount': Decimal('8000'), 'type': 'expense', 'color': '#E17055'},
                {'name': 'Entertainment', 'amount': Decimal('12000'), 'type': 'expense', 'color': '#FFEAA7'},
                {'name': 'Dining Out', 'amount': Decimal('10000'), 'type': 'expense', 'color': '#DFE6E9'},
                {'name': 'Emergency Fund', 'amount': Decimal('20000'), 'type': 'savings', 'color': '#00B894'},
                {'name': 'Retirement Savings', 'amount': Decimal('10000'), 'type': 'savings', 'color': '#00CEC9'},
                {'name': 'Kids Future', 'amount': Decimal('5000'), 'type': 'savings', 'color': '#6C5CE7'},
            ]
        },
        {
            'name': 'Minimal Budget (KES)',
            'description': 'Basic budget for minimal living expenses. Based on KES 40,000 monthly income.',
            'is_default': False,
            'categories': [
                {'name': 'Rent', 'amount': Decimal('15000'), 'type': 'expense', 'color': '#FF6B6B'},
                {'name': 'Food', 'amount': Decimal('12000'), 'type': 'expense', 'color': '#45B7D1'},
                {'name': 'Transportation', 'amount': Decimal('4000'), 'type': 'expense', 'color': '#96CEB4'},
                {'name': 'Utilities', 'amount': Decimal('3000'), 'type': 'expense', 'color': '#4ECDC4'},
                {'name': 'Phone/Internet', 'amount': Decimal('2000'), 'type': 'expense', 'color': '#A29BFE'},
                {'name': 'Emergency Fund', 'amount': Decimal('4000'), 'type': 'savings', 'color': '#00B894'},
            ]
        },
        {
            'name': 'Freelancer Budget (KES)',
            'description': 'Budget for freelancers with variable income. Based on KES 150,000 monthly income.',
            'is_default': False,
            'categories': [
                {'name': 'Housing', 'amount': Decimal('35000'), 'type': 'expense', 'color': '#FF6B6B'},
                {'name': 'Business Expenses', 'amount': Decimal('20000'), 'type': 'expense', 'color': '#E17055'},
                {'name': 'Groceries', 'amount': Decimal('15000'), 'type': 'expense', 'color': '#45B7D1'},
                {'name': 'Transportation', 'amount': Decimal('8000'), 'type': 'expense', 'color': '#96CEB4'},
                {'name': 'Utilities & Internet', 'amount': Decimal('7000'), 'type': 'expense', 'color': '#4ECDC4'},
                {'name': 'Health Insurance', 'amount': Decimal('5000'), 'type': 'expense', 'color': '#FD79A8'},
                {'name': 'Professional Development', 'amount': Decimal('10000'), 'type': 'expense', 'color': '#A29BFE'},
                {'name': 'Entertainment', 'amount': Decimal('8000'), 'type': 'expense', 'color': '#FFEAA7'},
                {'name': 'Emergency Fund (6 months)', 'amount': Decimal('20000'), 'type': 'savings', 'color': '#00B894'},
                {'name': 'Tax Reserve', 'amount': Decimal('15000'), 'type': 'savings', 'color': '#00CEC9'},
                {'name': 'Retirement', 'amount': Decimal('7000'), 'type': 'savings', 'color': '#6C5CE7'},
            ]
        }
    ]

    created_templates = []

    for template_data in templates:
        # Create the template
        template = BudgetTemplate(
            user_id=user_id,
            name=template_data['name'],
            description=template_data['description'],
            is_default=template_data['is_default']
        )
        db.session.add(template)
        db.session.flush()  # Get the template ID

        # Create template items
        for category in template_data['categories']:
            item = BudgetTemplateItem(
                template_id=template.id,
                category_name=category['name'],  # Fixed: was 'name', should be 'category_name'
                allocated_amount=category['amount'],
                category_type=category['type'],
                color=category['color']
            )
            db.session.add(item)

        created_templates.append(template)

    db.session.commit()
    return created_templates


def create_templates_for_existing_users():
    """Create starter templates for all existing users who don't have any templates"""
    users = User.query.all()
    count = 0

    for user in users:
        # Check if user already has templates
        existing_templates = BudgetTemplate.query.filter_by(user_id=user.id).count()

        if existing_templates == 0:
            create_starter_templates(user.id)
            count += 1
            print(f"Created templates for user: {user.username}")

    print(f"Created starter templates for {count} users")
    return count


if __name__ == '__main__':
    from app import app

    with app.app_context():
        create_templates_for_existing_users()
