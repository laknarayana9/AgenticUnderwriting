"""
Evaluation harness for the Agentic Quote-to-Underwrite system.
Provides automated testing with golden dataset and metrics calculation.
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import requests
from models.schemas import DecisionType


@dataclass
class TestCase:
    """Test case for evaluation."""
    test_id: str
    name: str
    submission: Dict[str, Any]
    use_agentic: bool = False
    additional_answers: Optional[Dict[str, Any]] = None
    expected_decision: Optional[str] = None
    expected_premium_range: Optional[Dict[str, float]] = None
    expected_citations_count: Optional[int] = None
    expected_missing_info: Optional[List[str]] = None
    description: str = ""


@dataclass
class EvaluationResult:
    """Result of a single test case evaluation."""
    test_case: TestCase
    actual_result: Dict[str, Any]
    success: bool
    execution_time: float
    errors: List[str]
    metrics: Dict[str, Any]


class EvaluationHarness:
    """
    Evaluation system for automated testing with golden dataset.
    """
    
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.golden_dataset = self._create_golden_dataset()
        self.results: List[EvaluationResult] = []
    
    def _create_golden_dataset(self) -> List[TestCase]:
        """
        Create golden dataset with expected outcomes.
        """
        return [
            # Test Case 1: Low Risk Property - Should ACCEPT
            TestCase(
                test_id="low_risk_accept",
                name="Low Risk Property - Should Accept",
                submission={
                    "applicant_name": "John Smith",
                    "address": "123 Main St, Irvine, CA 92620",
                    "property_type": "single_family",
                    "coverage_amount": 300000,
                    "construction_year": 2020,
                    "square_footage": 2000,
                    "roof_type": "tile",
                    "foundation_type": "concrete"
                },
                use_agentic=False,
                expected_decision="ACCEPT",
                expected_premium_range={"min": 600, "max": 1200},
                expected_citations_count=2,
                description="New construction in low-risk area should be accepted"
            ),
            
            # Test Case 2: High Wildfire Risk - Should REFER
            TestCase(
                test_id="wildfire_risk_refer",
                name="High Wildfire Risk - Should Refer",
                submission={
                    "applicant_name": "Jane Doe",
                    "address": "456 Oak Ave, Malibu, CA 90265",
                    "property_type": "single_family",
                    "coverage_amount": 800000,
                    "construction_year": 1965,
                    "square_footage": 1800,
                    "roof_type": "wood_shingle",
                    "foundation_type": "raised"
                },
                use_agentic=False,
                expected_decision="REFER",
                expected_citations_count=2,
                description="Old construction in high wildfire area should be referred"
            ),
            
            # Test Case 3: Missing Information - Should Request Info
            TestCase(
                test_id="missing_info_request",
                name="Missing Information - Should Request",
                submission={
                    "applicant_name": "",  # Missing
                    "address": "789 Pine St, Beverly Hills, CA 90210",
                    "property_type": "single_family",
                    "coverage_amount": 500000,
                    # Missing construction_year, square_footage
                },
                use_agentic=True,
                expected_decision="REFER",
                expected_missing_info=["applicant_name", "construction_year", "square_footage"],
                description="Incomplete submission should request missing information"
            ),
            
            # Test Case 4: Commercial Property - Should DECLINE
            TestCase(
                test_id="commercial_decline",
                name="Commercial Property - Should Decline",
                submission={
                    "applicant_name": "Business Owner",
                    "address": "321 Commerce Blvd, Los Angeles, CA 90001",
                    "property_type": "commercial",
                    "coverage_amount": 2000000,
                    "construction_year": 2015,
                    "square_footage": 5000,
                    "roof_type": "metal",
                    "foundation_type": "concrete"
                },
                use_agentic=False,
                expected_decision="DECLINE",
                description="Commercial property should be declined"
            ),
            
            # Test Case 5: Agentic with Additional Answers
            TestCase(
                test_id="agentic_with_answers",
                name="Agentic with Additional Answers",
                submission={
                    "applicant_name": "Mike Johnson",
                    "address": "555 Elm St, Pasadena, CA 91101",
                    "property_type": "condo",
                    "coverage_amount": 400000,
                    # Missing info to be provided
                },
                use_agentic=True,
                additional_answers={
                    "construction_year": 2018,
                    "square_footage": 1200,
                    "roof_type": "composite"
                },
                expected_decision="ACCEPT",
                description="Agentic workflow should process additional answers"
            ),
            
            # Test Case 6: Edge Case - Very High Coverage
            TestCase(
                test_id="high_coverage_refer",
                name="High Coverage Amount - Should Refer",
                submission={
                    "applicant_name": "Wealthy Client",
                    "address": "999 Luxury Lane, Newport Beach, CA 92663",
                    "property_type": "single_family",
                    "coverage_amount": 15000000,  # Very high
                    "construction_year": 2022,
                    "square_footage": 8000,
                    "roof_type": "slate",
                    "foundation_type": "concrete"
                },
                use_agentic=False,
                expected_decision="REFER",
                description="Very high coverage amount should be referred"
            )
        ]
    
    def run_evaluation(self, test_cases: Optional[List[TestCase]] = None) -> List[EvaluationResult]:
        """
        Run evaluation on test cases.
        """
        if test_cases is None:
            test_cases = self.golden_dataset
        
        results = []
        
        for test_case in test_cases:
            print(f"Running test: {test_case.name}")
            
            try:
                start_time = time.time()
                
                # Make API request
                request_data = {
                    "submission": test_case.submission,
                    "use_agentic": test_case.use_agentic
                }
                
                if test_case.additional_answers:
                    request_data["additional_answers"] = test_case.additional_answers
                
                response = requests.post(
                    f"{self.api_base}/quote/run",
                    json=request_data,
                    timeout=30
                )
                
                execution_time = time.time() - start_time
                
                if response.status_code == 200:
                    actual_result = response.json()
                    success, errors, metrics = self._evaluate_test_case(test_case, actual_result)
                else:
                    actual_result = {"error": response.text}
                    success = False
                    errors = [f"API Error: {response.status_code} - {response.text}"]
                    metrics = {}
                
                result = EvaluationResult(
                    test_case=test_case,
                    actual_result=actual_result,
                    success=success,
                    execution_time=execution_time,
                    errors=errors,
                    metrics=metrics
                )
                
                results.append(result)
                
                # Brief pause between tests
                time.sleep(0.5)
                
            except Exception as e:
                result = EvaluationResult(
                    test_case=test_case,
                    actual_result={"error": str(e)},
                    success=False,
                    execution_time=0,
                    errors=[f"Test execution error: {str(e)}"],
                    metrics={}
                )
                results.append(result)
        
        self.results = results
        return results
    
    def _evaluate_test_case(self, test_case: TestCase, actual_result: Dict[str, Any]) -> tuple[bool, List[str], Dict[str, Any]]:
        """
        Evaluate a single test case against expected outcomes.
        """
        errors = []
        metrics = {}
        success = True
        
        # Check decision
        actual_decision = actual_result.get("decision", {}).get("decision")
        if test_case.expected_decision and actual_decision != test_case.expected_decision:
            errors.append(f"Decision mismatch: expected {test_case.expected_decision}, got {actual_decision}")
            success = False
        
        metrics["decision_correct"] = actual_decision == test_case.expected_decision
        
        # Check premium range
        if test_case.expected_premium_range and actual_result.get("premium"):
            premium = actual_result["premium"].get("total_premium", 0)
            min_premium = test_case.expected_premium_range["min"]
            max_premium = test_case.expected_premium_range["max"]
            
            if not (min_premium <= premium <= max_premium):
                errors.append(f"Premium out of range: expected {min_premium}-{max_premium}, got {premium}")
                success = False
            
            metrics["premium_in_range"] = min_premium <= premium <= max_premium
            metrics["premium_amount"] = premium
        
        # Check citations count
        if test_case.expected_citations_count is not None:
            citations = actual_result.get("citations", [])
            actual_count = len(citations)
            expected_count = test_case.expected_citations_count
            
            if actual_count < expected_count:
                errors.append(f"Insufficient citations: expected >= {expected_count}, got {actual_count}")
                success = False
            
            metrics["citations_count"] = actual_count
            metrics["citations_adequate"] = actual_count >= expected_count
        
        # Check missing info
        if test_case.expected_missing_info:
            questions = actual_result.get("required_questions", [])
            actual_missing = [q.get("question_id", "").replace("missing_", "") for q in questions]
            
            for expected_field in test_case.expected_missing_info:
                if expected_field not in actual_missing:
                    errors.append(f"Missing expected question for: {expected_field}")
                    success = False
            
            metrics["missing_info_detected"] = len(actual_missing) > 0
            metrics["missing_info_correct"] = all(field in actual_missing for field in test_case.expected_missing_info)
        
        # Check execution status
        if actual_result.get("status") != "completed":
            errors.append(f"Workflow not completed: status={actual_result.get('status')}")
            success = False
        
        metrics["workflow_completed"] = actual_result.get("status") == "completed"
        
        return success, errors, metrics
    
    def calculate_overall_metrics(self) -> Dict[str, Any]:
        """
        Calculate overall evaluation metrics.
        """
        if not self.results:
            return {}
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        
        # Decision accuracy
        decision_correct = sum(1 for r in self.results if r.metrics.get("decision_correct", False))
        decision_accuracy = decision_correct / total_tests if total_tests > 0 else 0
        
        # Premium accuracy
        premium_tests = [r for r in self.results if "premium_in_range" in r.metrics]
        premium_correct = sum(1 for r in premium_tests if r.metrics.get("premium_in_range", False))
        premium_accuracy = premium_correct / len(premium_tests) if premium_tests else 0
        
        # Citation adequacy
        citation_tests = [r for r in self.results if "citations_adequate" in r.metrics]
        citation_adequate = sum(1 for r in citation_tests if r.metrics.get("citations_adequate", False))
        citation_accuracy = citation_adequate / len(citation_tests) if citation_tests else 0
        
        # Performance metrics
        avg_execution_time = sum(r.execution_time for r in self.results) / total_tests
        
        # Error analysis
        error_types = {}
        for result in self.results:
            for error in result.errors:
                error_type = error.split(":")[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "overall_success_rate": successful_tests / total_tests,
            "decision_accuracy": decision_accuracy,
            "premium_accuracy": premium_accuracy,
            "citation_accuracy": citation_accuracy,
            "avg_execution_time": avg_execution_time,
            "error_analysis": error_types,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_results(self, filepath: str = "evaluation_results.json"):
        """
        Save evaluation results to file.
        """
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_metrics": self.calculate_overall_metrics(),
            "test_results": [
                {
                    "test_id": r.test_case.test_id,
                    "name": r.test_case.name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "errors": r.errors,
                    "metrics": r.metrics,
                    "actual_result": r.actual_result
                }
                for r in self.results
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"Evaluation results saved to {filepath}")


def main():
    """
    Run evaluation harness.
    """
    harness = EvaluationHarness()
    
    print("=== Agentic Quote-to-Underwrite Evaluation ===\n")
    
    # Run evaluation
    results = harness.run_evaluation()
    
    # Calculate and display metrics
    metrics = harness.calculate_overall_metrics()
    
    print(f"\n=== Evaluation Results ===")
    print(f"Total Tests: {metrics['total_tests']}")
    print(f"Successful: {metrics['successful_tests']}")
    print(f"Success Rate: {metrics['overall_success_rate']:.1%}")
    print(f"Decision Accuracy: {metrics['decision_accuracy']:.1%}")
    print(f"Premium Accuracy: {metrics['premium_accuracy']:.1%}")
    print(f"Citation Accuracy: {metrics['citation_accuracy']:.1%}")
    print(f"Avg Execution Time: {metrics['avg_execution_time']:.2f}s")
    
    if metrics['error_analysis']:
        print(f"\nError Analysis:")
        for error_type, count in metrics['error_analysis'].items():
            print(f"  {error_type}: {count}")
    
    # Save results
    harness.save_results()
    
    print(f"\n=== Evaluation Complete ===")


if __name__ == "__main__":
    main()
