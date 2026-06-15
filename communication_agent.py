import time
import json
from typing import Optional, Dict, Any
from agent import BaseAgent
from utils import get_logger

logger = get_logger("communication_agent")

class CommunicationAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus = None):
        super().__init__(agent_id or f"comm_{int(time.time())}", message_bus)
        self.capabilities = ["http_request", "email_send", "message_publish"]

    def initialize(self):
        super().initialize()
        self.logger.info("Communication agent initialized")
        self.publish_state("agent_capabilities", {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        })

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a communication task"""
        task_id = payload.get("task_id", "unknown")
        operation = payload.get("operation", "")
        params = payload.get("params", {})

        self.logger.info(f"Executing communication task {task_id}: {operation}")

        result = {
            "task_id": task_id,
            "operation": operation,
            "status": "completed",
            "timestamp": time.time()
        }

        try:
            if operation == "http_request":
                # Simulate HTTP request
                url = params.get("url", "")
                method = params.get("method", "GET")
                time.sleep(1)  # Simulate network delay
                result["response"] = {
                    "status_code": 200,
                    "body": f"Simulated response from {url}",
                    "headers": {"Content-Type": "text/plain"}
                }

            elif operation == "email_send":
                to = params.get("to", "")
                subject = params.get("subject", "")
                body = params.get("body", "")
                # Simulate sending email
                time.sleep(0.5)
                result["message_id"] = f"<{int(time.time())}.{self.agent_id}@example.com>"
                result["sent_to"] = to

            elif operation == "message_publish":
                # Publish a message to a topic via our own message bus (for internal comms)
                topic = params.get("topic", "general")
                message = params.get("message", {})
                self.message_bus.publish(topic, {
                    "from": self.agent_id,
                    "message": message,
                    "timestamp": time.time()
                })
                result["published_to"] = topic
                result["message_id"] = str(int(time.time()))

            else:
                raise ValueError(f"Unknown communication operation: {operation}")

            result["status"] = "success"

        except Exception as e:
            self.logger.error(f"Communication task {task_id} failed: {e}", exc_info=True)
            task_type = payload.get("task_type", "communication")
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
        self.publish_state(f"comm_result_{task_id}", result)

        # Notify supervisor
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Communication task {task_id} completed with status: {result.get('status')}")

    def handle_query(self, payload: Dict[str, Any]):
        """Handle communication-related queries"""
        query_type = payload.get("type")
        if query_type == "status":
            requester = payload.get("from")
            if requester:
                self.send_message(requester, "query_response", {
                    "query": payload,
                    "result": {"agent_id": self.agent_id, "capabilities": self.capabilities, "status": "ready"}
                })