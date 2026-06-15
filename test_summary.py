#!/usr/bin/env python3
"""
Test script for SummaryAgent: sets up mock research data in blackboard.json,
runs SummaryAgent.execute_task, and prints logs and result.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from summary_agent import SummaryAgent

def setup_mock_blackboard():
    mock_blackboard = {
        "blackboard": {
            "research_result_1": {
                "query": "quantum error correction 2024",
                "summary": "Recent advances in quantum error correction include surface code improvements.",
                "results": [
                    {
                        "title": "Surface Code Breakthrough",
                        "url": "https://example.com/surface",
                        "snippet": "Researchers achieved 50% error reduction."
                    }
                ],
                "_timestamp": 1781472474
            },
            "research_result_2": {
                "query": "room temperature qubits",
                "summary": "Diamond-based qubits achieve coherence at room temperature.",
                "results": [
                    {
                        "title": "Room-Temperature Qubits",
                        "url": "https://example.com/diamond",
                        "snippet": "Coherence times of 2 ms at 300K."
                    }
                ],
                "_timestamp": 1781472133
            }
        },
        "logs": []
    }
    blackboard_path = os.path.join(os.path.dirname(__file__), "blackboard.json")
    with open(blackboard_path, 'w', encoding='utf-8') as f:
        json.dump(mock_blackboard, f, indent=2)
    print(f"Mock blackboard written to {blackboard_path}")

def main():
    print("=== SummaryAgent Test ===")
    setup_mock_blackboard()

    # Create and initialize agent
    agent = SummaryAgent(agent_id="test_summary_agent")
    agent.initialize()

    # Prepare task payload
    payload = {
        "task_id": "test_summary_task_001",
        "description": "Summarize mock research data"
    }
    print(f"\nExecuting task: {payload}")

    # Execute the task
    agent.execute_task(payload)

    # Give a moment for any async operations (though execute_task is synchronous)
    import time
    time.sleep(1)

    # Read blackboard to see results
    blackboard_path = os.path.join(os.path.dirname(__file__), "blackboard.json")
    try:
        with open(blackboard_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Extract summary results if present
        summary_results = data.get("blackboard", {}).get("summary_results")
        if summary_results:
            print("\n=== Summary Result (from blackboard) ===")
            print(json.dumps(summary_results, indent=2))
        else:
            # Also check for published state via message bus? Not needed.
            print("\nNo summary_results found in blackboard.")
    except Exception as e:
        print(f"\nError reading blackboard: {e}")

if __name__ == "__main__":
    main()