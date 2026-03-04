# Database Documentation

## Overview

The AgenticQuote system uses **SQLite** as its primary database for storing underwriting records, human review workflows, and audit trails. The database is designed for reliability, performance, and comprehensive tracking of all underwriting operations.

## Database Architecture

### **Database Engine**
- **Type**: SQLite 3.x
- **Location**: `storage/underwriting.db`
- **Connection Pool**: Single connection with thread-safe operations
- **Backup Strategy**: File-based backups with journaling enabled

### **Schema Design Principles**
- **ACID Compliance**: All transactions are atomic, consistent, isolated, and durable
- **Indexing Strategy**: Optimized for common query patterns
- **Data Integrity**: Foreign key constraints and validation rules
- **Audit Trail**: Complete history of all operations

## Database Tables

### 1. `run_records`

**Purpose**: Stores workflow execution records and state management

```sql
CREATE TABLE run_records (
    run_id TEXT PRIMARY KEY,                    -- Unique identifier for each run
    created_at TEXT NOT NULL,                    -- ISO timestamp when run was created
    updated_at TEXT NOT NULL,                    -- ISO timestamp of last update
    status TEXT NOT NULL,                        -- Current status (processing, completed, failed)
    workflow_state TEXT NOT NULL,                -- JSON serialized WorkflowState object
    node_outputs TEXT,                           -- JSON serialized node execution results
    error_message TEXT                           -- Error details if run failed
);
```

**Indexes**:
- `idx_run_id` - Primary key lookup
- `idx_created_at` - Chronological ordering
- `idx_status` - Status-based filtering

**Sample Data**:
```json
{
  "run_id": "run_abc123",
  "created_at": "2026-03-03T19:59:00Z",
  "updated_at": "2026-03-03T20:01:30Z",
  "status": "completed",
  "workflow_state": "{\"current_node\":\"decision_composer\",\"completed_nodes\":[\"validate\",\"enrich\",\"retrieve\"]}",
  "node_outputs": "{\"validate\":{\"valid\":true},\"enrich\":{\"address_normalized\":true}}",
  "error_message": null
}
```

### 2. `human_review_records`

**Purpose**: Manages human-in-the-loop review workflow

```sql
CREATE TABLE human_review_records (
    run_id TEXT PRIMARY KEY,                    -- Foreign key to run_records
    status TEXT NOT NULL,                        -- Review status (pending_review, approved, rejected)
    requires_human_review BOOLEAN NOT NULL DEFAULT 1,  -- Flag for human intervention
    final_decision TEXT,                         -- Final decision after review
    reviewer TEXT,                               -- Name/ID of reviewer
    review_timestamp TEXT,                       -- ISO timestamp of review completion
    approved_premium REAL,                       -- Premium amount after human review
    reviewer_notes TEXT,                         -- Reviewer comments and reasoning
    review_priority TEXT,                        -- Priority level (high, medium, low)
    assigned_reviewer TEXT,                      -- Assigned reviewer
    estimated_review_time TEXT,                  -- Estimated time for review
    submission_timestamp TEXT,                   -- When review was submitted
    review_deadline TEXT                         -- Deadline for review completion
);
```

**Indexes**:
- `idx_review_run_id` - Primary key lookup
- `idx_review_status` - Status-based filtering

**Sample Data**:
```json
{
  "run_id": "run_abc123",
  "status": "approved",
  "requires_human_review": true,
  "final_decision": "ACCEPT",
  "reviewer": "john.doe@company.com",
  "review_timestamp": "2026-03-03T20:05:00Z",
  "approved_premium": 1250.00,
  "reviewer_notes": "Property meets all eligibility criteria. No additional concerns.",
  "review_priority": "medium",
  "assigned_reviewer": "jane.smith@company.com",
  "estimated_review_time": "2 hours",
  "submission_timestamp": "2026-03-03T20:02:00Z",
  "review_deadline": "2026-03-03T22:00:00Z"
}
```

### 3. `quote_records`

**Purpose**: Stores complete quote processing records and results

