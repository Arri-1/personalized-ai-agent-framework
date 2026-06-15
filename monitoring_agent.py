import time
import psutil
from typing import Optional, Dict, Any
from agent import BaseAgent
from utils import get_logger

logger = get_logger("monitoring_agent")

class MonitoringAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus = None):
        super().__init__(agent_id or f"monitor_{int(time.time())}", message_bus)
        self.capabilities = ["system_monitor", "process_watch", "alert"]

    def initialize(self):
        super().initialize()
        self.logger.info("Monitoring agent initialized")
        self.publish_state("agent_capabilities", {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        })
        # Start a background monitoring thread (simple implementation)
        self._monitoring = True
        # In a full implementation, we'd start a thread; for now we'll just note

    def shutdown(self):
        self._monitoring = False
        super().shutdown()

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a monitoring task"""
        task_id = payload.get("task_id", "unknown")
        operation = payload.get("operation", "")
        params = payload.get("params", {})

        self.logger.info(f"Executing monitoring task {task_id}: {operation}")

        result = {
            "task_id": task_id,
            "operation": operation,
            "status": "completed",
            "timestamp": time.time()
        }

        try:
            if operation == "system_monitor":
                # Gather system metrics
                cpu_percent = psutil.cpu_percent(interval=0.5)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                result["metrics"] = {
                    "cpu_percent": cpu_percent,
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "used": memory.used,
                        "free": memory.free
                    },
                    "disk": {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percent": (disk.used / disk.total) * 100
                    }
                }

            elif operation == "process_watch":
                process_name = params.get("process_name")
                if process_name:
                    matches = []
                    for proc in psutil.process_iter(['pid', 'name']):
                        if process_name.lower() in proc.info['name'].lower():
                            matches.append(proc.info)
                    result["processes"] = matches
                    result["count"] = len(matches)
                else:
                    # List all processes
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'username']):
                        try:
                            processes.append(proc.info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    result["processes"] = processes[:10]  # Limit output
                    result["count"] = len(processes)

            elif operation == "alert":
                # Set up an alert condition (simplified)
                metric = params.get("metric")
                threshold = params.get("threshold")
                # In a full implementation, we'd register a callback
                result["alert_configured"] = {
                    "metric": metric,
                    "threshold": threshold,
                    "agent_id": self.agent_id
                }

            else:
                raise ValueError(f"Unknown monitoring operation: {operation}")

            result["status"] = "success"

        except Exception as e:
            self.logger.error(f"Monitoring task {task_id} failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)

        # Publish result
        self.publish_state(f"monitor_result_{task_id}", result)

        # Notify supervisor
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Monitoring task {task_id} completed with status: {result.get('status')}")

    def handle_query(self, payload: Dict[str, Any]):
        """Handle monitoring-related queries"""
        query_type = payload.get("type")
        if query_type == "metrics":
            # Return current system metrics
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                result = {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "timestamp": time.time()
                }
            except:
                result = {"error": "Unable to retrieve metrics"}
            requester = payload.get("from")
            if requester:
                self.send_message(requester, "query_response", {
                    "query": payload,
                    "result": result
                })