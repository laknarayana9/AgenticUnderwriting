"""
Metrics Dashboard for Agentic Quote-to-Underwrite system.
Provides real-time metrics and visualizations.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from error_analysis import ErrorAnalyzer


class MetricsDashboard:
    """
    Metrics dashboard with real-time analytics and visualizations.
    """
    
    def __init__(self, db_path: str = "storage/underwriting.db"):
        self.db_path = Path(db_path)
    
    def get_metrics_data(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for dashboard.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Basic stats
            total_runs = conn.execute("SELECT COUNT(*) as count FROM run_records").fetchone()['count']
            
            # Recent activity (last 24h, 7d, 30d)
            now = datetime.now()
            last_24h = conn.execute("""
                SELECT COUNT(*) as count FROM run_records 
                WHERE created_at > datetime('now', '-1 day')
            """).fetchone()['count']
            
            last_7d = conn.execute("""
                SELECT COUNT(*) as count FROM run_records 
                WHERE created_at > datetime('now', '-7 days')
            """).fetchone()['count']
            
            last_30d = conn.execute("""
                SELECT COUNT(*) as count FROM run_records 
                WHERE created_at > datetime('now', '-30 days')
            """).fetchone()['count']
            
            # Status distribution
            status_counts = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM run_records 
                GROUP BY status
            """).fetchall()
            
            # Decision distribution
            decision_counts = conn.execute("""
                SELECT json_extract(workflow_state, '$.decision.decision') as decision, COUNT(*) as count
                FROM run_records 
                WHERE json_extract(workflow_state, '$.decision.decision') IS NOT NULL
                GROUP BY json_extract(workflow_state, '$.decision.decision')
            """).fetchall()
            
            # Performance metrics
            avg_execution_times = conn.execute("""
                SELECT 
                    AVG((json_extract(node_outputs, '$.validation.tool_calls[0].execution_time_ms') / 1000.0)) as validation_time,
                    AVG((json_extract(node_outputs, '$.enrichment.tool_calls[0].execution_time_ms') / 1000.0)) as enrichment_time,
                    AVG((json_extract(node_outputs, '$.assessment.tool_calls[0].execution_time_ms') / 1000.0)) as assessment_time,
                    AVG((json_extract(node_outputs, '$.rating.tool_calls[0].execution_time_ms') / 1000.0)) as rating_time
                FROM run_records 
                WHERE json_extract(node_outputs, '$.validation.tool_calls') IS NOT NULL
                LIMIT 100
            """).fetchone()
            
            # Recent runs with details
            recent_runs = conn.execute("""
                SELECT run_id, created_at, updated_at, status,
                       json_extract(workflow_state, '$.decision.decision') as decision,
                       json_extract(workflow_state, '$.premium_breakdown.total_premium') as premium
                FROM run_records 
                ORDER BY created_at DESC 
                LIMIT 10
            """).fetchall()
            
            # Error analysis
            error_runs = conn.execute("""
                SELECT run_id, error_message, created_at
                FROM run_records 
                WHERE status = 'failed' OR error_message IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 20
            """).fetchall()
            
            # Tool call statistics
            tool_stats = conn.execute("""
                WITH tool_calls AS (
                    SELECT 
                        json_extract(node_outputs, '$.validation.tool_calls') as validation_tools,
                        json_extract(node_outputs, '$.enrichment.tool_calls') as enrichment_tools,
                        json_extract(node_outputs, '$.retrieval.tool_calls') as retrieval_tools,
                        json_extract(node_outputs, '$.assessment.tool_calls') as assessment_tools,
                        json_extract(node_outputs, '$.rating.tool_calls') as rating_tools,
                        json_extract(node_outputs, '$.decision.tool_calls') as decision_tools
                    FROM run_records 
                    WHERE json_extract(node_outputs, '$.validation.tool_calls') IS NOT NULL
                )
                SELECT 
                    'validation' as tool_type, COUNT(*) as count FROM tool_calls, json_each(validation_tools)
                UNION ALL
                SELECT 
                    'enrichment' as tool_type, COUNT(*) as count FROM tool_calls, json_each(enrichment_tools)
                UNION ALL
                SELECT 
                    'retrieval' as tool_type, COUNT(*) as count FROM tool_calls, json_each(retrieval_tools)
                UNION ALL
                SELECT 
                    'assessment' as tool_type, COUNT(*) as count FROM tool_calls, json_each(assessment_tools)
                UNION ALL
                SELECT 
                    'rating' as tool_type, COUNT(*) as count FROM tool_calls, json_each(rating_tools)
                UNION ALL
                SELECT 
                    'decision' as tool_type, COUNT(*) as count FROM tool_calls, json_each(decision_tools)
            """).fetchall()
            
            return {
                "overview": {
                    "total_runs": total_runs,
                    "last_24h": last_24h,
                    "last_7d": last_7d,
                    "last_30d": last_30d,
                    "timestamp": now.isoformat()
                },
                "status_distribution": {row['status']: row['count'] for row in status_counts},
                "decision_distribution": {row['decision']: row['count'] for row in decision_counts},
                "performance": dict(avg_execution_times) if avg_execution_times else {},
                "recent_runs": [dict(row) for row in recent_runs],
                "error_analysis": [dict(row) for row in error_runs],
                "tool_statistics": {row['tool_type']: row['count'] for row in tool_stats}
            }
    
    def get_trace_data(self, run_id: str) -> Dict[str, Any]:
        """
        Get detailed trace data for a specific run.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get run record
            run_record = conn.execute("""
                SELECT * FROM run_records WHERE run_id = ?
            """, (run_id,)).fetchone()
            
            if not run_record:
                raise HTTPException(status_code=404, detail="Run not found")
            
            # Parse workflow state
            workflow_state = json.loads(run_record['workflow_state'])
            node_outputs = json.loads(run_record['node_outputs'] or '{}')
            
            # Build trace data
            trace_data = {
                "run_id": run_id,
                "status": run_record['status'],
                "created_at": run_record['created_at'],
                "updated_at": run_record['updated_at'],
                "workflow_state": workflow_state,
                "node_outputs": node_outputs,
                "timeline": self._build_timeline(node_outputs),
                "flow_diagram": self._build_flow_diagram(node_outputs)
            }
            
            return trace_data
    
    def _build_timeline(self, node_outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build execution timeline from node outputs.
        """
        timeline = []
        
        for node_name, node_data in node_outputs.items():
            tool_calls = node_data.get('tool_calls', [])
            for tool_call in tool_calls:
                timeline.append({
                    "node": node_name,
                    "tool": tool_call.get('tool_name', 'unknown'),
                    "timestamp": tool_call.get('timestamp'),
                    "execution_time_ms": tool_call.get('execution_time_ms'),
                    "status": "completed"
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x.get('timestamp', ''))
        return timeline
    
    def _build_flow_diagram(self, node_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build flow diagram data from node outputs.
        """
        nodes = []
        edges = []
        
        # Add nodes
        for node_name in node_outputs.keys():
            nodes.append({
                "id": node_name,
                "label": node_name.replace('_', ' ').title(),
                "type": "process"
            })
        
        # Add edges (simplified linear flow)
        flow_order = ["validation", "enrichment", "retrieval", "assessment", "rating", "decision"]
        for i in range(len(flow_order) - 1):
            current = flow_order[i]
            next_node = flow_order[i + 1]
            if current in node_outputs and next_node in node_outputs:
                edges.append({
                    "from": current,
                    "to": next_node,
                    "type": "success"
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }


# Initialize dashboard
dashboard = MetricsDashboard()

# HTML templates
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Agentic Quote-to-Underwrite - Metrics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h2 { margin-top: 0; color: #333; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; }
        .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; }
        .chart-container { height: 300px; margin: 20px 0; }
        .full-width { grid-column: 1 / -1; }
        .status-good { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-error { color: #e74c3c; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
    </style>
</head>
<body>
    <h1>🏛️ Agentic Quote-to-Underwrite - Metrics Dashboard</h1>
    
    <div class="dashboard">
        <!-- Overview Card -->
        <div class="card">
            <h2>📊 Overview</h2>
            <div class="metric">
                <span class="metric-label">Total Runs</span>
                <span class="metric-value" id="total-runs">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">Last 24h</span>
                <span class="metric-value" id="last-24h">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">Last 7d</span>
                <span class="metric-value" id="last-7d">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">Last 30d</span>
                <span class="metric-value" id="last-30d">-</span>
            </div>
        </div>
        
        <!-- Status Distribution Card -->
        <div class="card">
            <h2>📈 Status Distribution</h2>
            <div class="chart-container">
                <canvas id="status-chart"></canvas>
            </div>
        </div>
        
        <!-- Decision Distribution Card -->
        <div class="card">
            <h2>🎯 Decision Distribution</h2>
            <div class="chart-container">
                <canvas id="decision-chart"></canvas>
            </div>
        </div>
        
        <!-- Performance Metrics Card -->
        <div class="card">
            <h2>⚡ Performance Metrics</h2>
            <div id="performance-metrics"></div>
        </div>
        
        <!-- Recent Runs Card -->
        <div class="card full-width">
            <h2>🕐 Recent Runs</h2>
            <table id="recent-runs-table">
                <thead>
                    <tr>
                        <th>Run ID</th>
                        <th>Status</th>
                        <th>Decision</th>
                        <th>Premium</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- Error Analysis Card -->
        <div class="card full-width">
            <h2>🚨 Error Analysis</h2>
            <table id="error-table">
                <thead>
                    <tr>
                        <th>Run ID</th>
                        <th>Error Message</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Load dashboard data
        async function loadDashboardData() {
            try {
                const response = await fetch('/dashboard/data');
                const data = await response.json();
                
                updateOverview(data.overview);
                updateCharts(data.status_distribution, data.decision_distribution);
                updatePerformance(data.performance);
                updateRecentRuns(data.recent_runs);
                updateErrorAnalysis(data.error_analysis);
            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }
        
        function updateOverview(overview) {
            document.getElementById('total-runs').textContent = overview.total_runs.toLocaleString();
            document.getElementById('last-24h').textContent = overview.last_24h.toLocaleString();
            document.getElementById('last-7d').textContent = overview.last_7d.toLocaleString();
            document.getElementById('last-30d').textContent = overview.last_30d.toLocaleString();
        }
        
        function updateCharts(statusDist, decisionDist) {
            // Status chart
            new Chart(document.getElementById('status-chart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(statusDist),
                    datasets: [{
                        data: Object.values(statusDist),
                        backgroundColor: ['#27ae60', '#f39c12', '#e74c3c']
                    }]
                }
            });
            
            // Decision chart
            new Chart(document.getElementById('decision-chart'), {
                type: 'pie',
                data: {
                    labels: Object.keys(decisionDist),
                    datasets: [{
                        data: Object.values(decisionDist),
                        backgroundColor: ['#3498db', '#e74c3c', '#f39c12']
                    }]
                }
            });
        }
        
        function updatePerformance(performance) {
            const container = document.getElementById('performance-metrics');
            container.innerHTML = '';
            
            Object.entries(performance).forEach(([key, value]) => {
                if (value) {
                    const metric = document.createElement('div');
                    metric.className = 'metric';
                    metric.innerHTML = `
                        <span class="metric-label">${key.replace(/_/g, ' ').toUpperCase()}</span>
                        <span class="metric-value">${(value || 0).toFixed(2)}s</span>
                    `;
                    container.appendChild(metric);
                }
            });
        }
        
        function updateRecentRuns(runs) {
            const tbody = document.querySelector('#recent-runs-table tbody');
            tbody.innerHTML = '';
            
            runs.forEach(run => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${run.run_id.substring(0, 8)}...</td>
                    <td><span class="status-${run.status}">${run.status}</span></td>
                    <td>${run.decision || '-'}</td>
                    <td>$${run.premium || '-'}</td>
                    <td>${new Date(run.created_at).toLocaleString()}</td>
                `;
            });
        }
        
        function updateErrorAnalysis(errors) {
            const tbody = document.querySelector('#error-table tbody');
            tbody.innerHTML = '';
            
            if (errors.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3">No errors in the last 20 runs</td></tr>';
                return;
            }
            
            errors.forEach(error => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${error.run_id.substring(0, 8)}...</td>
                    <td>${error.error_message}</td>
                    <td>${new Date(error.created_at).toLocaleString()}</td>
                `;
            });
        }
        
        // Load data on page load
        loadDashboardData();
        
        // Refresh every 30 seconds
        setInterval(loadDashboardData, 30000);
    </script>
</body>
</html>
"""


def create_dashboard_routes(app: FastAPI):
    """
    Add dashboard routes to FastAPI app.
    """
    
    @app.get("/dashboard")
    async def dashboard_page():
        """Serve metrics dashboard page."""
        return HTMLResponse(content=DASHBOARD_HTML)
    
    @app.get("/dashboard/data")
    async def dashboard_data():
        """Get dashboard metrics data."""
        return dashboard.get_metrics_data()
    
    @app.get("/dashboard/trace/{run_id}")
    async def trace_viewer(run_id: str):
        """Get detailed trace data for a run."""
        try:
            trace_data = dashboard.get_trace_data(run_id)
            return HTMLResponse(content=create_trace_viewer_html(trace_data))
        except HTTPException:
            raise
        except Exception as e:
            return HTMLResponse(content=f"<h1>Error</h1><p>{str(e)}</p>", status_code=500)
    
    @app.get("/dashboard/error-analysis")
    async def error_analysis_page():
        """Get error analysis and trends."""
        try:
            analyzer = ErrorAnalyzer()
            analysis = analyzer.analyze_errors()
            trends = analyzer.get_error_trends()
            
            return HTMLResponse(content=create_error_analysis_html(analysis, trends))
        except Exception as e:
            return HTMLResponse(content=f"<h1>Error</h1><p>{str(e)}</p>", status_code=500)
    
    @app.get("/dashboard/error-analysis/data")
    async def error_analysis_data():
        """Get error analysis data."""
        analyzer = ErrorAnalyzer()
        return analyzer.analyze_errors()


def create_trace_viewer_html(trace_data: Dict[str, Any]) -> str:
    """
    Create HTML for trace viewer.
    """
    timeline = trace_data.get('timeline', [])
    flow_diagram = trace_data.get('flow_diagram', {})
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Trace Viewer - {trace_data['run_id']}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .section {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .timeline {{ max-height: 400px; overflow-y: auto; }}
        .flow-diagram {{ height: 400px; border: 1px solid #ddd; }}
        .tool-call {{ padding: 10px; margin: 5px 0; border-left: 4px solid #3498db; background: #f8f9fa; }}
        .timestamp {{ color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>🔍 Trace Viewer - {trace_data['run_id']}</h1>
    
    <div class="header">
        <h3>Run Information</h3>
        <p><strong>Status:</strong> {trace_data['status']}</p>
        <p><strong>Created:</strong> {trace_data['created_at']}</p>
        <p><strong>Updated:</strong> {trace_data['updated_at']}</p>
    </div>
    
    <div class="section">
        <h3>⏱️ Execution Timeline</h3>
        <div class="timeline">
            {"".join([f"""
            <div class="tool-call">
                <strong>{item['tool']}</strong>
                <div class="timestamp">{item['timestamp']}</div>
                <div>Execution Time: {item.get('execution_time_ms', 'N/A')}ms</div>
                <div>Node: {item['node']}</div>
            </div>
            """ for item in timeline])}
        </div>
    </div>
    
    <div class="section">
        <h3>🔄 Flow Diagram</h3>
        <div id="flow-diagram" class="flow-diagram"></div>
    </div>
    
    <script>
        // Create flow diagram
        const nodes = new vis.DataSet([
            {', '.join([f'{{id: "{node["id"]}", label: "{node["label"]}"}}' for node in flow_diagram.get('nodes', [])])}
        ]);
        
        const edges = new vis.DataSet([
            {', '.join([f'{{from: "{edge["from"]}", to: "{edge["to"]}"}}' for edge in flow_diagram.get('edges', [])])}
        ]);
        
        const container = document.getElementById('flow-diagram');
        new vis.Network(container, {{nodes, edges}}, {{
            layout: {{
                hierarchical: {{
                    direction: 'UD'
                }}
            }}
        }});
    </script>
</body>
</html>
    """


def create_error_analysis_html(analysis, trends) -> str:
    """
    Create HTML for error analysis page.
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Error Analysis Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .dashboard {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h2 {{ margin-top: 0; color: #333; }}
        .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; }}
        .chart-container {{ height: 300px; margin: 20px 0; }}
        .full-width {{ grid-column: 1 / -1; }}
        .status-critical {{ color: #e74c3c; }}
        .status-high {{ color: #f39c12; }}
        .status-medium {{ color: #f59e0b; }}
        .status-low {{ color: #27ae60; }}
        .suggestion {{ background: #fff3cd; border-left: 4px solid #856404; padding: 10px; margin: 5px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <h1>🚨 Error Analysis Dashboard</h1>
    
    <div class="dashboard">
        <!-- Overview Card -->
        <div class="card">
            <h2>📊 Error Overview</h2>
            <div class="metric">
                <span class="metric-label">Total Errors</span>
                <span class="metric-value">{analysis.total_errors}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Auto-fixes Applied</span>
                <span class="metric-value">{analysis.auto_fixes_applied}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Analysis Time</span>
                <span class="metric-value">{analysis.timestamp}</span>
            </div>
        </div>
        
        <!-- Severity Distribution Card -->
        <div class="card">
            <h2>🎯 Severity Distribution</h2>
            <div class="chart-container">
                <canvas id="severity-chart"></canvas>
            </div>
        </div>
        
        <!-- Category Distribution Card -->
        <div class="card">
            <h2>📂 Category Distribution</h2>
            <div class="chart-container">
                <canvas id="category-chart"></canvas>
            </div>
        </div>
        
        <!-- Error Patterns Card -->
        <div class="card">
            <h2>🔍 Error Patterns</h2>
            <table>
                <thead>
                    <tr>
                        <th>Pattern</th>
                        <th>Count</th>
                        <th>Severity</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"""
                    <tr>
                        <td>{pattern_id}</td>
                        <td>{count}</td>
                        <td><span class="status-{severity.lower()}">{severity}</span></td>
                    </tr>
                    """ for pattern_id, count in analysis.error_patterns.items()])}
                </tbody>
            </table>
        </div>
        
        <!-- Improvement Suggestions Card -->
        <div class="card full-width">
            <h2>💡 Improvement Suggestions</h2>
            {"".join([f'<div class="suggestion">{suggestion}</div>' for suggestion in analysis.improvement_suggestions])}
        </div>
        
        <!-- Recent Errors Card -->
        <div class="card full-width">
            <h2>🕐 Recent Errors</h2>
            <table>
                <thead>
                    <tr>
                        <th>Run ID</th>
                        <th>Error Message</th>
                        <th>Timestamp</th>
                        <th>Pattern</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"""
                    <tr>
                        <td>{error['run_id'][:8]}...</td>
                        <td>{error['error_message'][:100]}...</td>
                        <td>{error['timestamp']}</td>
                        <td>{error['pattern_id']}</td>
                    </tr>
                    """ for error in analysis.recent_errors[:10]])}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Severity distribution chart
        new Chart(document.getElementById('severity-chart'), {{
            type: 'doughnut',
            data: {{
                labels: {list(analysis.severity_distribution.keys())},
                datasets: [{{
                    data: {list(analysis.severity_distribution.values())},
                    backgroundColor: ['#e74c3c', '#f39c12', '#f59e0b', '#27ae60']
                }}]
            }}
        }});
        
        // Category distribution chart
        new Chart(document.getElementById('category-chart'), {{
            type: 'pie',
            data: {{
                labels: {list(analysis.category_distribution.keys())},
                datasets: [{{
                    data: {list(analysis.category_distribution.values())},
                    backgroundColor: ['#3498db', '#e74c3c', '#f39c12', '#f59e0b', '#27ae60']
                }}]
            }}
        }});
    </script>
</body>
</html>
    """
