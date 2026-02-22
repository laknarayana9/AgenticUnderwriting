"""
Test configuration and fixtures for unit tests.

This module provides common test data and configuration.
"""

import pytest
from datetime import datetime, timedelta
from models.schemas import (
    QuoteSubmission,
    NormalizedAddress,
    HazardScores,
    PremiumBreakdown,
    WorkflowState,
    RunRecord,
    HumanReviewRecord,
    DecisionType
)


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_quote_submission(**overrides):
        """Create a valid QuoteSubmission with optional overrides."""
        defaults = {
            "applicant_name": "John Doe",
            "address": "123 Main St, Los Angeles, CA 90210",
            "property_type": "single_family",
            "coverage_amount": 250000.0,
            "construction_year": 1995,
            "square_footage": 2000.0,
            "roof_type": "asphalt",
            "foundation_type": "concrete",
            "additional_info": "No claims in 5 years"
        }
        defaults.update(overrides)
        return QuoteSubmission(**defaults)
    
    @staticmethod
    def create_normalized_address(**overrides):
        """Create a valid NormalizedAddress with optional overrides."""
        defaults = {
            "street_address": "123 Main St",
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90210",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "county": "Los Angeles County"
        }
        defaults.update(overrides)
        return NormalizedAddress(**defaults)
    
    @staticmethod
    def create_hazard_scores(**overrides):
        """Create valid HazardScores with optional overrides."""
        defaults = {
            "wildfire_risk": 0.3,
            "flood_risk": 0.2,
            "wind_risk": 0.1,
            "earthquake_risk": 0.4
        }
        defaults.update(overrides)
        return HazardScores(**defaults)
    
    @staticmethod
    def create_premium_breakdown(**overrides):
        """Create a valid PremiumBreakdown with optional overrides."""
        defaults = {
            "base_premium": 500.0,
            "hazard_surcharge": 150.0,
            "total_premium": 650.0,
            "rating_factors": {
                "base_rate": 2.5,
                "property_multiplier": 1.0,
                "hazard_load": 0.3
            }
        }
        defaults.update(overrides)
        return PremiumBreakdown(**defaults)
    
    @staticmethod
    def create_workflow_state(**overrides):
        """Create a valid WorkflowState with optional overrides."""
        defaults = {
            "current_node": "risk_assessment",
            "completed_nodes": [],
            "pending_nodes": ["risk_assessment", "rating", "decision"],
            "error_count": 0
        }
        defaults.update(overrides)
        return WorkflowState(**defaults)
    
    @staticmethod
    def create_run_record(**overrides):
        """Create a valid RunRecord with optional overrides."""
        defaults = {
            "run_id": "test_run_123",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "status": "in_progress",
            "workflow_state": TestDataFactory.create_workflow_state(),
            "node_outputs": {},
            "error_message": None
        }
        defaults.update(overrides)
        return RunRecord(**defaults)
    
    @staticmethod
    def create_human_review_record(**overrides):
        """Create a valid HumanReviewRecord with optional overrides."""
        defaults = {
            "run_id": "review_123",
            "status": "pending",
            "requires_human_review": True,
            "final_decision": None,
            "reviewer": None,
            "review_timestamp": None,
            "approved_premium": None,
            "reviewer_notes": None,
            "review_priority": "medium",
            "assigned_reviewer": "senior_reviewer",
            "estimated_review_time": "24 hours",
            "submission_timestamp": datetime.now(),
            "review_deadline": datetime.now() + timedelta(hours=24)
        }
        defaults.update(overrides)
        return HumanReviewRecord(**defaults)


