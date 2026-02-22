"""
Unit tests for validation and business rules.

Tests focus on input validation, business rules, and edge cases.
"""

import unittest
from datetime import datetime
from pydantic import ValidationError
from models.schemas import (
    QuoteSubmission, 
    NormalizedAddress, 
    HazardScores, 
    PremiumBreakdown,
    DecisionType,
    HumanReviewRecord
)


class TestQuoteSubmissionValidation(unittest.TestCase):
    """Test QuoteSubmission validation and business rules."""
    
    def test_valid_quote_submission(self):
        """Test a valid quote submission passes validation."""
        valid_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St, Los Angeles, CA 90210",
            property_type="single_family",
            coverage_amount=250000.0,
            construction_year=1995,
            square_footage=2000.0,
            roof_type="asphalt",
            foundation_type="concrete",
            additional_info="No claims in 5 years"
        )
        
        self.assertEqual(valid_submission.applicant_name, "John Doe")
        self.assertEqual(valid_submission.coverage_amount, 250000.0)
        self.assertEqual(valid_submission.property_type, "single_family")
    
    def test_invalid_coverage_amount(self):
        """Test validation rejects invalid coverage amounts."""
        # Negative coverage amount
        with self.assertRaises(ValidationError):
            QuoteSubmission(
                applicant_name="John Doe",
                address="123 Main St",
                property_type="single_family",
                coverage_amount=-1000.0
            )
        
        # Zero coverage amount
        with self.assertRaises(ValidationError):
            QuoteSubmission(
                applicant_name="John Doe",
                address="123 Main St",
                property_type="single_family",
                coverage_amount=0.0
            )
    
    def test_required_fields_validation(self):
        """Test required fields are validated."""
        # Missing applicant name
        with self.assertRaises(ValidationError):
            QuoteSubmission(
                address="123 Main St",
                property_type="single_family",
                coverage_amount=100000.0
            )
        
        # Missing address
        with self.assertRaises(ValidationError):
            QuoteSubmission(
                applicant_name="John Doe",
                property_type="single_family",
                coverage_amount=100000.0
            )
        
        # Missing property type
        with self.assertRaises(ValidationError):
            QuoteSubmission(
                applicant_name="John Doe",
                address="123 Main St",
                coverage_amount=100000.0
            )
    
    def test_property_type_validation(self):
        """Test property type validation."""
        valid_types = ["single_family", "condo", "townhouse", "commercial"]
        
        for prop_type in valid_types:
            submission = QuoteSubmission(
                applicant_name="John Doe",
                address="123 Main St",
                property_type=prop_type,
                coverage_amount=100000.0
            )
            self.assertEqual(submission.property_type, prop_type)
    
    def test_optional_fields_handling(self):
        """Test optional fields are handled correctly."""
        submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=100000.0
            # No optional fields provided
        )
        
        self.assertIsNone(submission.construction_year)
        self.assertIsNone(submission.square_footage)
        self.assertIsNone(submission.roof_type)
        self.assertIsNone(submission.foundation_type)
        self.assertIsNone(submission.additional_info)


class TestHazardScoresValidation(unittest.TestCase):
    """Test HazardScores validation and business rules."""
    
    def test_valid_hazard_scores(self):
        """Test valid hazard scores pass validation."""
        valid_scores = HazardScores(
            wildfire_risk=0.5,
            flood_risk=0.3,
            wind_risk=0.2,
            earthquake_risk=0.4
        )
        
        self.assertEqual(valid_scores.wildfire_risk, 0.5)
        self.assertEqual(valid_scores.flood_risk, 0.3)
    
    def test_hazard_score_bounds(self):
        """Test hazard scores are bounded between 0 and 1."""
        # Valid boundary values
        valid_boundary = HazardScores(
            wildfire_risk=0.0,
            flood_risk=1.0,
            wind_risk=0.5,
            earthquake_risk=0.999
        )
        self.assertEqual(valid_boundary.wildfire_risk, 0.0)
        self.assertEqual(valid_boundary.flood_risk, 1.0)
        
        # Invalid values below 0
        with self.assertRaises(ValidationError):
            HazardScores(
                wildfire_risk=-0.1,
                flood_risk=0.3,
                wind_risk=0.2,
                earthquake_risk=0.4
            )
        
        # Invalid values above 1
        with self.assertRaises(ValidationError):
            HazardScores(
                wildfire_risk=0.5,
                flood_risk=1.1,
                wind_risk=0.2,
                earthquake_risk=0.4
            )
    
    def test_required_hazard_fields(self):
        """Test all hazard fields are required."""
        # Missing wildfire risk
        with self.assertRaises(ValidationError):
            HazardScores(
                flood_risk=0.3,
                wind_risk=0.2,
                earthquake_risk=0.4
            )
        
        # Missing flood risk
        with self.assertRaises(ValidationError):
            HazardScores(
                wildfire_risk=0.5,
                wind_risk=0.2,
                earthquake_risk=0.4
            )


