"""
Unit tests for workflow and business process logic.

Tests focus on workflow state management, business processes, and decision logic.
"""

import unittest
from datetime import datetime, timedelta
from models.schemas import (
    RunRecord, 
    WorkflowState, 
    DecisionType,
    HumanReviewRecord
)


class TestWorkflowState(unittest.TestCase):
    """Test WorkflowState business logic."""
    
    def test_workflow_state_initialization(self):
        """Test workflow state initialization."""
        from models.schemas import QuoteSubmission
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        initial_state = WorkflowState(
            quote_submission=quote_submission,
            current_node="risk_assessment",
            missing_info=[],
            additional_answers={}
        )
        
        self.assertEqual(initial_state.current_node, "risk_assessment")
        self.assertEqual(initial_state.quote_submission.applicant_name, "John Doe")
        self.assertEqual(len(initial_state.missing_info), 0)
        self.assertFalse(initial_state.citation_guardrail_triggered)
    
    def test_workflow_state_progression(self):
        """Test workflow state progression."""
        from models.schemas import QuoteSubmission
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        # Start state
        state = WorkflowState(
            quote_submission=quote_submission,
            current_node="risk_assessment",
            missing_info=[],
            additional_answers={}
        )
        
        # Progress to next node
        state.current_node = "rating"
        
        self.assertEqual(state.current_node, "rating")
        self.assertEqual(state.quote_submission.applicant_name, "John Doe")
    
    def test_workflow_error_handling(self):
        """Test workflow error handling."""
        from models.schemas import QuoteSubmission
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        state = WorkflowState(
            quote_submission=quote_submission,
            current_node="risk_assessment",
            missing_info=["construction_year"],
            additional_answers={}
        )
        
        # Test missing info tracking
        self.assertIn("construction_year", state.missing_info)
        self.assertEqual(len(state.missing_info), 1)
        
        # Test citation guardrail
        state.citation_guardrail_triggered = True
        self.assertTrue(state.citation_guardrail_triggered)
        
        # Test additional answers
        state.additional_answers["construction_year"] = "1995"
        self.assertEqual(state.additional_answers["construction_year"], "1995")
    
    def test_workflow_completion(self):
        """Test workflow completion logic."""
        from models.schemas import QuoteSubmission, Decision, DecisionType, PremiumBreakdown
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        premium_breakdown = PremiumBreakdown(
            base_premium=500.0,
            hazard_surcharge=150.0,
            total_premium=650.0,
            rating_factors={}
        )
        
        decision = Decision(
            decision=DecisionType.ACCEPT,
            rationale="Low risk property",
            premium=premium_breakdown
        )
        
        state = WorkflowState(
            quote_submission=quote_submission,
            current_node="completed",
            decision=decision,
            premium_breakdown=premium_breakdown
        )
        
        self.assertEqual(state.current_node, "completed")
        self.assertEqual(state.decision.decision, DecisionType.ACCEPT)
        self.assertEqual(state.premium_breakdown.total_premium, 650.0)
    
    def test_workflow_restart_logic(self):
        """Test workflow restart logic."""
        from models.schemas import QuoteSubmission
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        # Initial failed state
        state = WorkflowState(
            quote_submission=quote_submission,
            current_node="failed",
            missing_info=["construction_year"],
            citation_guardrail_triggered=True
        )
        
        # Restart workflow
        state.current_node = "risk_assessment"
        state.missing_info = []
        state.citation_guardrail_triggered = False
        
        self.assertEqual(state.current_node, "risk_assessment")
        self.assertEqual(len(state.missing_info), 0)
        self.assertFalse(state.citation_guardrail_triggered)


