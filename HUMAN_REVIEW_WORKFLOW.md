# Human-in-the-Loop Workflow for Referred Quotes

## Overview

This feature implements a comprehensive human-in-the-loop workflow for quotes that require human review, following production best practices for safety and compliance.

## Workflow Scenarios

### 1. Automatic Referral Triggers

Quotes are automatically referred for human review when:

- **Coverage Amount > $500,000**: Exceeds maximum limit
- **Coverage Amount < $100,000**: Below minimum threshold  
- **Edge Cases**: Unusual property characteristics or risk factors

### 2. Human Review Process

#### **Review Assignment**
- **Assigned Team**: `underwriting_team`
- **Priority**: `high` for referred cases
- **SLA**: 24-48 hours review time
- **Tracking**: Full audit trail maintained

#### **Review Actions**
Human reviewer can:
- **ACCEPT**: Override with adjusted premium
- **REJECT**: Confirm rejection with detailed reasoning  
- **REFER**: Request additional information

## API Endpoints

### 1. Quote Processing
```http
POST /quote/run
```
Returns `requires_human_review: true` for referred cases.

### 2. Review Status Check
```http
GET /quote/{run_id}/review-status
```

**Response**:
```json
{
  "run_id": "uuid",
  "status": "pending_review",
  "requires_human_review": true,
  "assigned_reviewer": "underwriting_team", 
  "review_priority": "high",
  "estimated_review_time": "24-48 hours",
  "submission_timestamp": "2026-02-20T...",
  "review_deadline": "2026-02-22T..."
}
```

### 3. Human Approval
```http
POST /quote/{run_id}/approve
```

**Request Body**:
```json
{
  "final_decision": "ACCEPT",
  "approved_premium": 1200.00,
  "reviewer_notes": "Approved after manual review of property characteristics",
  "reviewer_name": "John Smith"
}
```

**Response**:
```json
{
  "run_id": "uuid",
  "status": "human_approved",
  "original_decision": "REFER",
  "final_decision": "ACCEPT", 
  "reviewer_notes": "Approved after manual review...",
  "approved_premium": 1200.00,
  "reviewer": "John Smith",
  "review_timestamp": "2026-02-20T...",
  "message": "Human review completed - ACCEPT"
}
```

## Browser Interface Features

### 1. Quote Submission
- Automatic detection of referral requirements
- Clear indication when human review is needed
- Detailed review information displayed

### 2. Review Status
- Real-time status checking
- Priority and deadline information
- Assigned reviewer details

### 3. Human Approval Form
- Secure approval interface for reviewers
- Required field validation
- Decision and premium override capability

## Production Benefits

### 1. Safety & Compliance
- **Risk Mitigation**: Human oversight for high-value cases
- **Regulatory Compliance**: Manual review for exceptions
- **Audit Trail**: Complete decision documentation

### 2. Operational Efficiency
- **Clear SLAs**: 24-48 hour review commitment
- **Priority Routing**: High-priority handling for referred cases
- **Status Transparency**: Real-time tracking available

### 3. Cost Management
- **Targeted Review**: Only necessary cases referred
- **Quick Resolution**: Streamlined approval process
- **Resource Optimization**: Automated where possible, human where needed

## Testing Scenarios

### 1. High Coverage Test
- **Input**: $600,000 coverage
- **Expected**: REFER with human review required
- **Test**: Verify human review workflow activation

### 2. Low Coverage Test  
- **Input**: $50,000 coverage
- **Expected**: REFER with human review required
- **Test**: Verify minimum threshold logic

### 3. Standard Coverage Test
- **Input**: $250,000 coverage
- **Expected**: ACCEPT without human review
- **Test**: Verify normal processing path

### 4. Human Approval Test
- **Step 1**: Submit referred quote
- **Step 2**: Check review status
- **Step 3**: Approve with human reviewer credentials
- **Expected**: Status changes to "human_approved"

## Security Considerations

### 1. Access Control
- Human approval endpoints should be protected
- Reviewer authentication required
- Role-based permissions enforced

### 2. Data Integrity
- Immutable audit logs
- Tamper-evident decision records
- Complete change history

### 3. Compliance
- SOX compliance for financial decisions
- Regulatory audit requirements met
- Decision rationale documentation

## Monitoring & Alerting

### 1. Review SLA Monitoring
- Alert if review exceeds 48 hours
- Queue depth monitoring
- Reviewer workload tracking

### 2. Quality Metrics
- Human vs. automated decision accuracy
- Reviewer performance metrics
- Approval turnaround time analytics

This human-in-the-loop system ensures that high-value or complex cases receive appropriate human oversight while maintaining operational efficiency for standard cases.