class TestNormalizedAddressValidation(unittest.TestCase):
    """Test NormalizedAddress validation and business rules."""
    
    def test_valid_normalized_address(self):
        """Test a valid normalized address."""
        valid_address = NormalizedAddress(
            street_address="123 Main St",
            city="Los Angeles",
            state="CA",
            zip_code="90210",
            latitude=34.0522,
            longitude=-118.2437,
            county="Los Angeles County"
        )
        
        self.assertEqual(valid_address.street_address, "123 Main St")
        self.assertEqual(valid_address.city, "Los Angeles")
        self.assertEqual(valid_address.state, "CA")
        self.assertEqual(valid_address.zip_code, "90210")
    
    def test_required_address_fields(self):
        """Test required address fields."""
        # Missing street address
        with self.assertRaises(ValidationError):
            NormalizedAddress(
                city="Los Angeles",
                state="CA",
                zip_code="90210"
            )
        
        # Missing city
        with self.assertRaises(ValidationError):
            NormalizedAddress(
                street_address="123 Main St",
                state="CA",
                zip_code="90210"
            )
        
        # Missing state
        with self.assertRaises(ValidationError):
            NormalizedAddress(
                street_address="123 Main St",
                city="Los Angeles",
                zip_code="90210"
            )
        
        # Missing zip code
        with self.assertRaises(ValidationError):
            NormalizedAddress(
                street_address="123 Main St",
                city="Los Angeles",
                state="CA"
            )
    
    def test_optional_coordinates(self):
        """Test coordinates are optional."""
        address_without_coords = NormalizedAddress(
            street_address="123 Main St",
            city="Los Angeles",
            state="CA",
            zip_code="90210"
        )
        
        self.assertIsNone(address_without_coords.latitude)
        self.assertIsNone(address_without_coords.longitude)
        self.assertIsNone(address_without_coords.county)


class TestPremiumBreakdownValidation(unittest.TestCase):
    """Test PremiumBreakdown validation and business rules."""
    
    def test_valid_premium_breakdown(self):
        """Test a valid premium breakdown."""
        valid_breakdown = PremiumBreakdown(
            base_premium=500.0,
            hazard_surcharge=150.0,
            total_premium=650.0,
            rating_factors={
                "base_rate": 2.5,
                "property_multiplier": 1.0,
                "hazard_load": 0.3
            }
        )
        
        self.assertEqual(valid_breakdown.base_premium, 500.0)
        self.assertEqual(valid_breakdown.hazard_surcharge, 150.0)
        self.assertEqual(valid_breakdown.total_premium, 650.0)
    
    def test_premium_calculation_consistency(self):
        """Test total premium equals base plus surcharge."""
        test_cases = [
            (100.0, 50.0, 150.0),
            (250.0, 75.0, 325.0),
            (1000.0, 200.0, 1200.0)
        ]
        
        for base, surcharge, total in test_cases:
            with self.subTest(base=base, surcharge=surcharge):
                breakdown = PremiumBreakdown(
                    base_premium=base,
                    hazard_surcharge=surcharge,
                    total_premium=total,
                    rating_factors={}
                )
                
                self.assertEqual(breakdown.total_premium, base + surcharge)
    
    def test_rating_factors_structure(self):
        """Test rating factors are properly structured."""
        breakdown = PremiumBreakdown(
            base_premium=500.0,
            hazard_surcharge=150.0,
            total_premium=650.0,
            rating_factors={
                "base_rate": 2.5,
                "property_multiplier": 1.0,
                "hazard_load": 0.3,
                "construction_discount": 0.9
            }
        )
        
        # Check factors are accessible
        self.assertEqual(breakdown.rating_factors["base_rate"], 2.5)
        self.assertEqual(breakdown.rating_factors["property_multiplier"], 1.0)
        self.assertEqual(breakdown.rating_factors["hazard_load"], 0.3)
        self.assertEqual(breakdown.rating_factors["construction_discount"], 0.9)


class TestDecisionTypeValidation(unittest.TestCase):
    """Test DecisionType enum validation."""
    
    def test_valid_decision_types(self):
        """Test all valid decision types."""
        valid_decisions = [DecisionType.ACCEPT, DecisionType.REFER, DecisionType.DECLINE]
        
        for decision in valid_decisions:
            self.assertIsInstance(decision, DecisionType)
            self.assertIn(decision.value, ["ACCEPT", "REFER", "DECLINE"])
    
    def test_decision_type_values(self):
        """Test decision type enum values."""
        self.assertEqual(DecisionType.ACCEPT.value, "ACCEPT")
        self.assertEqual(DecisionType.REFER.value, "REFER")
        self.assertEqual(DecisionType.DECLINE.value, "DECLINE")


