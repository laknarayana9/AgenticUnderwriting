import random
from typing import Dict, Any
from models.schemas import NormalizedAddress, HazardScores


class HazardScoreTool:
    """
    Stub implementation for hazard scoring.
    In production, this would integrate with FEMA flood maps, 
    wildfire risk services, wind zone data, etc.
    """
    
    def __init__(self):
        # Mock hazard data by county
        self.county_hazard_data = {
            "Los Angeles County": {
                "wildfire": 0.7,
                "flood": 0.3,
                "wind": 0.2,
                "earthquake": 0.8
            },
            "San Francisco County": {
                "wildfire": 0.1,
                "flood": 0.4,
                "wind": 0.3,
                "earthquake": 0.9
            },
            "San Diego County": {
                "wildfire": 0.8,
                "flood": 0.2,
                "wind": 0.4,
                "earthquake": 0.6
            },
            "Sacramento County": {
                "wildfire": 0.4,
                "flood": 0.5,
                "wind": 0.2,
                "earthquake": 0.5
            },
            "Fresno County": {
                "wildfire": 0.6,
                "flood": 0.3,
                "wind": 0.3,
                "earthquake": 0.4
            }
        }
    
    def calculate_hazard_scores(self, address: NormalizedAddress) -> HazardScores:
        """
        Calculate hazard scores based on address.
        """
        county = address.county
        
        # Get base scores for county, or use defaults
        base_scores = self.county_hazard_data.get(county, {
            "wildfire": 0.3,
            "flood": 0.3,
            "wind": 0.3,
            "earthquake": 0.3
        })
        
        # Add some randomness to simulate more sophisticated scoring
        # In production, this would be based on actual risk models
        wildfire_risk = max(0, min(1, base_scores["wildfire"] + random.uniform(-0.1, 0.1)))
        flood_risk = max(0, min(1, base_scores["flood"] + random.uniform(-0.1, 0.1)))
        wind_risk = max(0, min(1, base_scores["wind"] + random.uniform(-0.1, 0.1)))
        earthquake_risk = max(0, min(1, base_scores["earthquake"] + random.uniform(-0.1, 0.1)))
        
        return HazardScores(
            wildfire_risk=wildfire_risk,
            flood_risk=flood_risk,
            wind_risk=wind_risk,
            earthquake_risk=earthquake_risk
        )
    
    def __call__(self, address: NormalizedAddress) -> Dict[str, Any]:
        """
        Tool interface that returns structured output.
        """
        scores = self.calculate_hazard_scores(address)
        
        # Determine risk level
        max_risk = max(scores.wildfire_risk, scores.flood_risk, scores.wind_risk, scores.earthquake_risk)
        if max_risk >= 0.7:
            risk_level = "HIGH"
        elif max_risk >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "hazard_scores": scores.dict(),
            "overall_risk_level": risk_level,
            "primary_hazard": max([
                ("wildfire", scores.wildfire_risk),
                ("flood", scores.flood_risk),
                ("wind", scores.wind_risk),
                ("earthquake", scores.earthquake_risk)
            ], key=lambda x: x[1])[0],
            "data_source": "mock_data_v1"
        }
