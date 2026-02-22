"""
Unit tests for the Agentic Quote system.

This test suite focuses on core business logic components:
- Rating and premium calculation logic
- Hazard assessment and risk scoring
- Data validation and business rules
- Workflow state management
- Database operations and persistence
- Integration between components

Test Structure:
- test_business_logic.py: Core business logic tests
- test_validation.py: Input validation and business rules
- test_workflows.py: Workflow and process logic
- conftest.py: Test fixtures and data factories
- run_tests.py: Test runner and utilities

Running Tests:
--------------
# Run all tests
python tests/run_tests.py

# Run with coverage
python tests/run_tests.py --coverage

# Run specific module
python tests/run_tests.py --module test_business_logic

# Run with pytest (if installed)
pytest tests/

Test Coverage:
-------------
Tests cover:
- RatingTool premium calculation algorithms
- HazardScoreTool risk assessment logic
- UnderwritingDB database operations
- Schema validation and business rules
- Workflow state transitions
- Decision logic and business processes
- Error handling and edge cases

Business Logic Tested:
----------------------
1. Premium Calculation:
   - Base rate calculations
   - Property type multipliers
   - Construction year discounts/surcharges
   - Hazard surcharge calculations
   - Rating factor transparency

2. Risk Assessment:
   - County-based hazard scoring
   - Risk level classification
   - Primary hazard identification
   - Score bounds validation

3. Data Validation:
   - Required field validation
   - Data type validation
   - Business rule constraints
   - Edge case handling

4. Workflow Management:
   - State transitions
   - Error handling and recovery
   - Completion logic
   - Human review escalation

5. Decision Logic:
   - Accept/Refer/Decline criteria
   - Risk-based decision making
   - Premium ratio calculations
   - Consistency validation

Mock Strategy:
-------------
Tests focus on actual business logic, not external dependencies:
- No external API calls
- No database connections (uses in-memory SQLite)
- No external service dependencies
- Pure business logic testing

This ensures tests are:
- Fast and reliable
- Independent of external systems
- Focused on business rules
- Easy to maintain and debug
"""
