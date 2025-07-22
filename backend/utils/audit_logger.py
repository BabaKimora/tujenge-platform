"""
Tujenge Platform - Audit Logger
Enterprise audit logging for Tanzania banking compliance
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Enterprise audit logger for Tanzania banking compliance
    Records all user actions and system events for regulatory compliance
    """
    
    def __init__(self):
        self.logger = logging.getLogger("tujenge.audit")
        self.logger.setLevel(logging.INFO)
        
        # In production, this would log to a secure audit database
        # For now, we'll use file logging
        handler = logging.FileHandler("logs/audit.log", mode='a')
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    async def log_event(
        self,
        user_id: Optional[str] = None,
        action: str = "",
        resource_type: str = "",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Log an audit event for compliance tracking
        
        Args:
            user_id: ID of the user performing the action
            action: Action being performed (e.g., 'customer_created', 'loan_approved')
            resource_type: Type of resource being acted upon (e.g., 'customer', 'loan')
            resource_id: ID of the specific resource
            details: Additional details about the action
            ip_address: IP address of the user
            user_agent: User agent string
            session_id: Session ID
            
        Returns:
            audit_id: Unique ID for this audit event
        """
        audit_id = str(uuid4())
        
        audit_event = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "session_id": session_id,
            "compliance_level": "banking",  # Tanzania banking regulations
            "retention_period": "7_years",  # Tanzania requirement
        }
        
        # Log to audit system
        self.logger.info(json.dumps(audit_event, default=str))
        
        # In production, also save to secure audit database
        # await self._save_to_audit_db(audit_event)
        
        return audit_id
    
    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log security-related events"""
        return await self.log_event(
            user_id=user_id,
            action=f"security_{event_type}",
            resource_type="security",
            details={
                "event_type": event_type,
                "severity": severity,
                "description": description,
                "additional_data": additional_data or {},
            },
            ip_address=ip_address,
        )
    
    async def log_compliance_event(
        self,
        compliance_type: str,
        status: str,
        customer_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log compliance-related events for Tanzania regulations"""
        return await self.log_event(
            action=f"compliance_{compliance_type}",
            resource_type="compliance",
            resource_id=customer_id,
            details={
                "compliance_type": compliance_type,
                "status": status,
                "regulatory_framework": "tanzania_banking",
                **( details or {}),
            },
        )
    
    async def log_transaction_event(
        self,
        transaction_id: str,
        customer_id: str,
        amount: float,
        transaction_type: str,
        status: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log transaction events for financial compliance"""
        return await self.log_event(
            user_id=user_id,
            action=f"transaction_{status}",
            resource_type="transaction",
            resource_id=transaction_id,
            details={
                "customer_id": customer_id,
                "amount": amount,
                "currency": "TZS",
                "transaction_type": transaction_type,
                "status": status,
                **( details or {}),
            },
        )

# Global audit logger instance
audit_logger = AuditLogger() 