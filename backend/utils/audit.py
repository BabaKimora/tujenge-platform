"""
Audit Logger for Tujenge Platform
Comprehensive audit logging for security and compliance
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request
import asyncio
from enum import Enum
from backend.config import settings

class AuditEventType(str, Enum):
    """Types of audit events"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_ERROR = "login_error"
    USER_LOGOUT = "user_logout"
    USER_LOGOUT_ALL = "user_logout_all"
    TOKEN_REFRESHED = "token_refreshed"
    
    # User management events
    USER_REGISTERED = "user_registered"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    
    # Password events
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    PASSWORD_CHANGED = "password_changed"
    
    # Tenant events
    TENANT_CREATED = "tenant_created"
    TENANT_UPDATED = "tenant_updated"
    TENANT_SETTINGS_CHANGED = "tenant_settings_changed"
    
    # Loan events
    LOAN_APPLICATION_CREATED = "loan_application_created"
    LOAN_APPLICATION_UPDATED = "loan_application_updated"
    LOAN_APPROVED = "loan_approved"
    LOAN_REJECTED = "loan_rejected"
    LOAN_DISBURSED = "loan_disbursed"
    LOAN_REPAYMENT_MADE = "loan_repayment_made"
    
    # Customer events
    CUSTOMER_CREATED = "customer_created"
    CUSTOMER_UPDATED = "customer_updated"
    CUSTOMER_DELETED = "customer_deleted"
    CUSTOMER_VERIFIED = "customer_verified"
    
    # Financial events
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_PROCESSED = "transaction_processed"
    TRANSACTION_FAILED = "transaction_failed"
    MOBILE_MONEY_TRANSACTION = "mobile_money_transaction"
    
    # System events
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    SYSTEM_MAINTENANCE = "system_maintenance"
    
    # Security events
    SECURITY_BREACH_ATTEMPT = "security_breach_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PERMISSION_DENIED = "permission_denied"
    
    # Integration events
    NIDA_VERIFICATION = "nida_verification"
    TIN_VERIFICATION = "tin_verification"
    MPESA_API_CALL = "mpesa_api_call"
    AIRTEL_API_CALL = "airtel_api_call"

class AuditLogger:
    """Audit logging service for security and compliance"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.enabled = settings.AUDIT_LOG_ENABLED
        
        # Setup audit-specific logger
        if self.enabled:
            # Create file handler for audit logs
            audit_handler = logging.FileHandler("logs/audit.log")
            audit_formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
            audit_handler.setFormatter(audit_formatter)
            self.logger.addHandler(audit_handler)
            self.logger.setLevel(logging.INFO)
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        severity: str = "INFO"
    ):
        """Log an audit event"""
        if not self.enabled:
            return
        
        try:
            audit_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "severity": severity,
                "details": details or {},
            }
            
            # Add request information if available
            if request:
                audit_data.update({
                    "ip_address": request.client.host,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "method": request.method,
                    "path": str(request.url.path),
                    "query_params": dict(request.query_params) if request.query_params else None,
                })
            
            # Log the audit event
            self.logger.info(json.dumps(audit_data, default=str))
            
            # For critical events, also log to main logger
            if severity in ["ERROR", "CRITICAL"]:
                main_logger = logging.getLogger(__name__)
                main_logger.warning(f"Security audit event: {event_type} - {details}")
                
        except Exception as e:
            # Don't let audit logging failures break the application
            main_logger = logging.getLogger(__name__)
            main_logger.error(f"Audit logging failed: {str(e)}")
    
    async def log_security_event(
        self,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None
    ):
        """Log a security-related event"""
        await self.log_event(
            event_type=AuditEventType(event_type),
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
            request=request,
            severity="WARNING"
        )
    
    async def log_user_action(
        self,
        action: str,
        user_id: int,
        tenant_id: int,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log a user action"""
        await self.log_event(
            event_type=AuditEventType(action),
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
            request=request,
            severity="INFO"
        )
    
    async def log_financial_event(
        self,
        event_type: str,
        amount: float,
        currency: str,
        user_id: int,
        tenant_id: int,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log a financial event"""
        financial_details = {
            "amount": amount,
            "currency": currency,
            **(details or {})
        }
        
        await self.log_event(
            event_type=AuditEventType(event_type),
            user_id=user_id,
            tenant_id=tenant_id,
            details=financial_details,
            request=request,
            severity="INFO"
        )
    
    async def log_integration_event(
        self,
        service: str,
        operation: str,
        success: bool,
        response_time: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None
    ):
        """Log an integration event"""
        integration_details = {
            "service": service,
            "operation": operation,
            "success": success,
            "response_time_ms": response_time,
            **(details or {})
        }
        
        event_type = f"{service.lower()}_api_call"
        severity = "INFO" if success else "ERROR"
        
        await self.log_event(
            event_type=AuditEventType(event_type),
            user_id=user_id,
            tenant_id=tenant_id,
            details=integration_details,
            severity=severity
        )
    
    async def log_data_access(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        user_id: int,
        tenant_id: int,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log data access for compliance"""
        access_details = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            **(details or {})
        }
        
        await self.log_event(
            event_type=AuditEventType.CUSTOMER_UPDATED,  # Generic data access
            user_id=user_id,
            tenant_id=tenant_id,
            details=access_details,
            severity="INFO"
        )
    
    async def log_compliance_event(
        self,
        regulation: str,
        event_type: str,
        compliance_status: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None
    ):
        """Log compliance-related events"""
        compliance_details = {
            "regulation": regulation,
            "compliance_status": compliance_status,
            **(details or {})
        }
        
        severity = "WARNING" if compliance_status == "non_compliant" else "INFO"
        
        await self.log_event(
            event_type=AuditEventType(event_type),
            user_id=user_id,
            tenant_id=tenant_id,
            details=compliance_details,
            severity=severity
        )
    
    def create_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[list] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create an audit report for a specific time period"""
        # This would typically query a database or parse log files
        # For now, return a basic structure
        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "filters": {
                "event_types": event_types,
                "user_id": user_id,
                "tenant_id": tenant_id
            },
            "summary": {
                "total_events": 0,
                "by_type": {},
                "by_user": {},
                "by_tenant": {}
            },
            "events": []
        }

# Initialize audit logger
audit_logger = AuditLogger()

# Ensure logs directory exists
import os
os.makedirs("logs", exist_ok=True) 