class TestHumanReviewRecordValidation(unittest.TestCase):
    """Test HumanReviewRecord validation and business rules."""
    
    def test_valid_human_review_record(self):
        """Test a valid human review record."""
        valid_record = HumanReviewRecord(
            run_id="review_123",
            status="approved",
            requires_human_review=False,
            final_decision="ACCEPT",
            reviewer="senior_reviewer",
            review_timestamp=datetime.now(),
            approved_premium=1500.0,
            reviewer_notes="All documentation verified",
            review_priority="high",
            assigned_reviewer="team_lead",
            estimated_review_time="2 hours",
            submission_timestamp=datetime.now(),
            review_deadline=datetime.now()
        )
        
        self.assertEqual(valid_record.run_id, "review_123")
        self.assertEqual(valid_record.status, "approved")
        self.assertFalse(valid_record.requires_human_review)
        self.assertEqual(valid_record.final_decision, "ACCEPT")
    
    def test_required_review_fields(self):
        """Test required human review fields."""
        # All fields should be optional except run_id
        # Test minimal valid record
        minimal_record = HumanReviewRecord(
            run_id="review_123",
            status="pending",
            requires_human_review=True
        )
        
        self.assertEqual(minimal_record.run_id, "review_123")
        self.assertEqual(minimal_record.status, "pending")
        self.assertTrue(minimal_record.requires_human_review)
        
        # Test with all optional fields as None
        record_with_nones = HumanReviewRecord(
            run_id="review_124",
            status="pending",
            requires_human_review=True,
            final_decision=None,
            reviewer=None,
            review_timestamp=None,
            approved_premium=None,
            reviewer_notes=None
        )
        
        self.assertEqual(record_with_nones.run_id, "review_124")
        self.assertIsNone(record_with_nones.final_decision)
        self.assertIsNone(record_with_nones.reviewer)
    
    def test_review_status_values(self):
        """Test valid review status values."""
        valid_statuses = ["pending", "approved", "rejected", "requires_more_info"]
        
        for status in valid_statuses:
            record = HumanReviewRecord(
                run_id="test_123",
                status=status,
                requires_human_review=True
            )
            self.assertEqual(record.status, status)
    
    def test_boolean_field_validation(self):
        """Test boolean field validation."""
        # Test True value
        record_true = HumanReviewRecord(
            run_id="test_123",
            status="pending",
            requires_human_review=True
        )
        self.assertTrue(record_true.requires_human_review)
        
        # Test False value
        record_false = HumanReviewRecord(
            run_id="test_124",
            status="approved",
            requires_human_review=False
        )
        self.assertFalse(record_false.requires_human_review)


class TestBusinessRules(unittest.TestCase):
    """Test business rules and constraints."""
    
    def test_coverage_amount_business_limits(self):
        """Test business limits on coverage amounts."""
        # Test minimum reasonable coverage
        min_submission = QuoteSubmission(
            applicant_name="Test User",
            address="123 Test St",
            property_type="single_family",
            coverage_amount=50000.0  # $50K minimum
        )
        self.assertEqual(min_submission.coverage_amount, 50000.0)
        
        # Test maximum reasonable coverage
        max_submission = QuoteSubmission(
            applicant_name="Test User",
            address="123 Test St",
            property_type="single_family",
            coverage_amount=5000000.0  # $5M maximum
        )
        self.assertEqual(max_submission.coverage_amount, 5000000.0)
    
    def test_construction_year_business_rules(self):
        """Test business rules for construction years."""
        # Test very old property
        old_property = QuoteSubmission(
            applicant_name="Test User",
            address="123 Test St",
            property_type="single_family",
            coverage_amount=100000.0,
            construction_year=1800  # Very old
        )
        self.assertEqual(old_property.construction_year, 1800)
        
        # Test future year (should still validate but may trigger business rules)
        future_property = QuoteSubmission(
            applicant_name="Test User",
            address="123 Test St",
            property_type="single_family",
            coverage_amount=100000.0,
            construction_year=2030  # Future year
        )
        self.assertEqual(future_property.construction_year, 2030)
    
    def test_square_footage_business_rules(self):
        """Test business rules for square footage."""
        # Test very small property
        small_property = QuoteSubmission(
            applicant_name="Test User",
            address="123 Test St",
            property_type="single_family",
            coverage_amount=100000.0,
            square_footage=100.0  # Very small
        )
        self.assertEqual(small_property.square_footage, 100.0)
        
        # Test very large property
        large_property = QuoteSubmission(
            applicant_name="Test User",
            address="123 Test St",
            property_type="single_family",
            coverage_amount=100000.0,
            square_footage=20000.0  # Very large
        )
        self.assertEqual(large_property.square_footage, 20000.0)


if __name__ == '__main__':
    unittest.main()
