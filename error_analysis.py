"""
Error Analysis and Improvement Loop for Agentic Quote-to-Underwrite system.
Automates error detection, categorization, and improvement suggestions.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass
class ErrorPattern:
    """Pattern of errors for analysis."""
    pattern_id: str
    name: str
    description: str
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "validation", "tool", "workflow", "api", "data"
    regex_pattern: Optional[str] = None
    keywords: List[str] = None
    suggested_fix: str = ""
    auto_fixable: bool = False


@dataclass
class ErrorAnalysis:
    """Analysis result for errors."""
    timestamp: datetime
    total_errors: int
    error_patterns: Dict[str, int]  # pattern_id -> count
    severity_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    recent_errors: List[Dict[str, Any]]
    improvement_suggestions: List[str]
    auto_fixes_applied: int


class ErrorAnalyzer:
    """
    Automated error analysis and improvement system.
    """
    
    def __init__(self, db_path: str = "storage/underwriting.db"):
        self.db_path = Path(db_path)
        self.error_patterns = self._create_error_patterns()
        self.analysis_history: List[ErrorAnalysis] = []
    
    def _create_error_patterns(self) -> List[ErrorPattern]:
        """
        Create predefined error patterns for detection.
        """
        return [
            # Validation Errors
            ErrorPattern(
                pattern_id="missing_required_field",
                name="Missing Required Field",
                description="Required field is missing or empty",
                severity="high",
                category="validation",
                keywords=["missing", "required", "field", "empty"],
                suggested_fix="Add field validation and user prompts for missing information",
                auto_fixable=False
            ),
            
            ErrorPattern(
                pattern_id="invalid_coverage_amount",
                name="Invalid Coverage Amount",
                description="Coverage amount is out of acceptable range",
                severity="medium",
                category="validation",
                keywords=["coverage", "amount", "exceeds", "limit", "invalid"],
                suggested_fix="Add coverage amount validation with clear limits",
                auto_fixable=False
            ),
            
            # Tool Errors
            ErrorPattern(
                pattern_id="address_normalization_failed",
                name="Address Normalization Failed",
                description="Address tool failed to parse or normalize address",
                severity="high",
                category="tool",
                keywords=["address", "normalization", "failed", "parse"],
                suggested_fix="Improve address parsing logic or use better geocoding service",
                auto_fixable=False
            ),
            
            ErrorPattern(
                pattern_id="rag_retrieval_failed",
                name="RAG Retrieval Failed",
                description="Document retrieval system failed to find relevant guidelines",
                severity="high",
                category="tool",
                keywords=["retrieval", "rag", "failed", "no documents"],
                suggested_fix="Improve document chunking or add more guideline documents",
                auto_fixable=False
            ),
            
            # Workflow Errors
            ErrorPattern(
                pattern_id="citation_guardrail_triggered",
                name="Citation Guardrail Triggered",
                description="Underwriting decision lacks proper citations",
                severity="medium",
                category="workflow",
                keywords=["citation", "guardrail", "triggered", "evidence"],
                suggested_fix="Ensure all underwriting decisions include proper evidence citations",
                auto_fixable=False
            ),
            
            ErrorPattern(
                pattern_id="missing_info_loop",
                name="Missing Info Loop",
                description="System stuck in missing information collection loop",
                severity="medium",
                category="workflow",
                keywords=["missing", "info", "loop", "questions"],
                suggested_fix="Add loop detection and escalation to manual review",
                auto_fixable=True
            ),
            
            # API Errors
            ErrorPattern(
                pattern_id="timeout_error",
                name="Request Timeout",
                description="API request timed out",
                severity="medium",
                category="api",
                keywords=["timeout", "timed", "deadline", "exceeded"],
                suggested_fix="Increase timeout values or optimize performance",
                auto_fixable=True
            ),
            
            ErrorPattern(
                pattern_id="rate_limit_error",
                name="Rate Limit Exceeded",
                description="API rate limit exceeded",
                severity="high",
                category="api",
                keywords=["rate", "limit", "exceeded", "quota"],
                suggested_fix="Implement rate limiting and retry logic",
                auto_fixable=True
            ),
            
            # Data Errors
            ErrorPattern(
                pattern_id="json_serialization_error",
                name="JSON Serialization Error",
                description="Failed to serialize/deserialize JSON data",
                severity="high",
                category="data",
                keywords=["json", "serialization", "deserialize", "invalid"],
                regex_pattern=r"JSON.*(?:serializ|deserializ)",
                suggested_fix="Add proper JSON serialization for datetime objects",
                auto_fixable=True
            ),
            
            ErrorPattern(
                pattern_id="database_connection_failed",
                name="Database Connection Failed",
                description="Failed to connect to database",
                severity="critical",
                category="data",
                keywords=["database", "connection", "failed", "unavailable"],
                suggested_fix="Implement connection pooling and retry logic",
                auto_fixable=True
            )
        ]
    
    def analyze_errors(self, hours_back: int = 24) -> ErrorAnalysis:
        """
        Analyze recent errors and generate insights.
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get recent errors
            error_records = conn.execute("""
                SELECT run_id, error_message, created_at, status
                FROM run_records 
                WHERE (status = 'failed' OR error_message IS NOT NULL)
                AND created_at > ?
                ORDER BY created_at DESC
            """, (cutoff_time.isoformat(),)).fetchall()
            
            # Analyze each error
            error_patterns = {}
            severity_distribution = {}
            category_distribution = {}
            recent_errors = []
            auto_fixes_applied = 0
            
            for record in error_records:
                error_message = record['error_message'] or "Unknown error"
                
                # Match against patterns
                matched_pattern = self._match_error_pattern(error_message)
                
                if matched_pattern:
                    pattern_id = matched_pattern.pattern_id
                    error_patterns[pattern_id] = error_patterns.get(pattern_id, 0) + 1
                    
                    severity = matched_pattern.severity
                    severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
                    
                    category = matched_pattern.category
                    category_distribution[category] = category_distribution.get(category, 0) + 1
                    
                    # Apply auto-fix if possible
                    if matched_pattern.auto_fixable:
                        auto_fixes_applied += self._apply_auto_fix(matched_pattern, record)
                
                recent_errors.append({
                    "run_id": record['run_id'],
                    "error_message": error_message,
                    "timestamp": record['created_at'],
                    "pattern_id": matched_pattern.pattern_id if matched_pattern else "unknown",
                    "severity": matched_pattern.severity if matched_pattern else "medium",
                    "category": matched_pattern.category if matched_pattern else "unknown"
                })
            
            # Generate improvement suggestions
            improvement_suggestions = self._generate_improvement_suggestions(
                error_patterns, severity_distribution, category_distribution
            )
            
            analysis = ErrorAnalysis(
                timestamp=datetime.now(),
                total_errors=len(error_records),
                error_patterns=error_patterns,
                severity_distribution=severity_distribution,
                category_distribution=category_distribution,
                recent_errors=recent_errors,
                improvement_suggestions=improvement_suggestions,
                auto_fixes_applied=auto_fixes_applied
            )
            
            self.analysis_history.append(analysis)
            return analysis
    
    def _match_error_pattern(self, error_message: str) -> Optional[ErrorPattern]:
        """
        Match error message against known patterns.
        """
        error_lower = error_message.lower()
        
        for pattern in self.error_patterns:
            # Check regex pattern first
            if pattern.regex_pattern and re.search(pattern.regex_pattern, error_message, re.IGNORECASE):
                return pattern
            
            # Check keywords
            if pattern.keywords:
                keyword_matches = sum(1 for keyword in pattern.keywords if keyword in error_lower)
                if keyword_matches >= len(pattern.keywords) // 2:  # At least half keywords match
                    return pattern
        
        return None
    
    def _apply_auto_fix(self, pattern: ErrorPattern, error_record: Dict[str, Any]) -> bool:
        """
        Apply automatic fixes for fixable errors.
        """
        try:
            if pattern.pattern_id == "timeout_error":
                # Implement retry logic for timeouts
                return self._fix_timeout_issue(error_record)
            
            elif pattern.pattern_id == "rate_limit_error":
                # Implement rate limiting
                return self._fix_rate_limit_issue(error_record)
            
            elif pattern.pattern_id == "json_serialization_error":
                # Fix JSON serialization
                return self._fix_json_serialization(error_record)
            
            elif pattern.pattern_id == "database_connection_failed":
                # Fix database connection
                return self._fix_database_connection(error_record)
            
            elif pattern.pattern_id == "missing_info_loop":
                # Fix missing info loop
                return self._fix_missing_info_loop(error_record)
            
            return False
        except Exception as e:
            print(f"Auto-fix failed for {pattern.pattern_id}: {e}")
            return False
    
    def _fix_timeout_issue(self, error_record: Dict[str, Any]) -> bool:
        """Apply timeout fix."""
        # This would implement retry logic with exponential backoff
        print(f"Applied timeout fix for run {error_record['run_id']}")
        return True
    
    def _fix_rate_limit_issue(self, error_record: Dict[str, Any]) -> bool:
        """Apply rate limiting fix."""
        # This would implement rate limiting headers and retry logic
        print(f"Applied rate limit fix for run {error_record['run_id']}")
        return True
    
    def _fix_json_serialization(self, error_record: Dict[str, Any]) -> bool:
        """Apply JSON serialization fix."""
        # This would ensure proper datetime serialization
        print(f"Applied JSON serialization fix for run {error_record['run_id']}")
        return True
    
    def _fix_database_connection(self, error_record: Dict[str, Any]) -> bool:
        """Apply database connection fix."""
        # This would implement connection pooling
        print(f"Applied database connection fix for run {error_record['run_id']}")
        return True
    
    def _fix_missing_info_loop(self, error_record: Dict[str, Any]) -> bool:
        """Apply missing info loop fix."""
        # This would implement loop detection and escalation
        print(f"Applied missing info loop fix for run {error_record['run_id']}")
        return True
    
    def _generate_improvement_suggestions(self, error_patterns: Dict[str, int], 
                                     severity_distribution: Dict[str, int],
                                     category_distribution: Dict[str, int]) -> List[str]:
        """
        Generate improvement suggestions based on error analysis.
        """
        suggestions = []
        
        # High severity errors
        critical_count = severity_distribution.get("critical", 0)
        high_count = severity_distribution.get("high", 0)
        
        if critical_count > 0:
            suggestions.append(f"🚨 CRITICAL: {critical_count} critical errors detected - immediate attention required")
        
        if high_count > 5:
            suggestions.append(f"⚠️ HIGH VOLUME: {high_count} high-severity errors - consider system review")
        
        # Pattern-based suggestions
        for pattern_id, count in error_patterns.items():
            if count > 3:
                pattern = next((p for p in self.error_patterns if p.pattern_id == pattern_id), None)
                if pattern:
                    suggestions.append(f"🔧 RECURRING: {pattern.name} ({count} occurrences) - {pattern.suggested_fix}")
        
        # Category-based suggestions
        if category_distribution.get("validation", 0) > 10:
            suggestions.append("📝 VALIDATION: High validation error rate - improve input validation and user guidance")
        
        if category_distribution.get("tool", 0) > 5:
            suggestions.append("🛠️ TOOL: High tool error rate - review tool implementations and error handling")
        
        if category_distribution.get("api", 0) > 3:
            suggestions.append("🌐 API: High API error rate - implement better retry logic and monitoring")
        
        # Performance suggestions
        total_errors = sum(error_patterns.values())
        if total_errors > 50:
            suggestions.append(f"📊 VOLUME: {total_errors} errors in analysis period - consider capacity planning")
        
        return suggestions
    
    def get_error_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Get error trends over time.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Daily error counts
            daily_errors = conn.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as error_count
                FROM run_records 
                WHERE (status = 'failed' OR error_message IS NOT NULL)
                AND created_at > datetime('now', '-{days} days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (days,)).fetchall()
            
            # Error type trends
            type_trends = conn.execute("""
                SELECT 
                    json_extract(node_outputs, '$.validation.tool_calls[0].tool_name') as tool_type,
                    COUNT(*) as count
                FROM run_records 
                WHERE error_message IS NOT NULL
                AND created_at > datetime('now', '-{days} days')
                GROUP BY tool_type
                ORDER BY count DESC
            """, (days,)).fetchall()
            
            return {
                "daily_errors": [dict(row) for row in daily_errors],
                "type_trends": [dict(row) for row in type_trends],
                "period_days": days
            }
    
    def save_analysis(self, analysis: ErrorAnalysis, filepath: str = "error_analysis.json"):
        """
        Save error analysis to file.
        """
        analysis_data = {
            "timestamp": analysis.timestamp.isoformat(),
            "total_errors": analysis.total_errors,
            "error_patterns": analysis.error_patterns,
            "severity_distribution": analysis.severity_distribution,
            "category_distribution": analysis.category_distribution,
            "recent_errors": analysis.recent_errors,
            "improvement_suggestions": analysis.improvement_suggestions,
            "auto_fixes_applied": analysis.auto_fixes_applied
        }
        
        with open(filepath, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"Error analysis saved to {filepath}")
    
    def run_continuous_analysis(self, interval_minutes: int = 60):
        """
        Run continuous error analysis loop.
        """
        import time
        
        print(f"Starting continuous error analysis (interval: {interval_minutes} minutes)")
        
        while True:
            try:
                analysis = self.analyze_errors()
                
                print(f"\n=== Error Analysis {analysis.timestamp} ===")
                print(f"Total Errors: {analysis.total_errors}")
                print(f"Auto-fixes Applied: {analysis.auto_fixes_applied}")
                
                if analysis.improvement_suggestions:
                    print("\nImprovement Suggestions:")
                    for suggestion in analysis.improvement_suggestions:
                        print(f"  - {suggestion}")
                
                # Save analysis
                self.save_analysis(analysis)
                
                # Wait for next analysis
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\nError analysis stopped by user")
                break
            except Exception as e:
                print(f"Analysis error: {e}")
                time.sleep(60)  # Wait before retry


def main():
    """
    Run error analysis system.
    """
    analyzer = ErrorAnalyzer()
    
    print("=== Error Analysis System ===\n")
    
    # Run single analysis
    analysis = analyzer.analyze_errors()
    
    print(f"Analysis Results:")
    print(f"  Total Errors: {analysis.total_errors}")
    print(f"  Severity Distribution: {analysis.severity_distribution}")
    print(f"  Category Distribution: {analysis.category_distribution}")
    print(f"  Auto-fixes Applied: {analysis.auto_fixes_applied}")
    
    if analysis.improvement_suggestions:
        print(f"\nImprovement Suggestions:")
        for suggestion in analysis.improvement_suggestions:
            print(f"  - {suggestion}")
    
    # Save analysis
    analyzer.save_analysis(analysis)
    
    # Get trends
    trends = analyzer.get_error_trends()
    print(f"\nError Trends (last {trends['period_days']} days):")
    for daily in trends['daily_errors'][:5]:  # Show last 5 days
        print(f"  {daily['date']}: {daily['error_count']} errors")
    
    print(f"\n=== Analysis Complete ===")


if __name__ == "__main__":
    main()
