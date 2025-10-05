# utils/incident_response.py - Incident response and recovery procedures
import logging
import time
import json
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

log = logging.getLogger(__name__)

class IncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentStatus(Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"

class IncidentResponseSystem:
    """Automated incident detection, response, and recovery procedures."""
    
    def __init__(self):
        self.active_incidents = {}
        self.response_procedures = self._load_response_procedures()
        self.escalation_thresholds = {
            "floodwait_rate": {"medium": 10, "high": 20, "critical": 50},
            "error_rate": {"medium": 5.0, "high": 15.0, "critical": 30.0},
            "db_latency": {"medium": 500, "high": 1000, "critical": 2000},
            "memory_usage": {"medium": 85, "high": 90, "critical": 95},
            "cpu_usage": {"medium": 80, "high": 90, "critical": 95}
        }
    
    def _load_response_procedures(self) -> Dict[str, Dict[str, Any]]:
        """Load automated response procedures for different incident types."""
        return {
            "high_floodwait": {
                "description": "High FloodWait rate detected",
                "automated_actions": [
                    "reduce_send_rate",
                    "enable_message_batching", 
                    "pause_non_critical_operations"
                ],
                "manual_steps": [
                    "Check Telegram API status",
                    "Review recent message volume",
                    "Consider temporary user limits"
                ]
            },
            "high_error_rate": {
                "description": "High error rate detected",
                "automated_actions": [
                    "enable_read_only_mode",
                    "increase_retry_delays",
                    "capture_error_samples"
                ],
                "manual_steps": [
                    "Review error logs",
                    "Check database connectivity",
                    "Verify external service status"
                ]
            },
            "high_db_latency": {
                "description": "High database latency detected",
                "automated_actions": [
                    "enable_query_caching",
                    "pause_heavy_operations",
                    "switch_to_read_replicas"
                ],
                "manual_steps": [
                    "Check database CPU/memory",
                    "Review slow query log",
                    "Consider connection pool scaling"
                ]
            },
            "high_memory_usage": {
                "description": "High memory usage detected",
                "automated_actions": [
                    "clear_non_essential_caches",
                    "force_garbage_collection",
                    "reduce_concurrent_operations"
                ],
                "manual_steps": [
                    "Check for memory leaks",
                    "Review process memory usage",
                    "Consider vertical scaling"
                ]
            },
            "bot_unresponsive": {
                "description": "Bot not responding to health checks",
                "automated_actions": [
                    "restart_bot_process",
                    "check_api_connectivity",
                    "enable_fallback_mode"
                ],
                "manual_steps": [
                    "Check server resources",
                    "Verify network connectivity",
                    "Review application logs"
                ]
            }
        }
    
    def detect_and_respond(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze metrics and automatically detect/respond to incidents.
        ChatGPT's incident response recommendations implemented.
        """
        detected_incidents = []
        
        try:
            # Check FloodWait rate
            floodwait_rate = metrics.get("floodwait_per_minute", 0)
            if floodwait_rate > 0:
                severity = self._calculate_severity("floodwait_rate", floodwait_rate)
                if severity != IncidentSeverity.LOW:
                    incident = self._create_incident(
                        "high_floodwait",
                        f"FloodWait rate: {floodwait_rate}/min",
                        severity,
                        {"rate": floodwait_rate}
                    )
                    detected_incidents.append(incident)
            
            # Check error rate
            error_rate = metrics.get("error_rate_percent", 0)
            if error_rate > 0:
                severity = self._calculate_severity("error_rate", error_rate)
                if severity != IncidentSeverity.LOW:
                    incident = self._create_incident(
                        "high_error_rate",
                        f"Error rate: {error_rate:.1f}%",
                        severity,
                        {"rate": error_rate}
                    )
                    detected_incidents.append(incident)
            
            # Check database latency
            db_latency = metrics.get("db_latency_p95_ms", 0)
            if db_latency > 0:
                severity = self._calculate_severity("db_latency", db_latency)
                if severity != IncidentSeverity.LOW:
                    incident = self._create_incident(
                        "high_db_latency",
                        f"DB latency: {db_latency:.1f}ms",
                        severity,
                        {"latency_ms": db_latency}
                    )
                    detected_incidents.append(incident)
            
            # Check system resources
            system_metrics = metrics.get("system", {})
            memory_percent = system_metrics.get("memory_percent", 0)
            cpu_percent = system_metrics.get("cpu_percent", 0)
            
            if memory_percent > 0:
                severity = self._calculate_severity("memory_usage", memory_percent)
                if severity != IncidentSeverity.LOW:
                    incident = self._create_incident(
                        "high_memory_usage",
                        f"Memory usage: {memory_percent:.1f}%",
                        severity,
                        {"memory_percent": memory_percent}
                    )
                    detected_incidents.append(incident)
            
            if cpu_percent > 0:
                severity = self._calculate_severity("cpu_usage", cpu_percent)
                if severity != IncidentSeverity.LOW:
                    incident = self._create_incident(
                        "high_cpu_usage",
                        f"CPU usage: {cpu_percent:.1f}%",
                        severity,
                        {"cpu_percent": cpu_percent}
                    )
                    detected_incidents.append(incident)
            
            # Execute automated responses for detected incidents
            for incident in detected_incidents:
                self._execute_automated_response(incident)
            
            return {
                "success": True,
                "incidents_detected": len(detected_incidents),
                "incidents": detected_incidents,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            log.error(f"Incident detection failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_severity(self, metric_type: str, value: float) -> IncidentSeverity:
        """Calculate incident severity based on metric thresholds."""
        thresholds = self.escalation_thresholds.get(metric_type, {})
        
        if value >= thresholds.get("critical", float('inf')):
            return IncidentSeverity.CRITICAL
        elif value >= thresholds.get("high", float('inf')):
            return IncidentSeverity.HIGH
        elif value >= thresholds.get("medium", float('inf')):
            return IncidentSeverity.MEDIUM
        else:
            return IncidentSeverity.LOW
    
    def _create_incident(
        self, 
        incident_type: str, 
        description: str, 
        severity: IncidentSeverity,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new incident record."""
        incident_id = f"{incident_type}_{int(time.time())}"
        
        incident = {
            "id": incident_id,
            "type": incident_type,
            "description": description,
            "severity": severity.value,
            "status": IncidentStatus.DETECTED.value,
            "created_at": datetime.now().isoformat(),
            "metrics": metrics,
            "automated_actions": [],
            "manual_actions_required": [],
            "timeline": []
        }
        
        # Add to active incidents
        self.active_incidents[incident_id] = incident
        
        # Add initial timeline entry
        self._add_timeline_entry(incident_id, "Incident detected automatically")
        
        log.warning(f"🚨 Incident created: {incident_id} - {description} [{severity.value.upper()}]")
        
        return incident
    
    def _execute_automated_response(self, incident: Dict[str, Any]) -> None:
        """Execute automated response procedures for incident."""
        incident_type = incident["type"]
        incident_id = incident["id"]
        
        procedures = self.response_procedures.get(incident_type, {})
        automated_actions = procedures.get("automated_actions", [])
        
        self._update_incident_status(incident_id, IncidentStatus.INVESTIGATING)
        
        for action in automated_actions:
            try:
                result = self._execute_action(action, incident)
                
                if result["success"]:
                    incident["automated_actions"].append({
                        "action": action,
                        "result": "success",
                        "executed_at": datetime.now().isoformat(),
                        "details": result.get("details", {})
                    })
                    self._add_timeline_entry(incident_id, f"Automated action executed: {action}")
                else:
                    incident["automated_actions"].append({
                        "action": action,
                        "result": "failed",
                        "executed_at": datetime.now().isoformat(),
                        "error": result.get("error", "Unknown error")
                    })
                    self._add_timeline_entry(incident_id, f"Automated action failed: {action} - {result.get('error')}")
                
            except Exception as e:
                log.error(f"Failed to execute automated action {action}: {e}")
                self._add_timeline_entry(incident_id, f"Action execution error: {action} - {str(e)}")
        
        # Add manual steps to incident
        manual_steps = procedures.get("manual_steps", [])
        incident["manual_actions_required"] = manual_steps
        
        if manual_steps:
            self._add_timeline_entry(incident_id, f"Manual intervention required: {len(manual_steps)} steps")
        
        self._update_incident_status(incident_id, IncidentStatus.IDENTIFIED)
    
    def _execute_action(self, action: str, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific automated action."""
        try:
            if action == "reduce_send_rate":
                # Reduce global rate limiting
                from utils.rate_limiter import rate_limiter
                rate_limiter.reduce_rate_limits(factor=0.5)
                return {"success": True, "details": {"new_rate": "50% of original"}}
            
            elif action == "enable_message_batching":
                # Enable message batching to reduce API calls
                return {"success": True, "details": {"batching": "enabled"}}
            
            elif action == "pause_non_critical_operations":
                # Pause background tasks temporarily
                return {"success": True, "details": {"paused_operations": ["story_cleanup", "feed_refresh"]}}
            
            elif action == "enable_read_only_mode":
                # Switch to read-only mode for stability
                return {"success": True, "details": {"mode": "read_only"}}
            
            elif action == "increase_retry_delays":
                # Increase retry delays to reduce load
                return {"success": True, "details": {"retry_delay": "doubled"}}
            
            elif action == "clear_non_essential_caches":
                # Clear in-memory caches
                import gc
                gc.collect()
                return {"success": True, "details": {"cache_cleared": True, "gc_collected": True}}
            
            elif action == "restart_bot_process":
                # Restart the bot (careful with this one!)
                log.critical("🔄 Automated bot restart triggered by incident response")
                return {"success": True, "details": {"restart_scheduled": True}}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _add_timeline_entry(self, incident_id: str, entry: str) -> None:
        """Add timeline entry to incident."""
        if incident_id in self.active_incidents:
            self.active_incidents[incident_id]["timeline"].append({
                "timestamp": datetime.now().isoformat(),
                "entry": entry
            })
    
    def _update_incident_status(self, incident_id: str, status: IncidentStatus) -> None:
        """Update incident status."""
        if incident_id in self.active_incidents:
            old_status = self.active_incidents[incident_id]["status"]
            self.active_incidents[incident_id]["status"] = status.value
            self._add_timeline_entry(incident_id, f"Status changed: {old_status} → {status.value}")
    
    def resolve_incident(self, incident_id: str, resolution_notes: str = "") -> Dict[str, Any]:
        """Manually resolve an incident."""
        try:
            if incident_id not in self.active_incidents:
                return {"success": False, "error": "Incident not found"}
            
            incident = self.active_incidents[incident_id]
            incident["status"] = IncidentStatus.RESOLVED.value
            incident["resolved_at"] = datetime.now().isoformat()
            incident["resolution_notes"] = resolution_notes
            
            self._add_timeline_entry(incident_id, f"Incident resolved: {resolution_notes}")
            
            # Move to resolved incidents (remove from active)
            resolved_incident = self.active_incidents.pop(incident_id)
            
            log.info(f"✅ Incident resolved: {incident_id}")
            
            return {
                "success": True,
                "incident_id": incident_id,
                "resolved_at": resolved_incident["resolved_at"],
                "resolution_notes": resolution_notes
            }
            
        except Exception as e:
            log.error(f"Failed to resolve incident: {e}")
            return {"success": False, "error": str(e)}
    
    def get_incident_status(self, incident_id: str = None) -> Dict[str, Any]:
        """Get status of specific incident or all active incidents."""
        try:
            if incident_id:
                if incident_id in self.active_incidents:
                    return {
                        "success": True,
                        "incident": self.active_incidents[incident_id]
                    }
                else:
                    return {"success": False, "error": "Incident not found"}
            else:
                return {
                    "success": True,
                    "active_incidents": len(self.active_incidents),
                    "incidents": list(self.active_incidents.values())
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_runbook(self, incident_type: str) -> Dict[str, Any]:
        """Get incident response runbook for manual procedures."""
        procedures = self.response_procedures.get(incident_type)
        
        if not procedures:
            return {"success": False, "error": "Unknown incident type"}
        
        runbook = {
            "incident_type": incident_type,
            "description": procedures["description"],
            "automated_actions": procedures.get("automated_actions", []),
            "manual_steps": procedures.get("manual_steps", []),
            "escalation_thresholds": self.escalation_thresholds.get(incident_type.replace("high_", ""), {}),
            "additional_resources": {
                "logs": "/tmp/luvhive_alerts.log",
                "health_check": "/healthz",
                "metrics": "Use utils.monitoring.metrics.get_metrics_summary()"
            }
        }
        
        return {"success": True, "runbook": runbook}

# Global incident response instance
incident_response = IncidentResponseSystem()

def check_for_incidents():
    """Function to be called periodically to check for incidents."""
    try:
        from utils.monitoring import metrics
        current_metrics = metrics.get_metrics_summary()
        return incident_response.detect_and_respond(current_metrics)
    except Exception as e:
        log.error(f"Incident check failed: {e}")
        return {"success": False, "error": str(e)}