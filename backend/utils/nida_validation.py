"""
NIDA Validation Utility for Tanzania Fintech Platform
Handles National Identification Authority (NIDA) verification
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import httpx
import os
from backend.utils.redis_manager import redis_manager

logger = logging.getLogger(__name__)

class NIDAValidator:
    """NIDA validation service for Tanzania customers"""
    
    def __init__(self):
        self.base_url = os.getenv("NIDA_API_URL", "https://nida.go.tz/api")
        self.api_key = os.getenv("NIDA_API_KEY", "your-nida-api-key")
        self.timeout = 30  # seconds
        self.cache_ttl = 86400  # 24 hours cache for valid results
    
    async def validate_nida(self, nida_number: str) -> Dict[str, Any]:
        """
        Validate NIDA number with government database
        
        Args:
            nida_number: 20-digit NIDA number
            
        Returns:
            Dict containing validation result
        """
        try:
            # Basic format validation first
            if not self._validate_format(nida_number):
                return {
                    "valid": False,
                    "error": "Invalid NIDA format",
                    "verified_at": datetime.utcnow(),
                }
            
            # Check cache first
            cached_result = await self._get_cached_result(nida_number)
            if cached_result:
                logger.info(f"NIDA validation cache hit for: {nida_number[:8]}****")
                return cached_result
            
            # Call NIDA API
            api_result = await self._call_nida_api(nida_number)
            
            # Cache the result if valid
            if api_result.get("valid"):
                await self._cache_result(nida_number, api_result)
            
            return api_result
            
        except Exception as e:
            logger.error(f"NIDA validation error: {str(e)}")
            return {
                "valid": False,
                "error": f"Validation service error: {str(e)}",
                "verified_at": datetime.utcnow(),
            }
    
    def _validate_format(self, nida_number: str) -> bool:
        """Validate NIDA number format"""
        if not nida_number:
            return False
        
        # Remove any spaces or dashes
        clean_nida = nida_number.replace(" ", "").replace("-", "")
        
        # Must be exactly 20 digits
        if len(clean_nida) != 20:
            return False
        
        # Must be all digits
        if not clean_nida.isdigit():
            return False
        
        return True
    
    async def _get_cached_result(self, nida_number: str) -> Optional[Dict[str, Any]]:
        """Get cached NIDA validation result"""
        try:
            cache_key = f"nida_validation:{nida_number}"
            cached_data = await redis_manager.get_cache(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache retrieval error: {str(e)}")
            return None
    
    async def _cache_result(self, nida_number: str, result: Dict[str, Any]) -> None:
        """Cache NIDA validation result"""
        try:
            cache_key = f"nida_validation:{nida_number}"
            await redis_manager.set_cache(
                cache_key,
                json.dumps(result, default=str),
                ttl=self.cache_ttl
            )
            
        except Exception as e:
            logger.warning(f"Cache storage error: {str(e)}")
    
    async def _call_nida_api(self, nida_number: str) -> Dict[str, Any]:
        """Call NIDA government API for verification"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            payload = {
                "nida_number": nida_number,
                "verification_type": "basic",
                "request_id": f"tujenge_{int(datetime.utcnow().timestamp())}",
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/verify",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    api_data = response.json()
                    
                    # Process NIDA API response
                    return self._process_nida_response(api_data)
                
                elif response.status_code == 404:
                    return {
                        "valid": False,
                        "error": "NIDA number not found in government database",
                        "verified_at": datetime.utcnow(),
                    }
                
                elif response.status_code == 429:
                    return {
                        "valid": False,
                        "error": "NIDA service rate limit exceeded. Please try again later.",
                        "verified_at": datetime.utcnow(),
                    }
                
                else:
                    return {
                        "valid": False,
                        "error": f"NIDA service error: {response.status_code}",
                        "verified_at": datetime.utcnow(),
                    }
                    
        except httpx.TimeoutException:
            return {
                "valid": False,
                "error": "NIDA service timeout. Please try again.",
                "verified_at": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"NIDA API call error: {str(e)}")
            return {
                "valid": False,
                "error": f"NIDA verification failed: {str(e)}",
                "verified_at": datetime.utcnow(),
            }
    
    def _process_nida_response(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process NIDA API response"""
        try:
            # Standard NIDA API response format
            if api_data.get("status") == "success":
                verification_data = api_data.get("data", {})
                
                return {
                    "valid": True,
                    "verified_at": datetime.utcnow(),
                    "verification_id": api_data.get("verification_id"),
                    "person_details": {
                        "first_name": verification_data.get("first_name"),
                        "middle_name": verification_data.get("middle_name"), 
                        "last_name": verification_data.get("last_name"),
                        "date_of_birth": verification_data.get("date_of_birth"),
                        "gender": verification_data.get("gender"),
                        "nationality": verification_data.get("nationality", "Tanzanian"),
                    },
                    "document_status": verification_data.get("document_status", "active"),
                    "verification_level": "government_verified",
                }
            
            else:
                return {
                    "valid": False,
                    "error": api_data.get("message", "NIDA verification failed"),
                    "verified_at": datetime.utcnow(),
                }
                
        except Exception as e:
            logger.error(f"NIDA response processing error: {str(e)}")
            return {
                "valid": False,
                "error": "Error processing NIDA verification response",
                "verified_at": datetime.utcnow(),
            }
    
    async def bulk_validate(self, nida_numbers: list) -> Dict[str, Any]:
        """Bulk validate multiple NIDA numbers"""
        try:
            results = {}
            
            # Process in batches to avoid overwhelming the API
            batch_size = 10
            for i in range(0, len(nida_numbers), batch_size):
                batch = nida_numbers[i:i + batch_size]
                
                # Process batch concurrently
                tasks = [self.validate_nida(nida) for nida in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Collect results
                for nida, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        results[nida] = {
                            "valid": False,
                            "error": f"Validation error: {str(result)}",
                            "verified_at": datetime.utcnow(),
                        }
                    else:
                        results[nida] = result
                
                # Small delay between batches
                if i + batch_size < len(nida_numbers):
                    await asyncio.sleep(1)
            
            return {
                "bulk_validation": True,
                "total_processed": len(nida_numbers),
                "successful_validations": len([r for r in results.values() if r.get("valid")]),
                "failed_validations": len([r for r in results.values() if not r.get("valid")]),
                "results": results,
                "processed_at": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"Bulk NIDA validation error: {str(e)}")
            return {
                "bulk_validation": False,
                "error": f"Bulk validation failed: {str(e)}",
                "processed_at": datetime.utcnow(),
            }
    
    async def get_validation_statistics(self) -> Dict[str, Any]:
        """Get NIDA validation statistics"""
        try:
            # In real implementation, get from database/analytics
            return {
                "daily_validations": 245,
                "successful_validations": 230,
                "failed_validations": 15,
                "success_rate": 93.9,
                "average_response_time": 1.2,  # seconds
                "api_uptime": 99.5,  # percentage
                "last_updated": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"Statistics retrieval error: {str(e)}")
            return {
                "error": f"Statistics unavailable: {str(e)}",
                "last_updated": datetime.utcnow(),
            }

# Global instance
nida_validator = NIDAValidator() 