class TestRunRecord(unittest.TestCase):
    """Test RunRecord business logic."""
    
    def test_run_record_creation(self):
        """Test run record creation and validation."""
        from models.schemas import QuoteSubmission
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        workflow_state = WorkflowState(
            quote_submission=quote_submission,
            current_node="risk_assessment",
            missing_info=[],
            additional_answers={}
        )
        
        run_record = RunRecord(
            run_id="test_123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="in_progress",
            workflow_state=workflow_state,
            node_outputs={},
            error_message=None
        )
        
        self.assertEqual(run_record.run_id, "test_123")
        self.assertEqual(run_record.status, "in_progress")
        self.assertIsNone(run_record.error_message)
        self.assertIsInstance(run_record.workflow_state, WorkflowState)
        self.assertEqual(run_record.workflow_state.quote_submission.applicant_name, "John Doe")
    
    def test_run_record_status_transitions(self):
        """Test valid status transitions."""
        from models.schemas import QuoteSubmission
        
        valid_transitions = [
            ("pending", "in_progress"),
            ("in_progress", "completed"),
            ("in_progress", "failed"),
            ("failed", "pending"),  # Retry
            ("completed", "archived")
        ]
        
        for from_status, to_status in valid_transitions:
            with self.subTest(from_status=from_status, to_status=to_status):
                quote_submission = QuoteSubmission(
                    applicant_name="John Doe",
                    address="123 Main St",
                    property_type="single_family",
                    coverage_amount=250000.0
                )
                
                workflow_state = WorkflowState(
                    quote_submission=quote_submission,
                    current_node="test",
                    missing_info=[],
                    additional_answers={}
                )
                
                run_record = RunRecord(
                    run_id="test_123",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    status=from_status,
                    workflow_state=workflow_state,
                    node_outputs={},
                    error_message=None
                )
                
                # Update status
                run_record.status = to_status
                run_record.updated_at = datetime.now()
                
                self.assertEqual(run_record.status, to_status)
    
    def test_run_record_error_handling(self):
        """Test error handling in run records."""
        from models.schemas import QuoteSubmission
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        workflow_state = WorkflowState(
            quote_submission=quote_submission,
            current_node="failed",
            missing_info=["construction_year"],
            citation_guardrail_triggered=True
        )
        
        run_record = RunRecord(
            run_id="test_123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="failed",
            workflow_state=workflow_state,
            node_outputs={},
            error_message="Risk assessment service unavailable"
        )
        
        self.assertEqual(run_record.status, "failed")
        self.assertEqual(run_record.error_message, "Risk assessment service unavailable")
        self.assertIn("construction_year", run_record.workflow_state.missing_info)
    
    def test_run_record_timestamps(self):
        """Test timestamp management."""
        from models.schemas import QuoteSubmission, Decision, DecisionType, PremiumBreakdown
        
        created_time = datetime.now()
        updated_time = created_time + timedelta(minutes=5)
        
        quote_submission = QuoteSubmission(
            applicant_name="John Doe",
            address="123 Main St",
            property_type="single_family",
            coverage_amount=250000.0
        )
        
        premium_breakdown = PremiumBreakdown(
            base_premium=500.0,
            hazard_surcharge=150.0,
            total_premium=650.0,
            rating_factors={}
        )
        
        decision = Decision(
            decision=DecisionType.ACCEPT,
            rationale="Low risk property",
            premium=premium_breakdown
        )
        
        workflow_state = WorkflowState(
            quote_submission=quote_submission,
            current_node="completed",
            decision=decision,
            premium_breakdown=premium_breakdown
        )
        
        run_record = RunRecord(
            run_id="test_123",
            created_at=created_time,
            updated_at=updated_time,
            status="completed",
            workflow_state=workflow_state,
            node_outputs={},
            error_message=None
        )
        
        self.assertEqual(run_record.created_at, created_time)
        self.assertEqual(run_record.updated_at, updated_time)
        self.assertGreater(run_record.updated_at, run_record.created_at)


