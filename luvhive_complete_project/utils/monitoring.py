# utils/monitoring.py - Comprehensive monitoring and alerting system
import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import threading
import psutil

log = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and tracks application metrics for monitoring."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.timers = defaultdict(deque)  # Store last 100 measurements
        self.alerts = []
        self.alert_cooldowns = {}  # Prevent spam alerts
        self._lock = threading.Lock()
        
        # Performance thresholds (from ChatGPT recommendations)
        self.thresholds = {
            "floodwait_per_minute": 5,      # TG FloodWait spikes
            "error_rate_percent": 1.0,       # Handler error rate > 1%
            "db_latency_p95_ms": 200,       # DB p95 latency > 200ms
            "queue_depth": 100,             # Queue depth > 100
            "cpu_percent": 80,              # CPU > 80%
            "memory_percent": 85,           # RAM > 85%
            "webhook_5xx_rate": 0.5         # Webhook 5xx rate > 0.5%
        }
        
        # Start background monitoring
        self._start_monitoring_thread()
    
    def increment(self, metric_name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        with self._lock:
            key = f"{metric_name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.counters[key] += value
    
    def gauge(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value."""
        with self._lock:
            key = f"{metric_name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.gauges[key] = value
    
    def timer(self, metric_name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timing metric."""
        with self._lock:
            key = f"{metric_name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.timers[key].append((time.time(), duration_ms))
            
            # Keep only last 100 measurements
            if len(self.timers[key]) > 100:
                self.timers[key].popleft()
    
    def record_error(self, error_type: str, error_message: str, handler: str = None):
        """Record error for monitoring."""
        self.increment("errors_total", tags={
            "error_type": error_type,
            "handler": handler or "unknown"
        })
        
        with self._lock:
            self.metrics["errors"].append({
                "timestamp": time.time(),
                "error_type": error_type,
                "error_message": error_message,
                "handler": handler
            })
    
    def record_floodwait(self, delay_seconds: int, user_id: int = None):
        """Record Telegram FloodWait event."""
        self.increment("floodwait_total", tags={
            "delay_seconds": str(delay_seconds)
        })
        
        with self._lock:
            self.metrics["floodwaits"].append({
                "timestamp": time.time(),
                "delay_seconds": delay_seconds,
                "user_id": user_id
            })
    
    def record_db_query(self, duration_ms: float, query_type: str, success: bool = True):
        """Record database query metrics."""
        self.timer("db_query_duration_ms", duration_ms, tags={
            "query_type": query_type,
            "success": str(success)
        })
        
        if not success:
            self.increment("db_errors_total", tags={"query_type": query_type})
    
    def record_webhook_response(self, status_code: int, duration_ms: float):
        """Record webhook response metrics."""
        self.timer("webhook_duration_ms", duration_ms)
        self.increment("webhook_responses_total", tags={
            "status_code": str(status_code),
            "status_class": f"{status_code // 100}xx"
        })
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        with self._lock:
            now = time.time()
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "alerts_active": len([a for a in self.alerts if a.get("resolved", False) == False]),
                "system": {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage("/").percent
                }
            }
            
            # Calculate timer percentiles
            timer_stats = {}
            for key, measurements in self.timers.items():
                if measurements:
                    recent_values = [m[1] for m in measurements if now - m[0] < 300]  # Last 5 min
                    if recent_values:
                        recent_values.sort()
                        timer_stats[key] = {
                            "count": len(recent_values),
                            "avg": sum(recent_values) / len(recent_values),
                            "p95": recent_values[int(0.95 * len(recent_values))] if recent_values else 0,
                            "p99": recent_values[int(0.99 * len(recent_values))] if recent_values else 0
                        }
            
            summary["timers"] = timer_stats
            return summary
    
    def check_alerts(self):
        """Check metrics against thresholds and generate alerts."""
        now = time.time()
        
        try:
            # Check FloodWait rate (per minute)
            floodwait_count = len([
                m for m in self.metrics["floodwaits"] 
                if now - m["timestamp"] < 60
            ])
            
            if floodwait_count > self.thresholds["floodwait_per_minute"]:
                self._create_alert(
                    "high_floodwait_rate",
                    f"FloodWait rate: {floodwait_count}/min > {self.thresholds['floodwait_per_minute']}/min",
                    "critical"
                )
            
            # Check error rate (last 5 minutes)
            error_count = len([
                m for m in self.metrics["errors"]
                if now - m["timestamp"] < 300
            ])
            
            total_requests = sum([
                v for k, v in self.counters.items() 
                if "requests_total" in k
            ]) or 1
            
            error_rate = (error_count / total_requests) * 100
            if error_rate > self.thresholds["error_rate_percent"]:
                self._create_alert(
                    "high_error_rate", 
                    f"Error rate: {error_rate:.1f}% > {self.thresholds['error_rate_percent']}%",
                    "warning"
                )
            
            # Check database latency (p95)
            db_query_key = next((k for k in self.timers.keys() if "db_query_duration_ms" in k), None)
            if db_query_key:
                recent_queries = [
                    m[1] for m in self.timers[db_query_key] 
                    if now - m[0] < 300
                ]
                if recent_queries:
                    recent_queries.sort()
                    p95_latency = recent_queries[int(0.95 * len(recent_queries))]
                    
                    if p95_latency > self.thresholds["db_latency_p95_ms"]:
                        self._create_alert(
                            "high_db_latency",
                            f"DB p95 latency: {p95_latency:.1f}ms > {self.thresholds['db_latency_p95_ms']}ms",
                            "warning"
                        )
            
            # Check system resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > self.thresholds["cpu_percent"]:
                self._create_alert(
                    "high_cpu_usage",
                    f"CPU usage: {cpu_percent:.1f}% > {self.thresholds['cpu_percent']}%",
                    "warning"
                )
            
            if memory_percent > self.thresholds["memory_percent"]:
                self._create_alert(
                    "high_memory_usage", 
                    f"Memory usage: {memory_percent:.1f}% > {self.thresholds['memory_percent']}%",
                    "critical"
                )
                
        except Exception as e:
            log.error(f"Alert checking failed: {e}")
    
    def _create_alert(self, alert_type: str, message: str, severity: str):
        """Create alert with cooldown to prevent spam."""
        cooldown_key = f"{alert_type}:{severity}"
        now = time.time()
        
        # Check cooldown (5 minutes)
        if cooldown_key in self.alert_cooldowns:
            if now - self.alert_cooldowns[cooldown_key] < 300:
                return
        
        alert = {
            "id": f"{alert_type}_{int(now)}",
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": now,
            "resolved": False
        }
        
        self.alerts.append(alert)
        self.alert_cooldowns[cooldown_key] = now
        
        log.warning(f"🚨 ALERT [{severity.upper()}]: {message}")
        
        # TODO: Send to external monitoring (Sentry, Slack, etc.)
        self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: Dict[str, Any]):
        """Send alert notification (extend this for your notification system)."""
        try:
            # Log alert to file for now
            alert_log_file = "/tmp/luvhive_alerts.log"
            with open(alert_log_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} [{alert['severity'].upper()}] {alert['message']}\n")
            
            # TODO: Add webhook/email/Slack notifications here
            
        except Exception as e:
            log.error(f"Failed to send alert notification: {e}")
    
    def _start_monitoring_thread(self):
        """Start background thread for periodic monitoring."""
        def monitor_loop():
            while True:
                try:
                    time.sleep(60)  # Check every minute
                    self.check_alerts()
                    
                    # Clean old metrics (keep last hour)
                    self._cleanup_old_metrics()
                    
                except Exception as e:
                    log.error(f"Monitoring loop error: {e}")
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def _cleanup_old_metrics(self):
        """Clean up old metric data to prevent memory bloat."""
        cutoff_time = time.time() - 3600  # 1 hour ago
        
        with self._lock:
            for metric_type in self.metrics:
                self.metrics[metric_type] = [
                    m for m in self.metrics[metric_type]
                    if m["timestamp"] > cutoff_time
                ]

# Global metrics instance
metrics = MetricsCollector()

# Decorator for automatic timing
def time_function(metric_name: str, tags: Dict[str, str] = None):
    """Decorator to automatically time function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                metrics.timer(metric_name, duration_ms, tags)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metrics.timer(metric_name, duration_ms, {**(tags or {}), "success": "false"})
                metrics.record_error(type(e).__name__, str(e), func.__name__)
                raise
        return wrapper
    return decorator

# Context manager for database query timing
class DatabaseQueryTimer:
    def __init__(self, query_type: str):
        self.query_type = query_type
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        success = exc_type is None
        metrics.record_db_query(duration_ms, self.query_type, success)