import time
import uuid
from typing import Dict, List, Optional, Any
from agent import BaseAgent
from message_bus import MessageBus
from tasks import get_task_info, get_agent_for_task, validate_task_payload
from utils import get_logger

logger = get_logger("supervisor")

class SupervisorAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus: Optional[MessageBus] = None):
        super().__init__(agent_id or "supervisor", message_bus)
        self.known_agents: Dict[str, Dict] = {}  # agent_id -> info
        self.task_counter = 0

    def initialize(self):
        super().initialize()
        self.logger.info("Supervisor agent initialized")
        # Subscribe to agent registry updates
        self.message_bus.subscribe("agent_registry", self.handle_agent_registry)
        # Subscribe to completion messages
        self.message_bus.subscribe("task_completed", self.handle_task_completion)

    def handle_agent_registry(self, message: Dict[str, Any]):
        """Handle agent registration/deregistration"""
        agent_id = message.get("agent_id")
        status = message.get("status")
        if status == "initialized":
            self.known_agents[agent_id] = {
                "last_seen": time.time(),
                "status": "active",
                "capabilities": []  # Would be populated from agent's introduction message
            }
            self.logger.info(f"Agent registered: {agent_id}")
        elif status == "shutdown":
            if agent_id in self.known_agents:
                self.known_agents[agent_id]["status"] = "inactive"
                self.logger.info(f"Agent deregistered: {agent_id}")

    def handle_task_completion(self, message: Dict[str, Any]):
        """Handle task completion notifications"""
        task_id = message.get("task_id")
        agent_id = message.get("agent_id")
        result = message.get("result")
        self.logger.info(f"Task {task_id} completed by agent {agent_id}")
        # Update the task status in the blackboard to 'completed'
        current_state = self.get_state(f"task_{task_id}", {})
        if not current_state:
            # If we don't have the state, create a minimal one
            current_state = {
                "task_id": task_id,
                "assigned_to": agent_id
            }
        current_state.update({
            "status": "completed",
            "result": result,
            "completed_by": agent_id,
            "completed_at": time.time()
        })
        self.publish_state(f"task_{task_id}", current_state)
        # Could store result, notify requester, etc.

    def assign_task(self, task_type: str, payload: Dict[str, Any], target_agent_id: Optional[str] = None) -> str:
        """Assign a task to an agent"""
        task_id = str(uuid.uuid4())
        self.task_counter += 1

        # Validate task
        errors = validate_task_payload(task_type, payload)
        if errors:
            error_msg = f"Task validation failed: {', '.join(errors)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Determine target agent if not specified
        if not target_agent_id:
            target_agent_id = self._select_agent_for_task(task_type)
            if not target_agent_id:
                raise ValueError(f"No suitable agent found for task type: {task_type}")

        # Publish task message to the agent's message topic (disabled for synchronous execution)
        # task_message = {
        #     "type": "task",
        #     "payload": {
        #         "task_id": task_id,
        #         "task_type": task_type,
        #         "data": payload
        #     }
        # }
        # self.message_bus.publish(f"agent_messages_{target_agent_id}", task_message)
        self.logger.info(f"Assigned task {task_id} ({task_type}) to agent {target_agent_id} (direct execution)")

        # Publish task assignment to blackboard for tracking
        self.publish_state(f"task_{task_id}", {
            "task_id": task_id,
            "task_type": task_type,
            "assigned_to": target_agent_id,
            "status": "assigned",
            "timestamp": time.time(),
            "payload": payload
        })

        return task_id

    def _select_agent_for_task(self, task_type: str) -> Optional[str]:
        """Select the best agent for a given task type"""
        # Simple implementation: look for known agents with matching capabilities
        # In a full implementation, agents would advertise their capabilities
        task_info = get_task_info(task_type)
        if not task_info:
            return None

        example_agent = task_info.get("example_agent")
        # For now, we'll assume agents of that type exist or will be spawned
        # In practice, we might spawn a new agent of the required type
        return example_agent  # This would be the agent ID pattern

    def spawn_agent(self, agent_type: str) -> str:
        """Spawn a new agent of the specified type using Claude Code's Agent tool"""
        # This would interface with the Claude Code Agent tool
        # For now, we'll return a placeholder ID
        agent_id = f"{agent_type}_{str(uuid.uuid4())[:8]}"
        self.logger.info(f"Would spawn agent of type {agent_type} with ID {agent_id}")
        # In actual implementation, we would call:
        # agent_id = claude.agent.spawn(agent_type, config)
        return agent_id

    def handle_control(self, payload: Dict[str, Any]):
        """Handle supervisor-specific control commands"""
        command = payload.get("command")
        if command == "list_agents":
            self.publish_state("supervisor_status", {
                "known_agents": self.known_agents,
                "timestamp": time.time()
            })
        elif command == "get_task_status":
            task_id = payload.get("task_id")
            # Return task status from blackboard
        else:
            super().handle_control(payload)

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a task assigned to the supervisor"""
        task_id = payload.get("task_id", "unknown")
        task_type = payload.get("task_type", "unknown")
        data = payload.get("data", {})
        try:
            self.logger.info(f"Supervisor executing task {task_id} of type {task_type}")
            # Handle known supervisor task types
            if task_type == "list_agents":
                result = {"agents": list(self.known_agents.keys())}
            elif task_type == "get_status":
                result = self.get_system_status()
            else:
                result = {"message": f"Supervisor processed task {task_type}", "data": data}
            # Publish result
            self.publish_state(f"supervisor_task_result_{task_id}", result)
            # Notify supervisor (or any listener) of completion
            completion_message = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result,
                "timestamp": time.time()
            }
            self.message_bus.publish("task_completed", completion_message)

        except Exception as e:
            self.logger.error(f"Error in supervisor task {task_id}: {e}", exc_info=True)
            result = {
                "task_id": task_id,
                "task_type": task_type,
                "status": "failed",
                "error": str(e),
                "_timestamp": time.time()
            }
            # Publish result
            self.publish_state(f"supervisor_task_result_{task_id}", result)
            # Notify supervisor (or any listener) of completion
            completion_message = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result,
                "timestamp": time.time()
            }
            self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Supervisor task {task_id} completed")

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        return {
            "supervisor_id": self.agent_id,
            "known_agents": self.known_agents,
            "task_counter": self.task_counter,
            "timestamp": time.time()
        }