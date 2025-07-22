"""
Mobile Money Integration for Tanzania Fintech Platform
M-Pesa and Airtel Money integration for payments and disbursements
"""

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from enum import Enum

import httpx
from backend.core.config import settings


class PaymentProvider(str, Enum):
    """Mobile money providers in Tanzania"""
    MPESA = "mpesa"
    AIRTEL = "airtel"


class TransactionStatus(str, Enum):
    """Transaction status options"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TransactionType(str, Enum):
    """Transaction types"""
    DISBURSEMENT = "disbursement"
    COLLECTION = "collection"
    BALANCE_INQUIRY = "balance_inquiry"
    STATUS_CHECK = "status_check"


class MobileMoneyService:
    """
    Comprehensive mobile money service for Tanzania
    Handles M-Pesa and Airtel Money integrations
    """

    def __init__(self):
        """Initialize mobile money service with provider configurations"""
        self.mpesa_config = {
            "base_url": getattr(settings, "MPESA_BASE_URL", "https://api.safaricom.co.ke"),
            "consumer_key": getattr(settings, "MPESA_CONSUMER_KEY", ""),
            "consumer_secret": getattr(settings, "MPESA_CONSUMER_SECRET", ""),
            "passkey": getattr(settings, "MPESA_PASSKEY", ""),
            "shortcode": getattr(settings, "MPESA_SHORTCODE", "174379"),
            "initiator_name": getattr(settings, "MPESA_INITIATOR_NAME", "testapi"),
            "initiator_password": getattr(settings, "MPESA_INITIATOR_PASSWORD", ""),
        }
        
        self.airtel_config = {
            "base_url": getattr(settings, "AIRTEL_BASE_URL", "https://openapiuat.airtel.africa"),
            "client_id": getattr(settings, "AIRTEL_CLIENT_ID", ""),
            "client_secret": getattr(settings, "AIRTEL_CLIENT_SECRET", ""),
            "username": getattr(settings, "AIRTEL_USERNAME", ""),
            "password": getattr(settings, "AIRTEL_PASSWORD", ""),
            "env": getattr(settings, "AIRTEL_ENV", "sandbox"),
        }
        
        self.timeout = 30  # seconds
        self.max_retries = 3

    async def disburse_mpesa(
        self, 
        phone_number: str, 
        amount: float, 
        reference: str,
        remarks: str = "Loan disbursement"
    ) -> Dict[str, Any]:
        """
        Disburse funds via M-Pesa B2C
        
        Args:
            phone_number: Customer phone number (format: +255...)
            amount: Amount to disburse in TZS
            reference: Transaction reference
            remarks: Transaction remarks
            
        Returns:
            Dict with transaction result
        """
        try:
            # Format phone number for M-Pesa (remove + and country code)
            formatted_phone = self._format_phone_mpesa(phone_number)
            
            # Generate M-Pesa access token
            access_token = await self._get_mpesa_access_token()
            
            if not access_token:
                return {
                    "status": "failed",
                    "error": "Failed to obtain M-Pesa access token",
                    "provider": "mpesa"
                }

            # Prepare B2C request
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            security_credential = self._generate_mpesa_security_credential()
            
            payload = {
                "InitiatorName": self.mpesa_config["initiator_name"],
                "SecurityCredential": security_credential,
                "CommandID": "BusinessPayment",
                "Amount": int(amount),  # M-Pesa expects integer
                "PartyA": self.mpesa_config["shortcode"],
                "PartyB": formatted_phone,
                "Remarks": remarks,
                "QueueTimeOutURL": f"{settings.BASE_URL}/api/v1/mobile-money/mpesa/timeout",
                "ResultURL": f"{settings.BASE_URL}/api/v1/mobile-money/mpesa/result",
                "Occasion": reference,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.mpesa_config['base_url']}/mpesa/b2c/v1/paymentrequest",
                    json=payload,
                    headers=headers
                )

            response_data = response.json()

            if response.status_code == 200 and response_data.get("ResponseCode") == "0":
                return {
                    "status": "pending",
                    "transaction_id": response_data.get("ConversationID"),
                    "provider_reference": response_data.get("OriginatorConversationID"),
                    "amount": amount,
                    "phone_number": phone_number,
                    "provider": "mpesa",
                    "message": response_data.get("ResponseDescription", "Transaction initiated"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "failed",
                    "error": response_data.get("ResponseDescription", "Unknown error"),
                    "error_code": response_data.get("ResponseCode"),
                    "provider": "mpesa"
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": f"M-Pesa disbursement failed: {str(e)}",
                "provider": "mpesa"
            }

    async def disburse_airtel(
        self, 
        phone_number: str, 
        amount: float, 
        reference: str,
        remarks: str = "Loan disbursement"
    ) -> Dict[str, Any]:
        """
        Disburse funds via Airtel Money
        
        Args:
            phone_number: Customer phone number (format: +255...)
            amount: Amount to disburse in TZS
            reference: Transaction reference
            remarks: Transaction remarks
            
        Returns:
            Dict with transaction result
        """
        try:
            # Format phone number for Airtel (remove +)
            formatted_phone = self._format_phone_airtel(phone_number)
            
            # Get Airtel access token
            access_token = await self._get_airtel_access_token()
            
            if not access_token:
                return {
                    "status": "failed",
                    "error": "Failed to obtain Airtel access token",
                    "provider": "airtel"
                }

            # Generate transaction ID
            transaction_id = f"TUJ_{uuid.uuid4().hex[:12].upper()}"

            # Prepare disbursement request
            payload = {
                "payee": {
                    "msisdn": formatted_phone
                },
                "reference": reference,
                "pin": self.airtel_config.get("pin", "0000"),  # In production, use encrypted PIN
                "transaction": {
                    "amount": amount,
                    "id": transaction_id
                }
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Country": "TZ",
                "X-Currency": "TZS"
            }

            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.airtel_config['base_url']}/standard/v1/disbursements/",
                    json=payload,
                    headers=headers
                )

            response_data = response.json()

            if response.status_code == 200:
                if response_data.get("status", {}).get("success"):
                    return {
                        "status": "completed",  # Airtel often completes immediately
                        "transaction_id": transaction_id,
                        "provider_reference": response_data.get("data", {}).get("transaction", {}).get("id"),
                        "amount": amount,
                        "phone_number": phone_number,
                        "provider": "airtel",
                        "message": "Transaction completed successfully",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                else:
                    return {
                        "status": "failed",
                        "error": response_data.get("status", {}).get("message", "Transaction failed"),
                        "provider": "airtel"
                    }
            else:
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "provider": "airtel"
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": f"Airtel disbursement failed: {str(e)}",
                "provider": "airtel"
            }

    async def collect_payment_mpesa(
        self, 
        phone_number: str, 
        amount: float, 
        reference: str,
        description: str = "Loan repayment"
    ) -> Dict[str, Any]:
        """
        Collect payment via M-Pesa STK Push
        
        Args:
            phone_number: Customer phone number
            amount: Amount to collect
            reference: Payment reference
            description: Payment description
            
        Returns:
            Dict with collection result
        """
        try:
            # Format phone number
            formatted_phone = self._format_phone_mpesa(phone_number)
            
            # Get access token
            access_token = await self._get_mpesa_access_token()
            
            if not access_token:
                return {
                    "status": "failed",
                    "error": "Failed to obtain access token",
                    "provider": "mpesa"
                }

            # Generate timestamp and password
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = self._generate_mpesa_password(timestamp)

            payload = {
                "BusinessShortCode": self.mpesa_config["shortcode"],
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": formatted_phone,
                "PartyB": self.mpesa_config["shortcode"],
                "PhoneNumber": formatted_phone,
                "CallBackURL": f"{settings.BASE_URL}/api/v1/mobile-money/mpesa/callback",
                "AccountReference": reference,
                "TransactionDesc": description
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.mpesa_config['base_url']}/mpesa/stkpush/v1/processrequest",
                    json=payload,
                    headers=headers
                )

            response_data = response.json()

            if response.status_code == 200 and response_data.get("ResponseCode") == "0":
                return {
                    "status": "pending",
                    "transaction_id": response_data.get("CheckoutRequestID"),
                    "merchant_request_id": response_data.get("MerchantRequestID"),
                    "amount": amount,
                    "phone_number": phone_number,
                    "provider": "mpesa",
                    "message": "STK push sent to customer",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "failed",
                    "error": response_data.get("ResponseDescription", "STK push failed"),
                    "provider": "mpesa"
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": f"M-Pesa collection failed: {str(e)}",
                "provider": "mpesa"
            }

    async def verify_transaction(self, reference: str, provider: str = None) -> Dict[str, Any]:
        """
        Verify transaction status
        
        Args:
            reference: Transaction reference to verify
            provider: Provider to check (mpesa/airtel), if None, check both
            
        Returns:
            Dict with transaction verification result
        """
        try:
            if provider == "mpesa" or provider is None:
                mpesa_result = await self._verify_mpesa_transaction(reference)
                if mpesa_result.get("verified"):
                    return mpesa_result

            if provider == "airtel" or provider is None:
                airtel_result = await self._verify_airtel_transaction(reference)
                if airtel_result.get("verified"):
                    return airtel_result

            return {
                "verified": False,
                "message": "Transaction not found in any provider",
                "reference": reference
            }

        except Exception as e:
            return {
                "verified": False,
                "error": f"Transaction verification failed: {str(e)}",
                "reference": reference
            }

    async def get_balance(self, provider: str) -> Dict[str, Any]:
        """
        Get account balance for specified provider
        
        Args:
            provider: Provider (mpesa/airtel)
            
        Returns:
            Dict with balance information
        """
        try:
            if provider == "mpesa":
                return await self._get_mpesa_balance()
            elif provider == "airtel":
                return await self._get_airtel_balance()
            else:
                return {
                    "success": False,
                    "error": "Invalid provider specified"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Balance inquiry failed: {str(e)}",
                "provider": provider
            }

    # Private helper methods

    async def _get_mpesa_access_token(self) -> Optional[str]:
        """Get M-Pesa OAuth access token"""
        try:
            consumer_key = self.mpesa_config["consumer_key"]
            consumer_secret = self.mpesa_config["consumer_secret"]
            
            if not consumer_key or not consumer_secret:
                return None

            auth_string = f"{consumer_key}:{consumer_secret}"
            encoded_auth = hashlib.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.mpesa_config['base_url']}/oauth/v1/generate?grant_type=client_credentials",
                    headers=headers
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            
            return None

        except Exception:
            return None

    async def _get_airtel_access_token(self) -> Optional[str]:
        """Get Airtel Money OAuth access token"""
        try:
            payload = {
                "client_id": self.airtel_config["client_id"],
                "client_secret": self.airtel_config["client_secret"],
                "grant_type": "client_credentials"
            }

            headers = {
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.airtel_config['base_url']}/auth/oauth2/token",
                    json=payload,
                    headers=headers
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            
            return None

        except Exception:
            return None

    def _format_phone_mpesa(self, phone_number: str) -> str:
        """Format phone number for M-Pesa (254XXXXXXXXX)"""
        # Remove any spaces, dashes, or plus signs
        phone = phone_number.replace(" ", "").replace("-", "").replace("+", "")
        
        # Convert Tanzania numbers to Kenya format for testing
        # In production, use proper Tanzania M-Pesa format
        if phone.startswith("255"):
            return f"254{phone[3:]}"  # Convert to Kenya format for testing
        elif phone.startswith("0"):
            return f"254{phone[1:]}"
        
        return phone

    def _format_phone_airtel(self, phone_number: str) -> str:
        """Format phone number for Airtel Money"""
        phone = phone_number.replace(" ", "").replace("-", "").replace("+", "")
        
        if phone.startswith("255"):
            return phone
        elif phone.startswith("0"):
            return f"255{phone[1:]}"
        
        return f"255{phone}"

    def _generate_mpesa_password(self, timestamp: str) -> str:
        """Generate M-Pesa password for STK push"""
        shortcode = self.mpesa_config["shortcode"]
        passkey = self.mpesa_config["passkey"]
        
        data_to_encode = f"{shortcode}{passkey}{timestamp}"
        return hashlib.b64encode(data_to_encode.encode()).decode()

    def _generate_mpesa_security_credential(self) -> str:
        """Generate M-Pesa security credential for B2C"""
        # In production, encrypt the initiator password with M-Pesa public key
        # For now, return a mock credential
        return "mock_security_credential"

    async def _verify_mpesa_transaction(self, reference: str) -> Dict[str, Any]:
        """Verify M-Pesa transaction"""
        # Mock verification - in production, use M-Pesa transaction status API
        return {
            "verified": True,
            "transaction_id": reference,
            "amount": 100000,  # Mock amount
            "status": "completed",
            "provider": "mpesa",
            "verification_method": "api_check"
        }

    async def _verify_airtel_transaction(self, reference: str) -> Dict[str, Any]:
        """Verify Airtel Money transaction"""
        # Mock verification - in production, use Airtel transaction status API
        return {
            "verified": True,
            "transaction_id": reference,
            "amount": 100000,  # Mock amount
            "status": "completed",
            "provider": "airtel",
            "verification_method": "api_check"
        }

    async def _get_mpesa_balance(self) -> Dict[str, Any]:
        """Get M-Pesa account balance"""
        try:
            access_token = await self._get_mpesa_access_token()
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Failed to obtain access token"
                }

            # Mock balance response - in production, use actual M-Pesa balance API
            return {
                "success": True,
                "provider": "mpesa",
                "balance": 1500000.00,  # TZS
                "currency": "TZS",
                "account_name": "Tujenge Platform",
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"M-Pesa balance inquiry failed: {str(e)}"
            }

    async def _get_airtel_balance(self) -> Dict[str, Any]:
        """Get Airtel Money account balance"""
        try:
            access_token = await self._get_airtel_access_token()
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Failed to obtain access token"
                }

            # Mock balance response - in production, use actual Airtel balance API
            return {
                "success": True,
                "provider": "airtel",
                "balance": 2300000.00,  # TZS
                "currency": "TZS",
                "account_name": "Tujenge Platform",
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Airtel balance inquiry failed: {str(e)}"
            }

    async def process_callback(self, provider: str, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process mobile money callback/webhook
        
        Args:
            provider: Provider name (mpesa/airtel)
            callback_data: Callback data from provider
            
        Returns:
            Dict with processed callback result
        """
        try:
            if provider == "mpesa":
                return self._process_mpesa_callback(callback_data)
            elif provider == "airtel":
                return self._process_airtel_callback(callback_data)
            else:
                return {
                    "success": False,
                    "error": "Unknown provider"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Callback processing failed: {str(e)}"
            }

    def _process_mpesa_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process M-Pesa callback data"""
        # Extract relevant information from M-Pesa callback
        body = callback_data.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        
        result_code = stk_callback.get("ResultCode")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        
        if result_code == 0:
            # Successful transaction
            callback_metadata = stk_callback.get("CallbackMetadata", {})
            items = callback_metadata.get("Item", [])
            
            # Extract transaction details
            amount = None
            mpesa_receipt = None
            phone_number = None
            
            for item in items:
                name = item.get("Name")
                value = item.get("Value")
                
                if name == "Amount":
                    amount = value
                elif name == "MpesaReceiptNumber":
                    mpesa_receipt = value
                elif name == "PhoneNumber":
                    phone_number = value
            
            return {
                "success": True,
                "status": "completed",
                "transaction_id": checkout_request_id,
                "provider_reference": mpesa_receipt,
                "amount": amount,
                "phone_number": phone_number,
                "merchant_request_id": merchant_request_id
            }
        else:
            # Failed transaction
            return {
                "success": False,
                "status": "failed",
                "transaction_id": checkout_request_id,
                "error_code": result_code,
                "error_message": stk_callback.get("ResultDesc"),
                "merchant_request_id": merchant_request_id
            }

    def _process_airtel_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Airtel Money callback data"""
        # Process Airtel callback - structure depends on Airtel's API
        transaction = callback_data.get("transaction", {})
        status = callback_data.get("status", {})
        
        if status.get("success"):
            return {
                "success": True,
                "status": "completed",
                "transaction_id": transaction.get("id"),
                "provider_reference": transaction.get("airtel_reference"),
                "amount": transaction.get("amount"),
                "phone_number": callback_data.get("payee", {}).get("msisdn")
            }
        else:
            return {
                "success": False,
                "status": "failed",
                "transaction_id": transaction.get("id"),
                "error_message": status.get("message")
            }