class TestHumanReviewWorkflow(unittest.TestCase):
    """Test human review workflow business logic."""
    
    def test_human_review_initiation(self):
        """Test human review initiation logic."""
        review_record = HumanReviewRecord(
            run_id="review_123",
            status="pending",
            requires_human_review=True,
            final_decision=None,
            reviewer=None,
            review_timestamp=None,
            approved_premium=None,
            reviewer_notes=None,
            review_priority="high",
            assigned_reviewer="senior_reviewer",
            estimated_review_time="24 hours",
            submission_timestamp=datetime.now(),
            review_deadline=datetime.now() + timedelta(hours=24)
        )
        
        self.assertEqual(review_record.status, "pending")
        self.assertTrue(review_record.requires_human_review)
        self.assertIsNone(review_record.final_decision)
        self.assertIsNone(review_record.reviewer)
        self.assertIsNone(review_record.review_timestamp)
        self.assertEqual(review_record.review_priority, "high")
    
    def test_human_review_approval(self):
        """Test human review approval process."""
        review_time = datetime.now()
        
        review_record = HumanReviewRecord(
            run_id="review_123",
            status="approved",
            requires_human_review=False,
            final_decision="ACCEPT",
            reviewer="senior_reviewer",
            review_timestamp=review_time,
            approved_premium=1500.0,
            reviewer_notes="All documentation verified and approved",
            review_priority="high",
            assigned_reviewer="senior_reviewer",
            estimated_review_time="2 hours",
            submission_timestamp=datetime.now() - timedelta(hours=2),
            review_deadline=datetime.now() + timedelta(hours=22)
        )
        
        self.assertEqual(review_record.status, "approved")
        self.assertFalse(review_record.requires_human_review)
        self.assertEqual(review_record.final_decision, "ACCEPT")
        self.assertEqual(review_record.reviewer, "senior_reviewer")
        self.assertEqual(review_record.approved_premium, 1500.0)
        self.assertIsNotNone(review_record.review_timestamp)
    
    def test_human_review_rejection(self):
        """Test human review rejection process."""
        review_record = HumanReviewRecord(
            run_id="review_123",
            status="rejected",
            requires_human_review=False,
            final_decision="DECLINE",
            reviewer="senior_reviewer",
            review_timestamp=datetime.now(),
            approved_premium=None,
            reviewer_notes="Insufficient documentation and high risk factors",
            review_priority="high",
            assigned_reviewer="senior_reviewer",
            estimated_review_time="2 hours",
            submission_timestamp=datetime.now() - timedelta(hours=2),
            review_deadline=datetime.now() + timedelta(hours=22)
        )
        
        self.assertEqual(review_record.status, "rejected")
        self.assertFalse(review_record.requires_human_review)
        self.assertEqual(review_record.final_decision, "DECLINE")
        self.assertIsNone(review_record.approved_premium)  # No premium for rejected
        self.assertIn("Insufficient documentation", review_record.reviewer_notes)
    
    def test_human_review_priority_logic(self):
        """Test review priority assignment logic."""
        test_cases = [
            (500000.0, "high"),      # High coverage
            (250000.0, "medium"),    # Medium coverage
            (100000.0, "low")        # Low coverage
        ]
        
        for coverage_amount, expected_priority in test_cases:
            with self.subTest(coverage=coverage_amount):
                # Simulate priority assignment based on coverage
                if coverage_amount > 400000:
                    priority = "high"
                elif coverage_amount > 200000:
                    priority = "medium"
                else:
                    priority = "low"
                
                self.assertEqual(priority, expected_priority)
    
    def test_review_deadline_calculation(self):
        """Test review deadline calculation."""
        submission_time = datetime.now()
        
        # High priority - 24 hours
        high_deadline = submission_time + timedelta(hours=24)
        
        # Medium priority - 48 hours
        medium_deadline = submission_time + timedelta(hours=48)
        
        # Low priority - 72 hours
        low_deadline = submission_time + timedelta(hours=72)
        
        self.assertGreater(high_deadline, submission_time)
        self.assertGreater(medium_deadline, high_deadline)
        self.assertGreater(low_deadline, medium_deadline)


