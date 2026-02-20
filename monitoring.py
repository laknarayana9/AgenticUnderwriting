"""
Monitoring, logging, and alerting system for production deployment.
"""

import logging
import json
import asyncio
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from fastapi import Request
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
except ImportError:
    MimeText = None
    MimeMultipart = None
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import psutil
import sys
import traceback


# Prometheus metrics - avoid duplication
try:
    REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
    ACTIVE_WORKFLOWS = Gauge('active_workflows', 'Number of active workflows')
    DATABASE_CONNECTIONS = Gauge('database_connections', 'Active database connections')
    CACHE_HIT_RATE = Gauge('cache_hit_rate', 'Cache hit rate percentage')
    ERROR_COUNT = Counter('errors_total', 'Total errors', ['error_type', 'component'])
except Exception as e:
    print(f"Warning: Prometheus metrics initialization failed: {e}")
    # Fallback dummy metrics
    REQUEST_COUNT = None
    REQUEST_DURATION = None
    ACTIVE_WORKFLOWS = None
    DATABASE_CONNECTIONS = None
    CACHE_HIT_RATE = None
    ERROR_COUNT = None


class StructuredLogger:
    """Structured JSON logging for production."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove default handlers
        self.logger.handlers.clear()
        
        # Create structured formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if configured)
        try:
            from config import settings
            if hasattr(settings, 'log_file_path'):
                file_handler = logging.FileHandler(settings.log_file_path)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
        except:
            pass
    
    def log_structured(self, level: str, message: str, **kwargs):
        """Log structured message with additional context."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        
        getattr(self.logger, level.lower())(json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        self.log_structured("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log_structured("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log_structured("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log_structured("CRITICAL", message, **kwargs)


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self):
        self.checks = {}
        self.logger = StructuredLogger("health_checker")
    
    def register_check(self, name: str, check_func: Callable[[], Dict[str, Any]], 
                    interval: int = 60):
        """Register a health check."""
        self.checks[name] = {
            "func": check_func,
            "interval": interval,
            "last_check": None,
            "status": "unknown"
        }
    
    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        if name not in self.checks:
            return {"status": "error", "message": f"Check {name} not found"}
        
        check = self.checks[name]
        now = datetime.now()
        
        # Skip if recently checked
        if (check["last_check"] and 
            (now - check["last_check"]).seconds < check["interval"]):
            return {"status": check["status"]}
        
        try:
            result = await check["func"]()
            check["last_check"] = now
            check["status"] = result.get("status", "unknown")
            return result
        except Exception as e:
            self.logger.error(f"Health check {name} failed", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_status = "healthy"
        
        for name in self.checks:
            result = await self.run_check(name)
            results[name] = result
            
            if result.get("status") == "error":
                overall_status = "unhealthy"
            elif result.get("status") == "warning" and overall_status == "healthy":
                overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }


class AlertManager:
    """Alert management and notification system."""
    
    def __init__(self):
        self.alert_rules = []
        self.alert_history = []
        self.logger = StructuredLogger("alert_manager")
        self.email_config = {}
    
    def configure_email(self, smtp_host: str, smtp_port: int, 
                     smtp_user: str, smtp_password: str):
        """Configure email alerts."""
        self.email_config = {
            "host": smtp_host,
            "port": smtp_port,
            "user": smtp_user,
            "password": smtp_password
        }
    
    def add_rule(self, name: str, condition: Callable[[], bool], 
                severity: str, message: str, cooldown: int = 300):
        """Add alert rule."""
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "message": message,
            "cooldown": cooldown,
            "last_triggered": None
        })
    
    async def check_rules(self):
        """Check all alert rules."""
        for rule in self.alert_rules:
            try:
                if rule["condition"]():
                    await self.trigger_alert(rule)
            except Exception as e:
                self.logger.error(f"Alert rule {rule['name']} check failed", 
                               error=str(e))
    
    async def trigger_alert(self, rule: Dict[str, Any]):
        """Trigger an alert."""
        now = datetime.now()
        
        # Check cooldown
        if (rule["last_triggered"] and 
            (now - rule["last_triggered"]).seconds < rule["cooldown"]):
            return
        
        rule["last_triggered"] = now
        
        alert = {
            "name": rule["name"],
            "severity": rule["severity"],
            "message": rule["message"],
            "timestamp": now.isoformat()
        }
        
        self.alert_history.append(alert)
        self.logger.warning(f"Alert triggered: {rule['name']}", 
                          severity=rule["severity"], message=rule["message"])
        
        # Send email notification
        if self.email_config:
            await self.send_email_alert(alert)
    
    async def send_email_alert(self, alert: Dict[str, Any]):
        """Send email alert."""
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config["user"]
            msg['To'] = self.email_config["user"]  # Send to self for now
            msg['Subject'] = f"Alert: {alert['name']} ({alert['severity']})"
            
            body = f"""
            Alert: {alert['name']}
            Severity: {alert['severity']}
            Time: {alert['timestamp']}
            Message: {alert['message']}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config["host"], self.email_config["port"])
            server.starttls()
            server.login(self.email_config["user"], self.email_config["password"])
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            self.logger.error("Failed to send email alert", error=str(e))


class MetricsCollector:
    """Collect system and application metrics."""
    
    def __init__(self):
        self.logger = StructuredLogger("metrics")
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            network = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
        except Exception as e:
            self.logger.error("Failed to collect system metrics", error=str(e))
            return {}
    
    async def collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-specific metrics."""
        try:
            # Get database stats
            from storage.database import db
            db_stats = db.get_statistics()
            
            # Get cache stats
            cache_stats = {}
            try:
                from performance import cache_manager
                if cache_manager and cache_manager.redis:
                    info = cache_manager.redis.info()
                    cache_stats = {
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory": info.get("used_memory", 0),
                        "keyspace_hits": info.get("keyspace_hits", 0),
                        "keyspace_misses": info.get("keyspace_misses", 0)
                    }
            except:
                pass
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "database": db_stats,
                "cache": cache_stats,
                "active_workflows": ACTIVE_WORKFLOWS._value.get(),
                "database_connections": DATABASE_CONNECTIONS._value.get()
            }
        except Exception as e:
            self.logger.error("Failed to collect application metrics", error=str(e))
            return {}


