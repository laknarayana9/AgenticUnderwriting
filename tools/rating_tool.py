import math
from typing import Dict, Any
from models.schemas import HazardScores, PremiumBreakdown


class RatingTool:
    """
    Stub implementation for insurance rating.
    In production, this would use actuarial tables, 
    historical loss data, and sophisticated rating algorithms.
    """
    
    def __init__(self):
        # Base rates per $1000 coverage
        self.base_rate_per_1000 = 2.5  # $2.50 per $1000 coverage
        
        # Hazard multipliers
        self.hazard_multipliers = {
            "wildfire": 1.5,
            "flood": 1.8,
            "wind": 1.3,
            "earthquake": 2.0
        }
        
        # Property type multipliers
        self.property_multipliers = {
            "single_family": 1.0,
            "condo": 0.8,
            "townhouse": 0.9,
            "commercial": 1.5
        }
    
    def calculate_premium(
        self, 
        coverage_amount: float,
        property_type: str,
        hazard_scores: HazardScores,
        construction_year: int = None
    ) -> PremiumBreakdown:
        """
        Calculate insurance premium based on risk factors.
        """
        # Calculate base premium
        base_premium = (coverage_amount / 1000) * self.base_rate_per_1000
        
        # Apply property type multiplier
        prop_multiplier = self.property_multipliers.get(property_type, 1.0)
        base_premium *= prop_multiplier
        
        # Apply construction year discount/surcharge
        if construction_year:
            age = 2024 - construction_year
            if age < 10:  # New construction
                base_premium *= 0.9  # 10% discount
            elif age > 50:  # Old construction
                base_premium *= 1.2  # 20% surcharge
        
        # Calculate hazard surcharge
        hazard_surcharge = 0
        hazard_surcharge += hazard_scores.wildfire_risk * base_premium * 0.3
        hazard_surcharge += hazard_scores.flood_risk * base_premium * 0.4
        hazard_surcharge += hazard_scores.wind_risk * base_premium * 0.2
        hazard_surcharge += hazard_scores.earthquake_risk * base_premium * 0.5
        
        # Total premium
        total_premium = base_premium + hazard_surcharge
        
        # Rating factors for transparency
        rating_factors = {
            "base_rate": self.base_rate_per_1000,
            "property_multiplier": prop_multiplier,
            "hazard_load": hazard_surcharge / base_premium if base_premium > 0 else 0
        }
        
        if construction_year:
            age = 2024 - construction_year
            if age < 10:
                rating_factors["construction_discount"] = 0.9
            elif age > 50:
                rating_factors["construction_surcharge"] = 1.2
        
        return PremiumBreakdown(
            base_premium=round(base_premium, 2),
            hazard_surcharge=round(hazard_surcharge, 2),
            total_premium=round(total_premium, 2),
            rating_factors=rating_factors
        )
    
    def __call__(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool interface that returns structured output.
        """
        coverage_amount = risk_data.get("coverage_amount", 0)
        property_type = risk_data.get("property_type", "single_family")
        hazard_scores = HazardScores(**risk_data.get("hazard_scores", {}))
        construction_year = risk_data.get("construction_year")
        
        premium = self.calculate_premium(
            coverage_amount=coverage_amount,
            property_type=property_type,
            hazard_scores=hazard_scores,
            construction_year=construction_year
        )
        
        # Determine if premium is within acceptable range
        if premium.total_premium > 5000:
            premium_tier = "HIGH"
        elif premium.total_premium > 2000:
            premium_tier = "MEDIUM"
        else:
            premium_tier = "LOW"
        
        return {
            "premium_breakdown": premium.dict(),
            "premium_tier": premium_tier,
            "annual_premium": premium.total_premium,
            "monthly_premium": round(premium.total_premium / 12, 2),
            "rating_model": "basic_v1"
        }
