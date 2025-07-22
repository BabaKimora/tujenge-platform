"""
Validation utilities for Tanzania-specific data
"""

import re
from typing import Optional

def validate_phone_number(phone_number: str) -> bool:
    """Validate Tanzania phone number format"""
    if not phone_number:
        return False
    
    # Tanzania phone number patterns
    patterns = [
        r'^\+255[67]\d{8}$',      # +255612345678 or +255712345678
        r'^255[67]\d{8}$',        # 255612345678 or 255712345678
        r'^0[67]\d{8}$',          # 0612345678 or 0712345678
    ]
    
    return any(re.match(pattern, phone_number) for pattern in patterns)

def normalize_phone_number(phone_number: str) -> str:
    """Normalize phone number to +255 format"""
    if not phone_number:
        return phone_number
    
    # Remove any spaces or dashes
    phone_number = re.sub(r'[\s\-]', '', phone_number)
    
    # Convert to +255 format
    if phone_number.startswith('0'):
        return '+255' + phone_number[1:]
    elif phone_number.startswith('255'):
        return '+' + phone_number
    elif phone_number.startswith('+255'):
        return phone_number
    
    return phone_number

def validate_nida_number(nida_number: str) -> bool:
    """Validate NIDA number format"""
    if not nida_number:
        return True  # NIDA is optional
    
    # NIDA number should be exactly 20 digits
    return len(nida_number) == 20 and nida_number.isdigit()

def validate_tin_number(tin_number: str) -> bool:
    """Validate TIN number format"""
    if not tin_number:
        return True  # TIN is optional
    
    # TIN number should be 9 digits
    return len(tin_number) == 9 and tin_number.isdigit()

# Tanzania regions (for validation)
TANZANIA_REGIONS = [
    "Arusha", "Dar es Salaam", "Dodoma", "Geita", "Iringa", "Kagera",
    "Katavi", "Kigoma", "Kilimanjaro", "Lindi", "Manyara", "Mara",
    "Mbeya", "Morogoro", "Mtwara", "Mwanza", "Njombe", "Pemba North",
    "Pemba South", "Pwani", "Rukwa", "Ruvuma", "Shinyanga", "Simiyu",
    "Singida", "Songwe", "Tabora", "Tanga", "Unguja North", "Unguja South"
]

def validate_region(region: str) -> bool:
    """Validate Tanzania region"""
    return region in TANZANIA_REGIONS 