from typing import Dict, List, Optional
from utils import get_logger

logger = get_logger("tasks")

# Task registry: maps task type to required agent capabilities
TASK_REGISTRY = {
    "research": {
        "description": "Gather information from web sources",
        "required_capabilities": ["web_search", "summarization"],
        "example_agent": "research_agent"
    },
    "data_processing": {
        "description": "Process and analyze data",
        "required_capabilities": ["data_analysis", "statistics"],
        "example_agent": "data_agent"
    },
    "workflow_execution": {
        "description": "Execute a predefined workflow",
        "required_capabilities": ["orchestration", "tool_usage"],
        "example_agent": "workflow_agent"
    },
    "summary": {
        "description": "Summarize raw research data into key insights",
        "required_capabilities": ["summarization"],
        "example_agent": "summary_agent"
    },
    "file_operation": {
        "description": "Perform file operations (read/write/copy)",
        "required_capabilities": ["file_io"],
        "example_agent": "file_agent"
    },
    "custom": {
        "description": "Custom task defined by user",
        "required_capabilities": [],
        "example_agent": "custom_agent"
    }
}

def get_task_info(task_type: str) -> Optional[Dict]:
    """Get information about a task type"""
    return TASK_REGISTRY.get(task_type)

def get_agent_for_task(task_type: str) -> Optional[str]:
    """Get the recommended agent type for a given task"""
    info = get_task_info(task_type)
    return info.get("example_agent") if info else None

def validate_task_payload(task_type: str, payload: Dict) -> List[str]:
    """Validate task payload and return list of errors"""
    errors = []
    info = get_task_info(task_type)
    if not info:
        errors.append(f"Unknown task type: {task_type}")
        return errors

    # Basic validation - can be extended per task type
    required_caps = info.get("required_capabilities", [])
    if required_caps:
        # In a full implementation, we would check agent capabilities
        pass

    return errors