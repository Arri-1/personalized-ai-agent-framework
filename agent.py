import json
import os
import uuid
import time
import queue
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from message_bus import MessageBus
from utils import get_logger

class BaseAgent(ABC):
    def __init__(self, agent_id: Optional[str] = None, message_bus: Optional[MessageBus] = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.message_bus = message_bus or MessageBus()
        self.logger = get_logger(f"agent_{self.agent_id}")
        self.state: Dict[str, Any] = {}
        self.running = False
        # Internal task queue for deferring task execution
        self._task_queue = queue.Queue()
        # Worker thread for processing tasks from the internal queue
        self._worker_thread = None
        # Topic for receiving messages (tasks and direct messages)
        self._message_topic = f"agent_messages_{self.agent_id}"

    def initialize(self):
        """Initialize the agent"""
        self.logger.info(f"Initializing agent {self.agent_id}")
        self.running = True
        # Start the worker thread for processing tasks
        self._worker_thread = threading.Thread(target=self._process_task_queue, daemon=True)
        self._worker_thread.start()
        # Subscribe to the agent's message topic for all incoming messages
        self.message_bus.subscribe(self._message_topic, self.handle_message)
        # Publish presence to blackboard
        self.message_bus.publish("agent_registry", {
            "agent_id": self.agent_id,
            "status": "initialized",
            "timestamp": time.time()
        })

    def shutdown(self):
        """Shutdown the agent"""
        self.logger.info(f"Shutting down agent {self.agent_id}")
        self.running = False
        # Wake up the worker thread if it's waiting on the queue
        self._task_queue.put(None)
        # Wait for the worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        # Unsubscribe from the message topic
        self.message_bus.unsubscribe(self._message_topic, self.handle_message)
        # Publish presence to blackboard
        self.message_bus.publish("agent_registry", {
            "agent_id": self.agent_id,
            "status": "shutdown",
            "timestamp": time.time()
        })

    def _process_task_queue(self):
        """Worker thread function to process tasks from the internal queue"""
        while self.running:
            try:
                # Get a task from the queue (blocking with timeout)
                task_payload = self._task_queue.get(timeout=0.1)
                if task_payload is None:  # Shutdown signal
                    break
                try:
                    self.execute_task(task_payload)
                except Exception as e:
                    self.logger.error(f"Error executing task: {e}", exc_info=True)
                finally:
                    self._task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error in task worker: {e}", exc_info=True)

    def handle_message(self, message: Dict[str, Any]):
        """Handle incoming messages on the agent's message topic"""
        msg_type = message.get("type")
        self.logger.debug(f"Received message: {msg_type}")

        if msg_type == "task":
            # Defer task execution to the worker thread
            payload = message.get("payload", {})
            self._task_queue.put(payload)
        elif msg_type == "control":
            # Handle control messages immediately
            payload = message.get("payload", {})
            self.handle_control(payload)
        elif msg_type == "query":
            # Handle query messages immediately
            payload = message.get("payload", {})
            self.handle_query(payload)
        else:
            self.logger.warning(f"Unknown message type: {msg_type}")

    @abstractmethod
    def execute_task(self, payload: Dict[str, Any]):
        """Execute a specific task - to be implemented by subclasses"""
        pass

    def handle_control(self, payload: Dict[str, Any]):
        """Handle control commands"""
        command = payload.get("command")
        if command == "pause":
            self.logger.info("Agent paused")
            # Could implement pausing logic
        elif command == "resume":
            self.logger.info("Agent resumed")
        elif command == "stop":
            self.shutdown()
        else:
            self.logger.warning(f"Unknown control command: {command}")

    def handle_query(self, payload: Dict[str, Any]):
        """Handle query requests"""
        # Default implementation - can be overridden
        pass

    def send_message(self, target_agent_id: str, message_type: str, payload: Dict[str, Any]):
        """Send a message to another agent"""
        target_topic = f"agent_messages_{target_agent_id}"
        message = {
            "type": message_type,
            "payload": payload,
            "from": self.agent_id,
            "timestamp": time.time()
        }
        self.message_bus.publish(target_topic, message)
        self.logger.debug(f"Sent {message_type} to {target_agent_id}")

    def publish_state(self, key: str, value: Any):
        """Publish state update to blackboard"""
        self.message_bus.publish("blackboard", {
            "key": key,
            "value": value,
            "agent_id": self.agent_id,
            "timestamp": time.time()
        })
        self.state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state from blackboard (cached locally first)"""
        if key in self.state:
            return self.state[key]
        # In a real implementation, we might query the blackboard
        return default