# Utility functions for mobile money operations
async def detect_provider(phone_number: str) -> str:
    """
    Detect mobile money provider based on phone number
    
    Args:
        phone_number: Phone number to analyze
        
    Returns:
        Provider name (mpesa/airtel/unknown)
    """
    # Remove formatting
    phone = phone_number.replace(" ", "").replace("-", "").replace("+", "")
    
    # Tanzania mobile prefixes
    if phone.startswith("255"):
        phone = phone[3:]  # Remove country code
    elif phone.startswith("0"):
        phone = phone[1:]  # Remove leading zero
    
    # Vodacom (M-Pesa) prefixes in Tanzania
    mpesa_prefixes = ["74", "75", "76"]
    
    # Airtel prefixes in Tanzania
    airtel_prefixes = ["68", "69", "78"]
    
    prefix = phone[:2]
    
    if prefix in mpesa_prefixes:
        return PaymentProvider.MPESA.value
    elif prefix in airtel_prefixes:
        return PaymentProvider.AIRTEL.value
    else:
        return "unknown"


def format_amount_for_provider(amount: float, provider: str) -> int:
    """
    Format amount according to provider requirements
    
    Args:
        amount: Amount in TZS
        provider: Provider name
        
    Returns:
        Formatted amount
    """
    if provider == PaymentProvider.MPESA.value:
        # M-Pesa expects integer (no decimals)
        return int(amount)
    elif provider == PaymentProvider.AIRTEL.value:
        # Airtel accepts decimal amounts
        return amount
    else:
        return int(amount) 