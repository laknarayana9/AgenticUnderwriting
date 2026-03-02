"""
Mock Verisk Home Location API
Provides property location data and risk assessment for testing
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import random
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verisk", tags=["verisk"])

# Mock property data with different risk profiles
MOCK_PROPERTIES = [
    {
        "address": "1234 Main St, Fremont, CA 94536",
        "property_type": "single_family",
        "year_built": 1972,
        "square_footage": 1800,
        "risk_profile": {
            "wildfire_risk": "moderate",
            "flood_risk": "low",
            "fire_protection": "distance > 5 miles",
            "overall_risk": "MODERATE"
        }
    },
    {
        "address": "2231 Watermarke Pl, Irvine, CA 92612",
        "property_type": "single_family", 
        "year_built": 2018,
        "square_footage": 2200,
        "risk_profile": {
            "wildfire_risk": "low",
            "flood_risk": "low",
            "fire_protection": "hydrants within 5 miles",
            "overall_risk": "LOW"
        }
    },
    {
        "address": "5678 Oak Ave, Newport Beach, CA 92663",
        "property_type": "condo",
        "year_built": 2015,
        "square_footage": 1500,
        "risk_profile": {
            "wildfire_risk": "high",
            "flood_risk": "moderate", 
            "fire_protection": "ocean proximity",
            "overall_risk": "HIGH"
        }
    },
    {
        "address": "9012 Pacific Coast Hwy, Laguna Beach, CA 92651",
        "property_type": "single_family",
        "year_built": 2020,
        "square_footage": 2800,
        "risk_profile": {
            "wildfire_risk": "moderate",
            "flood_risk": "high",
            "fire_protection": "coastal elevation",
            "overall_risk": "HIGH"
        }
    },
    {
        "address": "4321 Wilshire Blvd, Los Angeles, CA 90048",
        "property_type": "multi_family",
        "year_built": 1965,
        "square_footage": 3200,
        "risk_profile": {
            "wildfire_risk": "high",
            "flood_risk": "moderate",
            "fire_protection": "urban fire department",
            "overall_risk": "HIGH"
        }
    }
]

@router.get("/random-location")
async def get_random_location():
    """Get a random property location for testing"""
    location = random.choice(MOCK_PROPERTIES)
    logger.info(f"Returning random location: {location['address']}")
    return {
        "address": location["address"],
        "property_type": location["property_type"],
        "year_built": location["year_built"],
        "square_footage": location["square_footage"],
        "risk_profile": location["risk_profile"],
        "location_id": f"LOC_{hash(location['address']) % 10000:04d}"
    }

@router.get("/location/{address}")
async def get_location_by_address(address: str):
    """Get property location data by address"""
    logger.info(f"Looking up location for address: {address}")
    
    # Find matching property (case-insensitive partial match)
    for prop in MOCK_PROPERTIES:
        if address.lower() in prop["address"].lower():
            logger.info(f"Found location: {prop['address']}")
            return {
                "address": prop["address"],
                "property_type": prop["property_type"],
                "year_built": prop["year_built"],
                "square_footage": prop["square_footage"],
                "risk_profile": prop["risk_profile"],
                "location_id": f"LOC_{hash(prop['address']) % 10000:04d}"
            }
    
    # If not found, return 404
    logger.warning(f"Location not found for address: {address}")
    raise HTTPException(status_code=404, detail=f"Location not found for address: {address}")

@router.get("/locations")
async def get_all_locations():
    """Get all available property locations"""
    logger.info("Returning all mock locations")
    return {
        "locations": MOCK_PROPERTIES,
        "total_count": len(MOCK_PROPERTIES),
        "risk_summary": {
            "LOW": len([p for p in MOCK_PROPERTIES if p["risk_profile"]["overall_risk"] == "LOW"]),
            "MODERATE": len([p for p in MOCK_PROPERTIES if p["risk_profile"]["overall_risk"] == "MODERATE"]),
            "HIGH": len([p for p in MOCK_PROPERTIES if p["risk_profile"]["overall_risk"] == "HIGH"])
        }
    }

@router.post("/bulk-lookup")
async def bulk_location_lookup(request: Dict[str, Any]):
    """Bulk lookup of multiple addresses"""
    addresses = request.get("addresses", [])
    results = []
    
    logger.info(f"Bulk lookup for {len(addresses)} addresses")
    
    for address in addresses:
        try:
            location_data = await get_location_by_address(address)
            results.append(location_data)
        except HTTPException as e:
            if e.status_code == 404:
                results.append({
                    "address": address,
                    "found": False,
                    "error": "Location not found"
                })
            else:
                results.append({
                    "address": address,
                    "found": False,
                    "error": str(e)
                })
    
    return {
        "results": results,
        "total_requested": len(addresses),
        "successful_lookups": len([r for r in results if r.get("found", False)])
    }
