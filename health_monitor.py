import time
import psutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SystemHealthMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.api_latency = []
        self.error_count = 0
        self.last_heartbeat = time.time()
        
    def check_system_health(self):
        """
        HFT Algo 11.1: System Health Monitor
        Checks CPU, Memory, API Latency, and Error rates.
        """
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent
        uptime = time.time() - self.start_time
        
        status = "HEALTHY"
        issues = []
        
        if cpu_usage > 90:
            status = "CRITICAL"
            issues.append(f"High CPU Usage: {cpu_usage}%")
        elif cpu_usage > 80:
            status = "WARNING"
            issues.append(f"Elevated CPU Usage: {cpu_usage}%")
            
        if memory_usage > 85:
            status = "CRITICAL"
            issues.append(f"High Memory Usage: {memory_usage}%")
            
        avg_latency = sum(self.api_latency[-100:]) / len(self.api_latency[-100:]) if self.api_latency else 0
        if avg_latency > 0.5: # 500ms
            status = "WARNING"
            issues.append(f"High API Latency: {avg_latency*1000:.2f}ms")
            
        return {
            "status": status,
            "issues": issues,
            "metrics": {
                "cpu": cpu_usage,
                "memory": memory_usage,
                "uptime_seconds": int(uptime),
                "avg_latency_ms": round(avg_latency * 1000, 2),
                "error_count": self.error_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
    def log_api_call(self, duration):
        self.api_latency.append(duration)
        if len(self.api_latency) > 1000:
            self.api_latency.pop(0)

    def log_error(self):
        self.error_count += 1
