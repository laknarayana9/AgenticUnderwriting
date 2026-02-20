import re
from typing import Dict, Any
from models.schemas import QuoteSubmission, NormalizedAddress


class AddressNormalizeTool:
    """
    Stub implementation for address normalization.
    In production, this would integrate with services like Google Maps API,
    SmartyStreets, or other address validation services.
    """
    
    def __init__(self):
        # Mock data for common cities/counties
        self.city_county_map = {
            "Los Angeles": "Los Angeles County",
            "San Francisco": "San Francisco County",
            "San Diego": "San Diego County",
            "Sacramento": "Sacramento County",
            "Fresno": "Fresno County"
        }
    
    def normalize(self, submission: QuoteSubmission) -> NormalizedAddress:
        """
        Normalize the address from quote submission.
        """
        address = submission.address
        
        # Basic parsing logic (very simplified)
        parts = address.split(',')
        
        if len(parts) >= 3:
            street = parts[0].strip()
            city = parts[1].strip()
            state_zip = parts[2].strip()
        elif len(parts) == 2:
            street = parts[0].strip()
            city_state_zip = parts[1].strip()
            # Try to extract city
            city_match = re.search(r'([A-Za-z\s]+),?', city_state_zip)
            city = city_match.group(1).strip() if city_match else ""
            state_zip = city_state_zip
        else:
            # Single line address
            street = address
            city = ""
            state_zip = ""
        
        # Extract state and zip
        state = ""
        zip_code = ""
        if state_zip:
            zip_match = re.search(r'(\d{5}(?:-\d{4})?)', state_zip)
            if zip_match:
                zip_code = zip_match.group(1)
                state = state_zip.replace(zip_code, '').strip().strip(',').strip()
            else:
                state = state_zip
        
        # Mock coordinates (in production, use geocoding API)
        latitude = 34.0522 if "Los Angeles" in city else 37.7749 if "San Francisco" in city else None
        longitude = -118.2437 if "Los Angeles" in city else -122.4194 if "San Francisco" in city else None
        
        # Get county
        county = self.city_county_map.get(city, "Unknown County")
        
        return NormalizedAddress(
            street_address=street,
            city=city,
            state=state,
            zip_code=zip_code,
            latitude=latitude,
            longitude=longitude,
            county=county
        )
    
    def __call__(self, submission: QuoteSubmission) -> Dict[str, Any]:
        """
        Tool interface that returns structured output.
        """
        normalized = self.normalize(submission)
        return {
            "normalized_address": normalized.dict(),
            "confidence": 0.85,  # Mock confidence score
            "warnings": [] if normalized.city else ["City could not be determined"]
        }
