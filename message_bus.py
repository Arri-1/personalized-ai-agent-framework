import json
import os
import threading
import time
from typing import Dict, List, Callable, Any, Optional
from utils import get_logger

class MessageBus:
    def __init__(self, storage_file: str = "blackboard.json"):
        self.logger = get_logger("message_bus")
        self.storage_file = storage_file
        self._lock = threading.Lock()
        # In-memory storage for queues and topics
        self.topics: Dict[str, List[Dict]] = {}  # topic -> list of messages
        self.subscribers: Dict[str, List[Callable]] = {}  # topic -> list of callbacks
        self.queues: Dict[str, List[Dict]] = {}  # queue name -> list of messages
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure storage file exists"""
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump({"blackboard": {}, "logs": []}, f)

    def _load_storage(self):
        """Load data from storage file"""
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                # For simplicity, we only load blackboard; queues are in-memory
                if "blackboard" in data:
                    # Could load persisted blackboard state here
                    pass
        except Exception as e:
            self.logger.error(f"Failed to load storage: {e}")

    def _save_storage(self):
        """Save blackboard state to storage file"""
        try:
            # In a simple implementation, we just keep blackboard in memory and persist periodically
            # For now, we'll skip complex persistence
            pass
        except Exception as e:
            self.logger.error(f"Failed to save storage: {e}")

    def publish(self, topic: str, message: Dict[str, Any]):
        """Publish a message to a topic"""
        with self._lock:
            if topic not in self.topics:
                self.topics[topic] = []
            self.topics[topic].append(message)
            # Keep only last 1000 messages per topic to prevent memory growth
            if len(self.topics[topic]) > 1000:
                self.topics[topic] = self.topics[topic][-1000:]

            # Notify subscribers
            if topic in self.subscribers:
                for callback in self.subscribers[topic]:
                    try:
                        callback(message)
                    except Exception as e:
                        self.logger.error(f"Error in subscriber callback: {e}")

            # Also treat as blackboard update if topic is "blackboard"
            if topic == "blackboard":
                self._update_blackboard(message)

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to a topic"""
        with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(callback)
        self.logger.debug(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]):
        """Unsubscribe from a topic"""
        with self._lock:
            if topic in self.subscribers and callback in self.subscribers[topic]:
                self.subscribers[topic].remove(callback)

    def publish_to_queue(self, queue_name: str, message: Dict[str, Any]):
        """Publish a message to a specific queue (point-to-point)"""
        with self._lock:
            if queue_name not in self.queues:
                self.queues[queue_name] = []
            self.queues[queue_name].append(message)
            # Keep queue size manageable
            if len(self.queues[queue_name]) > 1000:
                self.queues[queue_name] = self.queues[queue_name][-1000:]

    def consume_from_queue(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Consume a message from a queue (FIFO)"""
        with self._lock:
            if queue_name in self.queues and self.queues[queue_name]:
                return self.queues[queue_name].pop(0)
        return None

    def _update_blackboard(self, message: Dict[str, Any]):
        """Update blackboard from a message"""
        key = message.get("key")
        value = message.get("value")
        if key is not None:
            # Load current blackboard
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
            except:
                data = {"blackboard": {}, "logs": []}

            data["blackboard"][key] = value
            data["blackboard"]["_last_updated"] = time.time()

            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)