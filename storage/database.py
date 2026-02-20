import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from models.schemas import RunRecord, WorkflowState


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class UnderwritingDB:
    """
    SQLite database for storing underwriting run records.
    """
    
    def __init__(self, db_path: str = "storage/underwriting.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """
        Initialize the database schema.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_records (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    workflow_state TEXT NOT NULL,
                    node_outputs TEXT,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_id ON run_records(run_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON run_records(created_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON run_records(status)
            """)
    
    def save_run_record(self, record: RunRecord) -> str:
        """
        Save a run record to the database.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO run_records 
                (run_id, created_at, updated_at, status, workflow_state, node_outputs, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.run_id,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                record.status,
                record.workflow_state.model_dump_json(),
                json.dumps(record.node_outputs, cls=DateTimeEncoder),
                record.error_message
            ))
        
        return record.run_id
    
    def get_run_record(self, run_id: str) -> Optional[RunRecord]:
        """
        Retrieve a run record by ID.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM run_records WHERE run_id = ?",
                (run_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            # Parse the data
            workflow_state = WorkflowState.model_validate_json(row['workflow_state'])
            node_outputs = json.loads(row['node_outputs']) if row['node_outputs'] else {}
            
            return RunRecord(
                run_id=row['run_id'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                status=row['status'],
                workflow_state=workflow_state,
                node_outputs=node_outputs,
                error_message=row['error_message']
            )
    
    def list_runs(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List recent runs with optional status filter.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT run_id, created_at, updated_at, status FROM run_records"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def update_run_status(self, run_id: str, status: str, error_message: Optional[str] = None):
        """
        Update the status of a run.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE run_records 
                SET status = ?, updated_at = ?, error_message = ?
                WHERE run_id = ?
            """, (
                status,
                datetime.now().isoformat(),
                error_message,
                run_id
            ))
    
    def delete_run(self, run_id: str) -> bool:
        """
        Delete a run record.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM run_records WHERE run_id = ?",
                (run_id,)
            )
            return cursor.rowcount > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get basic statistics about runs.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total runs
            total_runs = conn.execute("SELECT COUNT(*) as count FROM run_records").fetchone()['count']
            
            # Runs by status
            status_counts = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM run_records 
                GROUP BY status
            """).fetchall()
            
            # Recent runs (last 24 hours)
            recent_runs = conn.execute("""
                SELECT COUNT(*) as count 
                FROM run_records 
                WHERE created_at > datetime('now', '-1 day')
            """).fetchone()['count']
            
            return {
                "total_runs": total_runs,
                "recent_runs_24h": recent_runs,
                "runs_by_status": {row['status']: row['count'] for row in status_counts}
            }


# Global database instance
db = UnderwritingDB()
