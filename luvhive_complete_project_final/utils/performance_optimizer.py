# utils/performance_optimizer.py - MS DHONI MODE 🏏
"""
MS Dhoni Performance Mode: Keep the bot cool, calm, and efficient!
Captain Cool never panics under pressure - neither should our bot!
"""

import os
import psutil
import time
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import registration as reg

log = logging.getLogger("luvbot.performance")

class MSDhoniOptimizer:
    """Captain Cool Performance Optimizer - Keeps bot calm under pressure"""
    
    def __init__(self):
        self.cpu_threshold_normal = 70.0  # Normal mode threshold
        self.cpu_threshold_cool = 80.0    # Cool mode threshold (lowered from 85%)
        self.cpu_samples = []
        self.max_samples = 10
        self.cool_mode_active = False
        self.last_optimization = datetime.now()
        
        # Performance metrics
        self.metrics = {
            'cpu_peaks': 0,
            'optimizations_applied': 0,
            'database_errors_prevented': 0,
            'total_uptime': 0
        }
        
        # Force initial CPU check
        current_cpu = self.get_cpu_usage()
        if current_cpu > self.cpu_threshold_cool:
            self.cool_mode_active = True
            log.warning(f"🏏 STARTUP: MS Dhoni Cool Mode activated - CPU: {current_cpu:.1f}%")
        
        log.info("🏏 MS Dhoni Performance Optimizer initialized - Captain Cool mode activated!")
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=1)
        except Exception as e:
            log.warning(f"❌ Could not get CPU usage: {e}")
            return 0.0
    
    def add_cpu_sample(self, cpu_percent: float):
        """Add CPU sample and maintain rolling average"""
        self.cpu_samples.append(cpu_percent)
        if len(self.cpu_samples) > self.max_samples:
            self.cpu_samples.pop(0)
    
    def get_avg_cpu(self) -> float:
        """Get average CPU usage from samples"""
        if not self.cpu_samples:
            return 0.0
        return sum(self.cpu_samples) / len(self.cpu_samples)
    
    def should_activate_cool_mode(self) -> bool:
        """Check if we should activate Captain Cool mode"""
        current_cpu = self.get_cpu_usage()
        self.add_cpu_sample(current_cpu)
        avg_cpu = self.get_avg_cpu()
        
        # Activate cool mode if sustained high CPU (lowered threshold for faster activation)
        if avg_cpu > self.cpu_threshold_cool and len(self.cpu_samples) >= 3:  # Reduced from 5 to 3
            if not self.cool_mode_active:
                log.warning(f"🏏 ACTIVATING MS DHONI COOL MODE - CPU: {avg_cpu:.1f}%")
                self.cool_mode_active = True
                self.metrics['cpu_peaks'] += 1
            return True
        
        # Also activate if current CPU is extremely high (immediate activation)
        elif current_cpu > 80.0:  # Lowered from 90.0 to 80.0
            if not self.cool_mode_active:
                log.warning(f"🏏 EMERGENCY MS DHONI COOL MODE - CPU: {current_cpu:.1f}%")
                self.cool_mode_active = True
                self.metrics['cpu_peaks'] += 1
            return True
        
        # Deactivate if CPU is stable
        elif avg_cpu < self.cpu_threshold_normal and self.cool_mode_active:
            log.info(f"✅ MS Dhoni Cool Mode deactivated - CPU stable: {avg_cpu:.1f}%")
            self.cool_mode_active = False
            
        return self.cool_mode_active
    
    def get_optimized_polling_interval(self) -> int:
        """Get optimal polling interval based on current load"""
        if self.cool_mode_active:
            # Captain Cool mode - slow down polling
            return 15  # 15 seconds instead of default ~10
        else:
            # Normal mode
            return 10  # Default polling
    
    def optimize_database_connections(self):
        """Optimize database connection usage"""
        try:
            # Force connection pool cleanup
            if hasattr(reg, '_pool') and reg._pool:
                # Close idle connections
                reg._pool.closeall()
                log.info("🔧 Database connection pool optimized")
                self.metrics['database_errors_prevented'] += 1
        except Exception as e:
            log.warning(f"⚠️ DB optimization warning: {e}")
    
    def apply_cpu_optimizations(self):
        """Apply various CPU optimizations when under pressure"""
        # Always check and update cool mode status
        cool_mode_needed = self.should_activate_cool_mode()
        
        if not cool_mode_needed:
            return
        
        optimizations_applied = 0
        
        # 1. Optimize database connections
        self.optimize_database_connections()
        optimizations_applied += 1
        
        # 2. Reduce logging verbosity temporarily
        if log.level < logging.WARNING:
            log.setLevel(logging.WARNING)
            optimizations_applied += 1
        
        # 3. Sleep briefly to let CPU recover
        time.sleep(0.5)
        optimizations_applied += 1
        
        self.metrics['optimizations_applied'] += optimizations_applied
        self.last_optimization = datetime.now()
        
        log.info(f"🏏 MS Dhoni optimizations applied: {optimizations_applied}")
    
    def get_performance_report(self) -> str:
        """Get current performance status report"""
        current_cpu = self.get_cpu_usage()
        avg_cpu = self.get_avg_cpu()
        
        status = "🏏 CAPTAIN COOL" if self.cool_mode_active else "⚡ NORMAL MODE"
        
        report = f"""
🏏 MS DHONI PERFORMANCE REPORT

📊 CURRENT STATUS: {status}
🔥 Current CPU: {current_cpu:.1f}%
📈 Average CPU: {avg_cpu:.1f}% (last {len(self.cpu_samples)} samples)
🎯 Polling Interval: {self.get_optimized_polling_interval()}s

📈 PERFORMANCE METRICS:
• CPU Peaks Handled: {self.metrics['cpu_peaks']}
• Optimizations Applied: {self.metrics['optimizations_applied']}
• Database Errors Prevented: {self.metrics['database_errors_prevented']}

🏏 Captain Cool keeps the bot steady under pressure!
"""
        return report.strip()
    
    async def monitor_and_optimize(self):
        """Continuous monitoring and optimization (like Dhoni's captaincy)"""
        log.info("🏏 MS Dhoni monitoring started - Captain Cool watching the game")
        
        while True:
            try:
                # Check current CPU and update cool mode status
                current_cpu = self.get_cpu_usage()
                self.add_cpu_sample(current_cpu)
                
                # Check if we should activate/deactivate cool mode
                prev_cool_mode = self.cool_mode_active
                self.should_activate_cool_mode()
                
                # Log status change
                if prev_cool_mode != self.cool_mode_active:
                    status = "ACTIVATED" if self.cool_mode_active else "DEACTIVATED"
                    log.info(f"🏏 MS Dhoni Cool Mode {status} - CPU: {current_cpu:.1f}%")
                
                # Apply optimizations if needed
                self.apply_cpu_optimizations()
                
                # Wait before next check (adaptive interval)
                wait_time = 15 if self.cool_mode_active else 30
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                log.error(f"❌ MS Dhoni monitoring error: {e}")
                await asyncio.sleep(30)

# Global optimizer instance
dhoni_optimizer = MSDhoniOptimizer()

def get_performance_optimizer():
    """Get the global performance optimizer"""
    return dhoni_optimizer

def apply_ms_dhoni_mode():
    """Apply MS Dhoni performance optimizations immediately"""
    dhoni_optimizer.apply_cpu_optimizations()
    return dhoni_optimizer.get_performance_report()

def get_optimized_polling_interval() -> int:
    """Get current optimized polling interval"""
    return dhoni_optimizer.get_optimized_polling_interval()

def is_cool_mode_active() -> bool:
    """Check if Captain Cool mode is currently active"""
    return dhoni_optimizer.cool_mode_active