# Global instances
logger = StructuredLogger("monitoring")
health_checker = HealthChecker()
alert_manager = AlertManager()
metrics_collector = MetricsCollector()


def setup_monitoring():
    """Setup monitoring system."""
    
    # Register health checks
    health_checker.register_check("database", check_database_health)
    health_checker.register_check("redis", check_redis_health)
    health_checker.register_check("disk_space", check_disk_space)
    health_checker.register_check("memory", check_memory_usage)
    
    # Register alert rules
    alert_manager.add_rule(
        "high_error_rate",
        lambda: ERROR_COUNT._value.get() > 10,  # More than 10 errors in last minute
        "critical",
        "High error rate detected"
    )
    
    alert_manager.add_rule(
        "high_memory_usage",
        lambda: psutil.virtual_memory().percent > 90,
        "warning",
        "High memory usage"
    )
    
    alert_manager.add_rule(
        "low_disk_space",
        lambda: psutil.disk_usage('/').percent > 85,
        "critical",
        "Low disk space"
    )


async def check_database_health() -> Dict[str, Any]:
    """Check database health."""
    try:
        from storage.database import db
        stats = db.get_statistics()
        return {"status": "healthy", "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis health."""
    try:
        from performance import cache_manager
        if cache_manager and cache_manager.redis:
            cache_manager.redis.ping()
            return {"status": "healthy"}
        else:
            return {"status": "warning", "message": "Redis not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def check_disk_space() -> Dict[str, Any]:
    """Check disk space."""
    try:
        disk = psutil.disk_usage('/')
        percent_used = (disk.used / disk.total) * 100
        
        if percent_used > 90:
            return {"status": "error", "percent": percent_used}
        elif percent_used > 80:
            return {"status": "warning", "percent": percent_used}
        else:
            return {"status": "healthy", "percent": percent_used}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def check_memory_usage() -> Dict[str, Any]:
    """Check memory usage."""
    try:
        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            return {"status": "error", "percent": memory.percent}
        elif memory.percent > 80:
            return {"status": "warning", "percent": memory.percent}
        else:
            return {"status": "healthy", "percent": memory.percent}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def monitoring_loop():
    """Background monitoring loop."""
    while True:
        try:
            # Check health
            health_status = await health_checker.run_all_checks()
            logger.info("Health check completed", status=health_status["status"])
            
            # Check alerts
            await alert_manager.check_rules()
            
            # Collect metrics
            system_metrics = await metrics_collector.collect_system_metrics()
            app_metrics = await metrics_collector.collect_application_metrics()
            
            logger.info("Metrics collected", 
                       system=system_metrics, 
                       application=app_metrics)
            
            # Wait before next check
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error("Monitoring loop error", error=str(e))
            await asyncio.sleep(60)


# Middleware for FastAPI
async def monitoring_middleware(request, call_next):
    """Middleware to monitor requests."""
    start_time = datetime.now()
    
    try:
        response = await call_next(request)
        
        # Record metrics only if available
        if REQUEST_COUNT is not None:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            duration = (datetime.now() - start_time).total_seconds()
            if REQUEST_DURATION is not None:
                REQUEST_DURATION.observe(duration)
        
        # Log request only if logger is available
        try:
            logger.info("HTTP request", 
                       method=request.method,
                       path=request.url.path,
                       status=response.status_code,
                       duration=duration)
        except:
            pass  # Skip logging if logger not available
        
        return response
        
    except Exception as e:
        # Record error only if metrics available
        if ERROR_COUNT is not None:
            ERROR_COUNT.labels(error_type=type(e).__name__, component="api").inc()
        
        try:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error("Request error", 
                        method=request.method,
                        path=request.url.path,
                        error=str(e),
                        traceback=str(e.__traceback__))
            if REQUEST_DURATION is not None:
                REQUEST_DURATION.observe(duration)
        except:
            pass  # Skip logging if logger not available
        
        raise


# Prometheus metrics endpoint
def metrics_endpoint():
    """Prometheus metrics endpoint."""
    if REQUEST_COUNT is None:
        return {"error": "Prometheus metrics not available"}
    return generate_latest()


# Health check endpoint
async def health_endpoint(request: Request = None):
    """Health check endpoint."""
    if health_checker is None:
        return {"status": "degraded", "message": "Health checker not initialized"}
    
    health_status = await health_checker.run_all_checks()
    
    if health_status["status"] == "healthy":
        return health_status
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=health_status)
