"""
Unit tests for configuration module
"""

import pytest
from backend.core.config import settings, TANZANIA_CONFIG, MOBILE_MONEY_PROVIDERS


def test_tanzania_config():
    """Test Tanzania-specific configuration"""
    assert TANZANIA_CONFIG["currency"] == "TZS"
    assert TANZANIA_CONFIG["timezone"] == "Africa/Dar_es_Salaam"
    assert TANZANIA_CONFIG["language"] == "sw"
    assert TANZANIA_CONFIG["phone_prefix"] == "+255"


def test_mobile_money_providers():
    """Test mobile money provider configuration"""
    assert "mpesa" in MOBILE_MONEY_PROVIDERS
    assert "airtel" in MOBILE_MONEY_PROVIDERS
    assert MOBILE_MONEY_PROVIDERS["mpesa"]["name"] == "M-Pesa"
    assert MOBILE_MONEY_PROVIDERS["airtel"]["name"] == "Airtel Money"


def test_settings_validation():
    """Test settings validation"""
    assert settings.APP_NAME == "Tujenge Platform"
    assert settings.DEFAULT_CURRENCY == "TZS"
    assert settings.JWT_ALGORITHM == "HS256"
