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
        self.api_url = Config.EXCHANGE_API_URL
        self.cache_duration = timedelta(hours=1)  # Cache rates for 1 hour
    
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
        """Fetch exchange rate from external API"""
        if not self.api_url:
            raise Exception("Exchange rate API URL not configured")
        
        url = f"{self.api_url}{base_currency}"
        
        headers = {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'rates' not in data or target_currency not in data['rates']:
            raise Exception(f"Rate for {target_currency} not found in response")
        
        rate = Decimal(str(data['rates'][target_currency]))
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
        """Get default exchange rate as fallback"""
        default_rates = {
            ('USD', 'KES'): Decimal('150.0'),
            ('KES', 'USD'): Decimal('0.0067'),
            ('USD', 'EUR'): Decimal('0.85'),
            ('EUR', 'USD'): Decimal('1.18'),
            ('USD', 'GBP'): Decimal('0.73'),
            ('GBP', 'USD'): Decimal('1.37'),
            ('EUR', 'GBP'): Decimal('0.86'),
            ('GBP', 'EUR'): Decimal('1.16'),
            ('KES', 'EUR'): Decimal('0.0057'),
            ('EUR', 'KES'): Decimal('175.0'),
        }
        
        rate = default_rates.get((base_currency, target_currency))
        if rate:
            return rate
        
        # If no direct rate, try reverse rate
        reverse_rate = default_rates.get((target_currency, base_currency))
        if reverse_rate:
            return Decimal('1.0') / reverse_rate
        
        # Ultimate fallback
        return Decimal('1.0')

# Create singleton instance
exchange_rate_service = ExchangeRateService()