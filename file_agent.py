import os
import shutil
import time
from typing import Optional, Dict, Any
from agent import BaseAgent
from utils import get_logger

logger = get_logger("file_agent")

class FileAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus = None):
        super().__init__(agent_id or f"file_{int(time.time())}", message_bus)
        self.capabilities = ["file_io", "file_search", "file_copy"]

    def initialize(self):
        super().initialize()
        self.logger.info("File agent initialized")
        self.publish_state("agent_capabilities", {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        })

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a file operation task"""
        task_id = payload.get("task_id", "unknown")
        operation = payload.get("operation", "")
        params = payload.get("params", {})

        self.logger.info(f"Executing file task {task_id}: {operation}")

        result = {
            "task_id": task_id,
            "operation": operation,
            "status": "completed",
            "timestamp": time.time()
        }

        try:
            if operation == "read":
                file_path = params.get("file_path")
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    result["content"] = content
                    result["size"] = len(content)
                else:
                    raise FileNotFoundError(f"File not found: {file_path}")

            elif operation == "write":
                file_path = params.get("file_path")
                content = params.get("content", "")
                mode = params.get("mode", "w")
                with open(file_path, mode, encoding='utf-8') as f:
                    f.write(content)
                result["bytes_written"] = len(content.encode('utf-8'))

            elif operation == "copy":
                src = params.get("source")
                dst = params.get("destination")
                if src and dst:
                    shutil.copy2(src, dst)
                    result["copied_to"] = dst
                else:
                    raise ValueError("Source and destination required for copy")

            elif operation == "search":
                directory = params.get("directory", ".")
                pattern = params.get("pattern", "*")
                # Simple implementation - in practice would use glob or regex
                matches = []
                for root, dirs, files in os.walk(directory):
                    for f in files:
                        if pattern in f:
                            matches.append(os.path.join(root, f))
                result["matches"] = matches
                result["count"] = len(matches)

            elif operation == "list":
                directory = params.get("directory", ".")
                if os.path.isdir(directory):
                    items = os.listdir(directory)
                    result["items"] = items
                    result["count"] = len(items)
                else:
                    raise NotADirectoryError(f"Not a directory: {directory}")

            else:
                raise ValueError(f"Unknown file operation: {operation}")

            result["status"] = "success"

        except Exception as e:
            self.logger.error(f"File task {task_id} failed: {e}", exc_info=True)
            task_type = payload.get("task_type", "file_operation")
            description = payload.get("description", "")
            result = {
                "task_id": task_id,
                "task_type": task_type,
                "description": description,
                "status": "failed",
                "error": str(e),
                "_timestamp": time.time()
            }

        # Publish result
        self.publish_state(f"file_result_{task_id}", result)

        # Notify supervisor
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"File task {task_id} completed with status: {result.get('status')}")

    def handle_query(self, payload: Dict[str, Any]):
        """Handle file-related queries"""
        query_type = payload.get("type")
        if query_type == "exists":
            file_path = payload.get("file_path")
            exists = os.path.exists(file_path) if file_path else False
            requester = payload.get("from")
            if requester:
                self.send_message(requester, "query_response", {
                    "query": payload,
                    "result": {"exists": exists, "file_path": file_path}
                })