```sql
CREATE TABLE quote_records (
    run_id TEXT PRIMARY KEY,                    -- Foreign key to run_records
    status TEXT NOT NULL,                        -- Processing status
    timestamp TEXT NOT NULL,                     -- Quote processing timestamp
    message TEXT NOT NULL,                       -- Status message or result
    processing_time_ms INTEGER NOT NULL,         -- Total processing time in milliseconds
    submission TEXT NOT NULL,                    -- JSON serialized QuoteSubmission
    decision TEXT,                               -- JSON serialized decision details
    premium TEXT,                                -- JSON serialized premium calculation
    rce_adjustment TEXT,                         -- JSON serialized RCE adjustment info
    requires_human_review BOOLEAN NOT NULL DEFAULT 0,  -- Human review flag
    human_review_details TEXT,                   -- JSON serialized review details
    required_questions TEXT,                      -- JSON serialized missing info questions
    citations TEXT                               -- JSON serialized evidence citations
);
```

**Indexes**:
- `idx_quote_run_id` - Primary key lookup
- `idx_quote_status` - Status-based filtering
- `idx_quote_timestamp` - Chronological ordering

**Sample Data**:
```json
{
  "run_id": "run_abc123",
  "status": "completed",
  "timestamp": "2026-03-03T20:01:30Z",
  "message": "Quote processed successfully",
  "processing_time_ms": 1500,
  "submission": "{\"applicant_name\":\"John Doe\",\"address\":\"123 Main St\",\"property_type\":\"single_family\",\"coverage_amount\":500000}",
  "decision": "{\"decision\":\"ACCEPT\",\"confidence\":0.85,\"reasoning\":\"Property meets all eligibility criteria\"}",
  "premium": "{\"base_premium\":1000,\"hazard_surcharge\":250,\"total_premium\":1250}",
  "rce_adjustment": null,
  "requires_human_review": false,
  "human_review_details": null,
  "required_questions": [],
  "citations": "[{\"doc_id\":\"uw_guide_001\",\"section\":\"eligibility\",\"confidence\":0.9}]"
}
```

## Data Relationships

### **Entity Relationship Diagram**

```
run_records (1) ──── (1) quote_records
    │
    └─── (1) ──── (1) human_review_records
```

### **Key Relationships**
- **One-to-One**: `run_records` ↔ `quote_records` (each run has one quote record)
- **One-to-One**: `run_records` ↔ `human_review_records` (optional, only if human review required)
- **Primary Key**: `run_id` links all tables together

## Database Operations

### **Core Operations**

#### **Run Management**
```python
# Save run record
db.save_run_record(run_record)

# Retrieve run record
run = db.get_run_record(run_id)

# List recent runs
runs = db.list_runs(limit=50, status="completed")

# Update run status
db.update_run_status(run_id, "completed")

# Delete run record
success = db.delete_run(run_id)
```

#### **Quote Processing**
```python
# Save quote record
db.save_quote_record(quote_record)

# Retrieve quote record
quote = db.get_quote_record(run_id)
```

#### **Human Review Workflow**
```python
# Save review record
db.save_human_review_record(review_record)

# Retrieve review record
review = db.get_human_review_record(run_id)
```

### **Statistics and Analytics**
```python
# Get database statistics
stats = db.get_statistics()
# Returns: {
#   "total_runs": 1250,
#   "recent_runs_24h": 45,
#   "runs_by_status": {"completed": 1100, "processing": 25, "failed": 125}
# }
```

## Performance Considerations

### **Indexing Strategy**
- **Primary Keys**: Automatically indexed by SQLite
- **Foreign Keys**: Indexed for fast joins
- **Query Patterns**: Indexes on frequently filtered columns (status, timestamp)
- **Composite Indexes**: Not needed due to simple query patterns

### **Query Optimization**
- **Prepared Statements**: Used for all database operations
- **Connection Pooling**: Single connection with proper transaction management
- **Batch Operations**: Not needed due to low volume
- **Caching**: Application-level caching for frequently accessed data

### **Storage Requirements**
- **Estimated Size**: ~1KB per run record
- **Growth Rate**: ~100 runs/day = ~100KB/day
- **Retention**: No automatic cleanup (manual archival required)
- **Backup Strategy**: File-based backups with version control

## Data Integrity

### **Constraints**
- **NOT NULL**: Required fields enforced at database level
- **UNIQUE**: Primary keys prevent duplicates
- **CHECK**: Boolean fields validated
- **Foreign Keys**: Logical relationships maintained

### **Validation**
- **JSON Schema**: Application-level validation for JSON fields
- **Type Safety**: Pydantic models ensure data consistency
- **Timestamp Format**: ISO 8601 format enforced
- **Business Rules**: Application logic enforces underwriting rules

## Security Considerations

