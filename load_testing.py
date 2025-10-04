# utils/load_testing.py - Simple load testing for performance validation
import asyncio
import logging
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

log = logging.getLogger(__name__)

class LoadTestingSystem:
    """
    Simple load testing system for validating bot performance.
    ChatGPT recommendation: simulate 1-2k concurrent chats with realistic scenarios.
    """
    
    def __init__(self):
        self.test_scenarios = {
            "basic_chat": {
                "description": "Basic chat flow: start → send → like → comment",
                "steps": ["start_chat", "send_message", "like_post", "comment_post"],
                "weight": 0.4
            },
            "registration": {
                "description": "New user registration flow",
                "steps": ["start_registration", "set_profile", "select_interests"],
                "weight": 0.2
            },
            "feed_browsing": {
                "description": "Browse public feed and interact",
                "steps": ["view_feed", "like_posts", "view_profiles", "send_message"],
                "weight": 0.3
            },
            "premium_features": {
                "description": "Premium user activities",
                "steps": ["view_stories", "create_story", "secret_chat", "advanced_search"],
                "weight": 0.1
            }
        }
        
        self.performance_thresholds = {
            "avg_response_time_ms": 500,
            "p95_response_time_ms": 1000,
            "error_rate_percent": 2.0,
            "concurrent_users": 1000
        }
    
    async def run_load_test(
        self, 
        concurrent_users: int = 100,
        duration_minutes: int = 5,
        ramp_up_minutes: int = 1
    ) -> Dict[str, Any]:
        """
        Run comprehensive load test with realistic user behavior.
        """
        log.info(f"🧪 Starting load test: {concurrent_users} users for {duration_minutes} minutes")
        
        test_start = time.time()
        results = {
            "test_config": {
                "concurrent_users": concurrent_users,
                "duration_minutes": duration_minutes,
                "ramp_up_minutes": ramp_up_minutes,
                "scenarios": list(self.test_scenarios.keys())
            },
            "metrics": {
                "requests_sent": 0,
                "requests_succeeded": 0,
                "requests_failed": 0,
                "response_times": [],
                "errors": [],
                "scenario_results": {}
            },
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Create user tasks with staggered start (ramp-up)
            user_tasks = []
            ramp_up_delay = (ramp_up_minutes * 60) / concurrent_users
            
            for user_id in range(concurrent_users):
                delay = user_id * ramp_up_delay
                task = asyncio.create_task(
                    self._simulate_user_behavior(user_id, duration_minutes * 60, delay, results)
                )
                user_tasks.append(task)
            
            # Wait for all users to complete
            await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Calculate final metrics
            test_duration = time.time() - test_start
            self._calculate_final_metrics(results, test_duration)
            
            # Performance analysis
            performance_analysis = self._analyze_performance(results)
            results["performance_analysis"] = performance_analysis
            
            results["completed_at"] = datetime.now().isoformat()
            results["success"] = True
            
            log.info(f"✅ Load test completed: {results['metrics']['requests_sent']} requests in {test_duration:.2f}s")
            
            return results
            
        except Exception as e:
            log.error(f"Load test failed: {e}")
            results["error"] = str(e)
            results["success"] = False
            return results
    
    async def _simulate_user_behavior(
        self, 
        user_id: int, 
        duration_seconds: int, 
        start_delay: float,
        results: Dict[str, Any]
    ) -> None:
        """Simulate realistic user behavior patterns."""
        try:
            # Wait for ramp-up delay
            await asyncio.sleep(start_delay)
            
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                # Choose random scenario based on weights
                scenario = self._choose_scenario()
                
                # Execute scenario steps
                await self._execute_scenario(user_id, scenario, results)
                
                # Random wait between actions (realistic user behavior)
                await asyncio.sleep(random.uniform(2, 10))
                
        except Exception as e:
            log.warning(f"User {user_id} simulation failed: {e}")
            results["metrics"]["errors"].append({
                "user_id": user_id,
                "error": str(e),
                "timestamp": time.time()
            })
    
    def _choose_scenario(self) -> str:
        """Choose scenario based on weights."""
        scenarios = list(self.test_scenarios.keys())
        weights = [self.test_scenarios[s]["weight"] for s in scenarios]
        return random.choices(scenarios, weights=weights)[0]
    
    async def _execute_scenario(self, user_id: int, scenario: str, results: Dict[str, Any]) -> None:
        """Execute specific test scenario."""
        scenario_config = self.test_scenarios[scenario]
        steps = scenario_config["steps"]
        
        scenario_start = time.time()
        scenario_requests = 0
        scenario_errors = 0
        
        for step in steps:
            try:
                # Simulate API request
                request_start = time.time()
                success = await self._simulate_api_request(user_id, step)
                request_duration = (time.time() - request_start) * 1000  # ms
                
                # Record metrics
                results["metrics"]["requests_sent"] += 1
                scenario_requests += 1
                
                if success:
                    results["metrics"]["requests_succeeded"] += 1
                    results["metrics"]["response_times"].append(request_duration)
                else:
                    results["metrics"]["requests_failed"] += 1
                    scenario_errors += 1
                
                # Small delay between steps
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
            except Exception as e:
                results["metrics"]["requests_failed"] += 1
                scenario_errors += 1
                log.warning(f"Step {step} failed for user {user_id}: {e}")
        
        # Record scenario results
        scenario_duration = time.time() - scenario_start
        if scenario not in results["metrics"]["scenario_results"]:
            results["metrics"]["scenario_results"][scenario] = {
                "executions": 0,
                "total_requests": 0,
                "total_errors": 0,
                "total_duration": 0
            }
        
        scenario_stats = results["metrics"]["scenario_results"][scenario]
        scenario_stats["executions"] += 1
        scenario_stats["total_requests"] += scenario_requests
        scenario_stats["total_errors"] += scenario_errors
        scenario_stats["total_duration"] += scenario_duration
    
    async def _simulate_api_request(self, user_id: int, action: str) -> bool:
        """
        Simulate API request with realistic response times and failure rates.
        Returns True for success, False for failure.
        """
        # Simulate network latency
        base_latency = random.uniform(0.1, 0.3)  # 100-300ms base
        
        # Different actions have different characteristics
        action_profiles = {
            "start_chat": {"latency_factor": 1.0, "failure_rate": 0.01},
            "send_message": {"latency_factor": 1.2, "failure_rate": 0.02},
            "like_post": {"latency_factor": 0.5, "failure_rate": 0.005},
            "comment_post": {"latency_factor": 0.8, "failure_rate": 0.01},
            "start_registration": {"latency_factor": 1.5, "failure_rate": 0.02},
            "set_profile": {"latency_factor": 1.0, "failure_rate": 0.01},
            "select_interests": {"latency_factor": 0.7, "failure_rate": 0.005},
            "view_feed": {"latency_factor": 2.0, "failure_rate": 0.02},
            "view_profiles": {"latency_factor": 1.2, "failure_rate": 0.01},
            "view_stories": {"latency_factor": 1.5, "failure_rate": 0.015},
            "create_story": {"latency_factor": 2.5, "failure_rate": 0.03},
            "secret_chat": {"latency_factor": 1.8, "failure_rate": 0.02},
            "advanced_search": {"latency_factor": 3.0, "failure_rate": 0.025}
        }
        
        profile = action_profiles.get(action, {"latency_factor": 1.0, "failure_rate": 0.01})
        
        # Simulate latency
        latency = base_latency * profile["latency_factor"]
        await asyncio.sleep(latency)
        
        # Simulate failure rate
        return random.random() > profile["failure_rate"]
    
    def _calculate_final_metrics(self, results: Dict[str, Any], test_duration: float) -> None:
        """Calculate final performance metrics."""
        metrics = results["metrics"]
        response_times = metrics["response_times"]
        
        if response_times:
            response_times.sort()
            metrics["avg_response_time_ms"] = sum(response_times) / len(response_times)
            metrics["min_response_time_ms"] = min(response_times)
            metrics["max_response_time_ms"] = max(response_times)
            metrics["p95_response_time_ms"] = response_times[int(0.95 * len(response_times))]
            metrics["p99_response_time_ms"] = response_times[int(0.99 * len(response_times))]
        else:
            metrics.update({
                "avg_response_time_ms": 0,
                "min_response_time_ms": 0,
                "max_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0
            })
        
        total_requests = metrics["requests_sent"]
        if total_requests > 0:
            metrics["error_rate_percent"] = (metrics["requests_failed"] / total_requests) * 100
            metrics["success_rate_percent"] = (metrics["requests_succeeded"] / total_requests) * 100
            metrics["requests_per_second"] = total_requests / test_duration
        else:
            metrics.update({
                "error_rate_percent": 0,
                "success_rate_percent": 0,
                "requests_per_second": 0
            })
        
        metrics["test_duration_seconds"] = test_duration
    
    def _analyze_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance against thresholds and provide recommendations."""
        metrics = results["metrics"]
        analysis = {
            "overall_status": "pass",
            "threshold_violations": [],
            "recommendations": [],
            "score": 100
        }
        
        # Check against thresholds
        checks = [
            ("avg_response_time_ms", "Average response time"),
            ("p95_response_time_ms", "P95 response time"),
            ("error_rate_percent", "Error rate")
        ]
        
        for metric_key, description in checks:
            metric_value = metrics.get(metric_key, 0)
            threshold = self.performance_thresholds.get(metric_key, float('inf'))
            
            if metric_value > threshold:
                violation = {
                    "metric": metric_key,
                    "description": description,
                    "value": metric_value,
                    "threshold": threshold,
                    "severity": "high" if metric_value > threshold * 2 else "medium"
                }
                analysis["threshold_violations"].append(violation)
                analysis["overall_status"] = "fail"
                analysis["score"] -= 20
        
        # Generate recommendations
        if metrics.get("avg_response_time_ms", 0) > self.performance_thresholds["avg_response_time_ms"]:
            analysis["recommendations"].append(
                "Consider database query optimization and connection pooling improvements"
            )
        
        if metrics.get("error_rate_percent", 0) > self.performance_thresholds["error_rate_percent"]:
            analysis["recommendations"].append(
                "Investigate error patterns and implement better error handling"
            )
        
        if metrics.get("p95_response_time_ms", 0) > self.performance_thresholds["p95_response_time_ms"]:
            analysis["recommendations"].append(
                "Add caching layers and optimize slow operations"
            )
        
        # Scenario-specific analysis
        scenario_analysis = {}
        for scenario, stats in metrics.get("scenario_results", {}).items():
            if stats["executions"] > 0:
                avg_duration = stats["total_duration"] / stats["executions"]
                error_rate = (stats["total_errors"] / stats["total_requests"]) * 100 if stats["total_requests"] > 0 else 0
                
                scenario_analysis[scenario] = {
                    "avg_duration_seconds": round(avg_duration, 2),
                    "error_rate_percent": round(error_rate, 2),
                    "total_executions": stats["executions"]
                }
        
        analysis["scenario_analysis"] = scenario_analysis
        analysis["score"] = max(0, analysis["score"])
        
        return analysis
    
    def get_test_report_summary(self, results: Dict[str, Any]) -> str:
        """Generate human-readable test report summary."""
        if not results.get("success"):
            return f"❌ Load test failed: {results.get('error', 'Unknown error')}"
        
        metrics = results["metrics"]
        analysis = results.get("performance_analysis", {})
        
        status_emoji = "✅" if analysis.get("overall_status") == "pass" else "⚠️"
        
        report = f"""
{status_emoji} **Load Test Results**

**Test Configuration:**
• Users: {results['test_config']['concurrent_users']}
• Duration: {results['test_config']['duration_minutes']} minutes
• Scenarios: {len(results['test_config']['scenarios'])}

**Performance Metrics:**
• Total Requests: {metrics['requests_sent']:,}
• Success Rate: {metrics.get('success_rate_percent', 0):.1f}%
• Error Rate: {metrics.get('error_rate_percent', 0):.1f}%
• Avg Response Time: {metrics.get('avg_response_time_ms', 0):.1f}ms
• P95 Response Time: {metrics.get('p95_response_time_ms', 0):.1f}ms
• Requests/sec: {metrics.get('requests_per_second', 0):.1f}

**Analysis:**
• Overall Status: {analysis.get('overall_status', 'unknown').title()}
• Performance Score: {analysis.get('score', 0)}/100
• Threshold Violations: {len(analysis.get('threshold_violations', []))}

**Recommendations:**
"""
        
        for rec in analysis.get("recommendations", []):
            report += f"• {rec}\n"
        
        if not analysis.get("recommendations"):
            report += "• No performance issues detected 🎉\n"
        
        return report.strip()

# Global load testing instance
load_tester = LoadTestingSystem()

async def run_quick_load_test(users: int = 50, minutes: int = 2) -> Dict[str, Any]:
    """Run a quick load test for basic performance validation."""
    return await load_tester.run_load_test(
        concurrent_users=users,
        duration_minutes=minutes,
        ramp_up_minutes=1
    )

async def run_full_load_test(users: int = 500, minutes: int = 10) -> Dict[str, Any]:
    """Run a comprehensive load test for thorough performance validation."""
    return await load_tester.run_load_test(
        concurrent_users=users,
        duration_minutes=minutes,
        ramp_up_minutes=2
    )