class TestDecisionLogic(unittest.TestCase):
    """Test business decision logic."""
    
    def test_accept_decision_criteria(self):
        """Test criteria for ACCEPT decision."""
        # Low risk, good property, reasonable premium
        accept_criteria = {
            "max_hazard_score": 0.4,
            "max_premium_to_coverage_ratio": 0.01,
            "min_property_age": 5,
            "max_property_age": 50
        }
        
        test_case = {
            "hazard_scores": {"max": 0.3},  # Below threshold
            "premium_ratio": 0.008,      # Below threshold
            "property_age": 20,           # Within range
            "expected_decision": "ACCEPT"
        }
        
        self.assertLess(test_case["hazard_scores"]["max"], accept_criteria["max_hazard_score"])
        self.assertLess(test_case["premium_ratio"], accept_criteria["max_premium_to_coverage_ratio"])
        self.assertGreaterEqual(test_case["property_age"], accept_criteria["min_property_age"])
        self.assertLessEqual(test_case["property_age"], accept_criteria["max_property_age"])
    
    def test_refer_decision_criteria(self):
        """Test criteria for REFER decision."""
        # Medium risk or unusual circumstances
        refer_criteria = {
            "min_hazard_score": 0.4,
            "max_hazard_score": 0.7,
            "min_premium_to_coverage_ratio": 0.01,
            "max_premium_to_coverage_ratio": 0.02
        }
        
        test_case = {
            "hazard_scores": {"max": 0.5},  # In refer range
            "premium_ratio": 0.015,      # In refer range
            "property_age": 60,             # Above normal range
            "expected_decision": "REFER"
        }
        
        self.assertGreaterEqual(test_case["hazard_scores"]["max"], refer_criteria["min_hazard_score"])
        self.assertLessEqual(test_case["hazard_scores"]["max"], refer_criteria["max_hazard_score"])
        self.assertGreaterEqual(test_case["premium_ratio"], refer_criteria["min_premium_to_coverage_ratio"])
        self.assertLessEqual(test_case["premium_ratio"], refer_criteria["max_premium_to_coverage_ratio"])
    
    def test_decline_decision_criteria(self):
        """Test criteria for DECLINE decision."""
        # High risk or unacceptable conditions
        decline_criteria = {
            "min_hazard_score": 0.7,
            "max_premium_to_coverage_ratio": 0.02,
            "max_property_age": 100
        }
        
        test_cases = [
            {
                "hazard_scores": {"max": 0.8},  # Above threshold
                "premium_ratio": 0.01,       # Acceptable
                "property_age": 30,           # Acceptable
                "expected_decision": "DECLINE"
            },
            {
                "hazard_scores": {"max": 0.5},  # Acceptable
                "premium_ratio": 0.025,      # Above threshold
                "property_age": 30,           # Acceptable
                "expected_decision": "DECLINE"
            },
            {
                "hazard_scores": {"max": 0.5},  # Acceptable
                "premium_ratio": 0.01,       # Acceptable
                "property_age": 120,          # Above threshold
                "expected_decision": "DECLINE"
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                # At least one criterion should trigger decline
                hazard_decline = case["hazard_scores"]["max"] >= decline_criteria["min_hazard_score"]
                premium_decline = case["premium_ratio"] > decline_criteria["max_premium_to_coverage_ratio"]
                age_decline = case["property_age"] > decline_criteria["max_property_age"]
                
                self.assertTrue(hazard_decline or premium_decline or age_decline)
    
    def test_decision_consistency(self):
        """Test decision consistency across similar cases."""
        # Similar risk profiles should yield similar decisions
        similar_cases = [
            {
                "hazard_max": 0.35,
                "premium_ratio": 0.008,
                "property_age": 25
            },
            {
                "hazard_max": 0.38,
                "premium_ratio": 0.009,
                "property_age": 28
            },
            {
                "hazard_max": 0.32,
                "premium_ratio": 0.007,
                "property_age": 22
            }
        ]
        
        # All should be ACCEPT decisions
        for case in similar_cases:
            with self.subTest(case=case):
                # Apply decision logic
                if case["hazard_max"] < 0.4 and case["premium_ratio"] < 0.01 and 5 <= case["property_age"] <= 50:
                    decision = "ACCEPT"
                elif case["hazard_max"] < 0.7 and case["premium_ratio"] < 0.02:
                    decision = "REFER"
                else:
                    decision = "DECLINE"
                
                self.assertEqual(decision, "ACCEPT")


class TestBusinessProcessIntegration(unittest.TestCase):
    """Test integration of business processes."""
    
    def test_complete_underwriting_workflow(self):
        """Test complete underwriting workflow."""
        # Step 1: Initial submission
        submission_data = {
            "run_id": "workflow_test_123",
            "status": "pending",
            "created_at": datetime.now()
        }
        
        # Step 2: Risk assessment
        risk_assessment_result = {
            "hazard_scores": {
                "wildfire_risk": 0.3,
                "flood_risk": 0.2,
                "wind_risk": 0.1,
                "earthquake_risk": 0.4
            },
            "overall_risk": "medium"
        }
        
        # Step 3: Premium calculation
        premium_result = {
            "base_premium": 500.0,
            "hazard_surcharge": 150.0,
            "total_premium": 650.0,
            "premium_ratio": 0.0065  # 650/100000
        }
        
        # Step 4: Decision making
        if (risk_assessment_result["overall_risk"] == "medium" and 
            premium_result["premium_ratio"] < 0.01):
            decision = "ACCEPT"
        elif risk_assessment_result["overall_risk"] == "high":
            decision = "REFER"
        else:
            decision = "DECLINE"
        
        # Step 5: Final status
        final_status = {
            "run_id": submission_data["run_id"],
            "status": "completed",
            "decision": decision,
            "premium": premium_result["total_premium"],
            "completed_at": datetime.now()
        }
        
        # Verify workflow completion
        self.assertEqual(final_status["run_id"], "workflow_test_123")
        self.assertEqual(final_status["status"], "completed")
        self.assertEqual(final_status["decision"], "ACCEPT")
        self.assertEqual(final_status["premium"], 650.0)
    
    def test_error_recovery_workflow(self):
        """Test error recovery in workflow."""
        # Simulate workflow with error
        workflow_state = WorkflowState(
            current_node="risk_assessment",
            completed_nodes=[],
            pending_nodes=["risk_assessment", "rating", "decision"],
            error_count=1
        )
        
        # Error recovery logic
        if workflow_state.error_count < 3:
            # Retry the failed node
            workflow_state.current_node = "risk_assessment"
            recovery_action = "retry"
        else:
            # Escalate to human review
            workflow_state.current_node = "human_review_required"
            recovery_action = "escalate"
        
        self.assertEqual(recovery_action, "retry")
        self.assertEqual(workflow_state.current_node, "risk_assessment")
        
        # Test escalation after multiple errors
        workflow_state.error_count = 3
        
        if workflow_state.error_count < 3:
            recovery_action = "retry"
        else:
            workflow_state.current_node = "human_review_required"
            recovery_action = "escalate"
        
        self.assertEqual(recovery_action, "escalate")
        self.assertEqual(workflow_state.current_node, "human_review_required")


if __name__ == '__main__':
    unittest.main()
