import requests
from models import db, ExchangeRate
from decimal import Decimal
from datetime import datetime, timedelta
from config import Config
import logging

logger = logging.getLogger(__name__)

class ExchangeRateService:
    """Service for managing exchange rates"""

    def __init__(self):
        self.api_key = Config.EXCHANGE_API_KEY
        self.cache_duration = timedelta(hours=1)  # Cache rates for 1 hour

        # Create persistent HTTP session with connection pooling to prevent connection leaks
        self.session = requests.Session()
        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def get_rate(self, base_currency, target_currency):
        """Get exchange rate between two currencies"""
        if base_currency == target_currency:
            return Decimal('1.0')
        
        # Check cache first
        cached_rate = ExchangeRate.query.filter_by(
            base_currency=base_currency,
            target_currency=target_currency
        ).first()
        
        if cached_rate and self._is_rate_fresh(cached_rate):
            return cached_rate.rate
        
        # Fetch from API if not cached or stale
        try:
            rate = self._fetch_rate_from_api(base_currency, target_currency)
            self._update_cached_rate(base_currency, target_currency, rate)
            return rate
        except Exception as e:
            logger.error(f"Failed to fetch exchange rate: {e}")
            # Return cached rate if available, even if stale
            if cached_rate:
                return cached_rate.rate
            # Return default rate as fallback
            return self._get_default_rate(base_currency, target_currency)
    
    def convert_amount(self, amount, from_currency, to_currency):
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount
        
        rate = self.get_rate(from_currency, to_currency)
        return amount * rate
    
    def update_all_rates(self):
        """Update all cached exchange rates"""
        currency_pairs = [
            ('USD', 'KES'),
            ('KES', 'USD'),
            ('USD', 'EUR'),
            ('EUR', 'USD'),
            ('USD', 'GBP'),
            ('GBP', 'USD'),
            ('EUR', 'GBP'),
            ('GBP', 'EUR'),
            ('KES', 'EUR'),
            ('EUR', 'KES'),
        ]
        
        updated_count = 0
        for base, target in currency_pairs:
            try:
                rate = self._fetch_rate_from_api(base, target)
                self._update_cached_rate(base, target, rate)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update rate {base}/{target}: {e}")
        
        logger.info(f"Updated {updated_count} exchange rates")
        return updated_count
    
    def get_supported_currencies(self):
        """Get list of supported currencies"""
        return Config.DEFAULT_CURRENCIES
    
    def _fetch_rate_from_api(self, base_currency, target_currency):
        """Fetch exchange rate from external API (V6)"""
        if not self.api_key:
            raise Exception("Exchange rate API Key not configured")

        # V6 URL structure: v6/API_KEY/latest/BASE_CURRENCY
        url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest/{base_currency}"

        # Use persistent session instead of requests.get to enable connection pooling
        # No headers needed - API key is in URL path
        response = self.session.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Check for API errors
        if data.get('result') == 'error':
            error_type = data.get('error-type', 'unknown')
            raise Exception(f"Exchange rate API error: {error_type}")

        # V6 API response structure has conversion_rates instead of rates
        if 'conversion_rates' not in data or target_currency not in data['conversion_rates']:
            raise Exception(f"Rate for {target_currency} not found in response")

        rate = Decimal(str(data['conversion_rates'][target_currency]))
        return rate
    
    def _update_cached_rate(self, base_currency, target_currency, rate):
        """Update cached exchange rate in database"""
        cached_rate = ExchangeRate.query.filter_by(
            base_currency=base_currency,
            target_currency=target_currency
        ).first()
        
        if cached_rate:
            cached_rate.rate = rate
            cached_rate.updated_at = datetime.utcnow()
        else:
            cached_rate = ExchangeRate(
                base_currency=base_currency,
                target_currency=target_currency,
                rate=rate
            )
            db.session.add(cached_rate)
        
        db.session.commit()
    
    def _is_rate_fresh(self, cached_rate):
        """Check if cached rate is still fresh"""
        if not cached_rate.updated_at:
            return False
        
        age = datetime.utcnow() - cached_rate.updated_at
        return age < self.cache_duration
    
    def _get_default_rate(self, base_currency, target_currency):
        """Get default exchange rate as fallback (approximate rates as of 2024)"""
        default_rates = {
            # USD pairs
            ('USD', 'EUR'): Decimal('0.92'),
            ('USD', 'GBP'): Decimal('0.79'),
            ('USD', 'KES'): Decimal('150.0'),
            ('USD', 'TSH'): Decimal('2500.0'),
            ('USD', 'CAD'): Decimal('1.35'),
            ('USD', 'AUD'): Decimal('1.52'),
            ('USD', 'JPY'): Decimal('148.0'),
            ('USD', 'CNY'): Decimal('7.24'),
            ('USD', 'INR'): Decimal('83.0'),
            ('USD', 'ZAR'): Decimal('18.5'),
            ('USD', 'NGN'): Decimal('1550.0'),
            ('USD', 'GHS'): Decimal('12.0'),
            ('USD', 'UGX'): Decimal('3700.0'),
            ('USD', 'CHF'): Decimal('0.88'),
            ('USD', 'SEK'): Decimal('10.5'),
            ('USD', 'NOK'): Decimal('10.6'),
            ('USD', 'DKK'): Decimal('6.85'),
            ('USD', 'NZD'): Decimal('1.64'),
            ('USD', 'SGD'): Decimal('1.34'),
            ('USD', 'HKD'): Decimal('7.82'),
            ('USD', 'MXN'): Decimal('17.0'),
            ('USD', 'BRL'): Decimal('4.95'),
            ('USD', 'AED'): Decimal('3.67'),
            ('USD', 'SAR'): Decimal('3.75'),

            # EUR pairs
            ('EUR', 'USD'): Decimal('1.09'),
            ('EUR', 'GBP'): Decimal('0.86'),
            ('EUR', 'KES'): Decimal('163.0'),
            ('EUR', 'TSH'): Decimal('2720.0'),

            # GBP pairs
            ('GBP', 'USD'): Decimal('1.27'),
            ('GBP', 'EUR'): Decimal('1.16'),
            ('GBP', 'KES'): Decimal('190.0'),

            # East African pairs
            ('KES', 'USD'): Decimal('0.0067'),
            ('KES', 'EUR'): Decimal('0.0061'),
            ('KES', 'TSH'): Decimal('16.67'),
            ('TSH', 'USD'): Decimal('0.0004'),
            ('TSH', 'KES'): Decimal('0.06'),
            ('UGX', 'USD'): Decimal('0.00027'),
            ('UGX', 'KES'): Decimal('0.041'),
        }

        rate = default_rates.get((base_currency, target_currency))
        if rate:
            return rate

        # If no direct rate, try reverse rate
        reverse_rate = default_rates.get((target_currency, base_currency))
        if reverse_rate and reverse_rate > 0:
            return Decimal('1.0') / reverse_rate

        # Ultimate fallback
        return Decimal('1.0')

# Create singleton instance
exchange_rate_service = ExchangeRateService()