### **Access Control**
- **File Permissions**: Database file restricted to application user
- **SQL Injection**: Prepared statements prevent injection attacks
- **Data Encryption**: At rest encryption handled by filesystem
- **Audit Trail**: All operations logged with timestamps

### **Privacy Protection**
- **PII Handling**: Personal information stored in JSON fields
- **Data Retention**: Configurable retention policies
- **Compliance**: GDPR/CCPA considerations for data storage
- **Anonymization**: Options for data anonymization in analytics

## Backup and Recovery

### **Backup Strategy**
```bash
# Full backup
cp storage/underwriting.db backup/underwriting_$(date +%Y%m%d_%H%M%S).db

# Incremental backup (SQLite journal mode)
sqlite3 storage/underwriting.db ".backup backup/incremental_$(date +%Y%m%d_%H%M%S).db"
```

### **Recovery Procedures**
```bash
# Restore from backup
cp backup/underwriting_20260303_200000.db storage/underwriting.db

# Check database integrity
sqlite3 storage/underwriting.db "PRAGMA integrity_check;"
```

### **Disaster Recovery**
- **Point-in-Time Recovery**: Using backup files
- **Replication**: Not implemented (single node)
- **Failover**: Manual process with backup restoration
- **RTO**: < 5 minutes for backup restoration

## Monitoring and Maintenance

### **Database Health Checks**
```python
# Connection test
db = UnderwritingDB()
db.init_db()  # Verifies database accessibility

# Statistics monitoring
stats = db.get_statistics()
if stats["recent_runs_24h"] > 1000:
    # Alert: High activity detected
```

### **Maintenance Tasks**
- **Vacuum**: Periodic database optimization
- **Index Rebuild**: Automatic with SQLite
- **Log Rotation**: Application-level log management
- **Archive**: Manual archival of old records

## Migration and Versioning

### **Schema Versioning**
- **Current Version**: v1.0
- **Migration Strategy**: Application-level migrations
- **Backward Compatibility**: Maintained for minor versions
- **Breaking Changes**: Major version increments only

### **Migration Scripts**
```python
# Example migration
def migrate_v1_to_v2():
    """Add new columns to quote_records table"""
    with sqlite3.connect(db_path) as conn:
        conn.execute("ALTER TABLE quote_records ADD COLUMN new_field TEXT")
```

## Integration Points

### **Application Integration**
- **FastAPI**: Database dependency injection
- **LangGraph**: Workflow state persistence
- **RAG Engine**: Evidence storage and retrieval
- **LLM Engine**: Decision audit trail

### **External Systems**
- **Monitoring**: Database metrics collection
- **Backup**: Automated backup systems
- **Analytics**: Business intelligence tools
- **Compliance**: Audit and reporting systems

## Troubleshooting

### **Common Issues**

#### **Database Lock**
```python
# Symptom: "database is locked" error
# Solution: Ensure proper connection management
with sqlite3.connect(db_path) as conn:
    # Database operations
```

#### **Corruption**
```bash
# Symptom: "database disk image is malformed"
# Solution: Integrity check and recovery
sqlite3 underwriting.db ".recover" | sqlite3 recovered.db
```

#### **Performance Issues**
```python
# Symptom: Slow query performance
# Solution: Add missing indexes
conn.execute("CREATE INDEX idx_missing ON table_name(column_name)")
```

### **Debugging Tools**
```bash
# Database schema
sqlite3 underwriting.db ".schema"

# Table statistics
sqlite3 underwriting.db "SELECT COUNT(*) FROM run_records;"

# Query plan
sqlite3 underwriting.db "EXPLAIN QUERY PLAN SELECT * FROM run_records WHERE status = 'completed';"
```

## Best Practices

### **Development**
- **Use Transactions**: Always wrap operations in transactions
- **Handle Exceptions**: Proper error handling and logging
- **Validate Input**: Application-level validation before database operations
- **Use Prepared Statements**: Prevent SQL injection

### **Production**
- **Regular Backups**: Automated backup schedule
- **Monitor Performance**: Track query performance and database size
- **Plan Capacity**: Anticipate growth and plan scaling
- **Document Changes**: Maintain migration scripts and changelog

### **Security**
- **Principle of Least Privilege**: Minimal database permissions
- **Encrypt Sensitive Data**: Protect PII at rest
- **Audit Access**: Log all database operations
- **Regular Updates**: Keep SQLite version updated

---

**Last Updated**: 2026-03-03  
**Version**: 1.0  
**Maintainer**: AgenticQuote Development Team