class TestScenarios:
    """Predefined test scenarios for common use cases."""
    
    @staticmethod
    def low_risk_scenario():
        """Low risk property scenario."""
        return {
            "address": TestDataFactory.create_normalized_address(
                county="Sacramento County"  # Lower risk area
            ),
            "hazard_scores": TestDataFactory.create_hazard_scores(
                wildfire_risk=0.2,
                flood_risk=0.1,
                wind_risk=0.1,
                earthquake_risk=0.2
            ),
            "submission": TestDataFactory.create_quote_submission(
                property_type="condo",
                construction_year=2018,
                coverage_amount=200000.0
            ),
            "expected_decision": "ACCEPT",
            "expected_premium_range": (300.0, 500.0)
        }
    
    @staticmethod
    def medium_risk_scenario():
        """Medium risk property scenario."""
        return {
            "address": TestDataFactory.create_normalized_address(
                county="Fresno County"  # Medium risk area
            ),
            "hazard_scores": TestDataFactory.create_hazard_scores(
                wildfire_risk=0.6,
                flood_risk=0.3,
                wind_risk=0.3,
                earthquake_risk=0.4
            ),
            "submission": TestDataFactory.create_quote_submission(
                property_type="single_family",
                construction_year=1985,
                coverage_amount=350000.0
            ),
            "expected_decision": "REFER",
            "expected_premium_range": (800.0, 1200.0)
        }
    
    @staticmethod
    def high_risk_scenario():
        """High risk property scenario."""
        return {
            "address": TestDataFactory.create_normalized_address(
                county="Los Angeles County"  # High risk area
            ),
            "hazard_scores": TestDataFactory.create_hazard_scores(
                wildfire_risk=0.8,
                flood_risk=0.4,
                wind_risk=0.3,
                earthquake_risk=0.9
            ),
            "submission": TestDataFactory.create_quote_submission(
                property_type="commercial",
                construction_year=1950,
                coverage_amount=500000.0
            ),
            "expected_decision": "DECLINE",
            "expected_premium_range": (2000.0, 5000.0)
        }
    
    @staticmethod
    def edge_case_scenarios():
        """Edge case scenarios for testing."""
        return [
            {
                "name": "minimum_coverage",
                "submission": TestDataFactory.create_quote_submission(
                    coverage_amount=50000.0
                ),
                "expected_behavior": "should_process_successfully"
            },
            {
                "name": "maximum_coverage",
                "submission": TestDataFactory.create_quote_submission(
                    coverage_amount=5000000.0
                ),
                "expected_behavior": "should_process_successfully"
            },
            {
                "name": "very_old_property",
                "submission": TestDataFactory.create_quote_submission(
                    construction_year=1800
                ),
                "expected_behavior": "should_flag_for_review"
            },
            {
                "name": "future_construction",
                "submission": TestDataFactory.create_quote_submission(
                    construction_year=2030
                ),
                "expected_behavior": "should_flag_for_review"
            },
            {
                "name": "minimal_square_footage",
                "submission": TestDataFactory.create_quote_submission(
                    square_footage=100.0
                ),
                "expected_behavior": "should_process_successfully"
            },
            {
                "name": "large_square_footage",
                "submission": TestDataFactory.create_quote_submission(
                    square_footage=20000.0
                ),
                "expected_behavior": "should_process_successfully"
            }
        ]


class TestConstants:
    """Constants used in testing."""
    
    # Business rule thresholds
    MAX_HAZARD_RISK_ACCEPT = 0.4
    MAX_HAZARD_RISK_REFER = 0.7
    MAX_PREMIUM_TO_COVERAGE_RATIO = 0.01
    MAX_PREMIUM_TO_COVERAGE_REFER = 0.02
    
    # Property age limits
    MIN_PROPERTY_AGE = 5
    MAX_PROPERTY_AGE = 50
    MAX_PROPERTY_AGE_DECLINE = 100
    
    # Coverage limits
    MIN_COVERAGE_AMOUNT = 50000.0
    MAX_COVERAGE_AMOUNT = 5000000.0
    
    # Premium tiers
    PREMIUM_TIER_LOW = 2000.0
    PREMIUM_TIER_HIGH = 5000.0
    
    # Review deadlines (hours)
    REVIEW_DEADLINE_HIGH = 24
    REVIEW_DEADLINE_MEDIUM = 48
    REVIEW_DEADLINE_LOW = 72
    
    # Error thresholds
    MAX_WORKFLOW_ERRORS = 3


@pytest.fixture
def sample_quote_submission():
    """Fixture providing a sample quote submission."""
    return TestDataFactory.create_quote_submission()


@pytest.fixture
def sample_normalized_address():
    """Fixture providing a sample normalized address."""
    return TestDataFactory.create_normalized_address()


@pytest.fixture
def sample_hazard_scores():
    """Fixture providing sample hazard scores."""
    return TestDataFactory.create_hazard_scores()


@pytest.fixture
def sample_premium_breakdown():
    """Fixture providing a sample premium breakdown."""
    return TestDataFactory.create_premium_breakdown()


@pytest.fixture
def sample_workflow_state():
    """Fixture providing a sample workflow state."""
    return TestDataFactory.create_workflow_state()


@pytest.fixture
def sample_run_record():
    """Fixture providing a sample run record."""
    return TestDataFactory.create_run_record()


@pytest.fixture
def sample_human_review_record():
    """Fixture providing a sample human review record."""
    return TestDataFactory.create_human_review_record()


@pytest.fixture
def low_risk_scenario():
    """Fixture providing low risk test scenario."""
    return TestScenarios.low_risk_scenario()


@pytest.fixture
def medium_risk_scenario():
    """Fixture providing medium risk test scenario."""
    return TestScenarios.medium_risk_scenario()


@pytest.fixture
def high_risk_scenario():
    """Fixture providing high risk test scenario."""
    return TestScenarios.high_risk_scenario()
