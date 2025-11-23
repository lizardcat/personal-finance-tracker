"""
Exchange Rates API endpoints
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from services.exchange_rate_service import exchange_rate_service
from decimal import Decimal

exchange_rates_bp = Blueprint('exchange_rates_api', __name__, url_prefix='/api/exchange-rates')

@exchange_rates_bp.route('/current', methods=['GET'])
@login_required
def get_current_rates():
    """Get current exchange rates for user's currency"""
    try:
        user_currency = current_user.default_currency or 'KES'

        # Common currencies to show
        currencies = ['USD', 'EUR', 'GBP', 'KES']

        # Remove user's currency from the list
        if user_currency in currencies:
            currencies.remove(user_currency)

        rates = {}
        for currency in currencies:
            try:
                rate = exchange_rate_service.get_rate(currency, user_currency)
                rates[currency] = {
                    'rate': float(rate),
                    'formatted': f"1 {currency} = {float(rate):.2f} {user_currency}"
                }
            except Exception as e:
                rates[currency] = {
                    'rate': None,
                    'error': str(e)
                }

        return jsonify({
            'base_currency': user_currency,
            'rates': rates,
            'last_updated': 'Live'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@exchange_rates_bp.route('/convert', methods=['POST'])
@login_required
def convert_currency():
    """Convert amount between currencies"""
    try:
        data = request.get_json()

        amount = Decimal(str(data.get('amount', 0)))
        from_currency = data.get('from_currency')
        to_currency = data.get('to_currency')

        if not amount or not from_currency or not to_currency:
            return jsonify({'error': 'Amount, from_currency, and to_currency are required'}), 400

        converted = exchange_rate_service.convert_amount(amount, from_currency, to_currency)
        rate = exchange_rate_service.get_rate(from_currency, to_currency)

        return jsonify({
            'original_amount': float(amount),
            'converted_amount': float(converted),
            'from_currency': from_currency,
            'to_currency': to_currency,
            'exchange_rate': float(rate),
            'formatted': f"{float(amount):.2f} {from_currency} = {float(converted):.2f} {to_currency}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@exchange_rates_bp.route('/all', methods=['GET'])
@login_required
def get_all_rates():
    """Get all available exchange rates"""
    try:
        user_currency = current_user.default_currency or 'KES'
        from config import Config

        all_currencies = Config.DEFAULT_CURRENCIES
        rates = {}

        for currency in all_currencies:
            if currency != user_currency:
                try:
                    rate = exchange_rate_service.get_rate(currency, user_currency)
                    rates[currency] = {
                        'rate': float(rate),
                        'name': Config.CURRENCY_NAMES.get(currency, currency),
                        'symbol': Config.CURRENCY_SYMBOLS.get(currency, currency)
                    }
                except Exception as e:
                    rates[currency] = {
                        'rate': None,
                        'error': str(e)
                    }

        return jsonify({
            'base_currency': user_currency,
            'rates': rates
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
