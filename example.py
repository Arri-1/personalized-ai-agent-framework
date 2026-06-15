"""
Continuous AI Agent Service
"""
import time
import os
import shutil
import json
from supervisor import SupervisorAgent
from research_agent import ResearchAgent
from data_agent import DataAgent
from workflow_agent import WorkflowAgent
from file_agent import FileAgent
from communication_agent import CommunicationAgent
from monitoring_agent import MonitoringAgent
from summary_agent import SummaryAgent
from workflow_agent import WorkflowAgent

def main():
    print("Starting AI Agent Framework as continuous service...")

    # Ensure directories exist
    tasks_input_dir = os.path.join(os.path.dirname(__file__), "tasks_input")
    tasks_archive_dir = os.path.join(os.path.dirname(__file__), "tasks_archive")
    os.makedirs(tasks_input_dir, exist_ok=True)
    os.makedirs(tasks_archive_dir, exist_ok=True)

    # Start supervisor
    print("\n1. Starting Supervisor Agent...")
    supervisor = SupervisorAgent()
    supervisor.initialize()

    # Create agents
    print("\n2. Creating Research Agent...")
    researcher = ResearchAgent()
    researcher.initialize()

    print("\n3. Creating Data Agent...")
    data_agent = DataAgent()
    data_agent.initialize()

    print("\n4. Creating Workflow Agent...")
    workflow_agent = WorkflowAgent()
    workflow_agent.initialize()

    print("\n5. Creating File Agent...")
    file_agent = FileAgent()
    file_agent.initialize()

    print("\n6. Creating Communication Agent...")
    comm_agent = CommunicationAgent()
    comm_agent.initialize()

    print("\n7. Creating Monitoring Agent...")
    monitor_agent = MonitoringAgent()
    monitor_agent.initialize()

    print("\n8. Creating Summary Agent...")
    summary_agent = SummaryAgent()
    summary_agent.initialize()

    print("\n9. Creating Work Flow Agent...")
    workflow_agent = WorkflowAgent()
    workflow_agent.initialize()

    # Give agents time to register
    time.sleep(2)

    # Assign a research task
    print("\n8. Assigning Research Task...")
    research_task_id = supervisor.assign_task(
        task_type="research",
        payload={
            "query": "latest AI agent frameworks 2024",
            "max_results": 10
        }
    )
    print(f"   Assigned research task ID: {research_task_id}")

    # Assign a data task
    print("\n9. Assigning Data Task...")
    data_task_id = supervisor.assign_task(
        task_type="data_processing",
        payload={
            "operation": "analyze",
            "file_path": "sample_data.csv"  # We'll create a sample CSV file below
        }
    )
    print(f"   Assigned data task ID: {data_task_id}")

    # Create a sample CSV file for the data task to process
    sample_csv_path = os.path.join(os.path.dirname(__file__), "sample_data.csv")
    if not os.path.exists(sample_csv_path):
        # Create a simple CSV file with some data
        csv_data = """name,age,score,category
Alice,25,85.5,A
Bob,30,92.0,B
Charlie,35,78.5,A
Diana,28,88.0,B
Eve,32,95.0,A
"""
        with open(sample_csv_path, 'w') as f:
            f.write(csv_data)
        print(f"   Created sample data file: {sample_csv_path}")

    # Assign a workflow task with report generation
    print("\n10. Assigning Workflow Task (with report generation)...")
    workflow_task_id = supervisor.assign_task(
        task_type="workflow_execution",
        payload={
            "description": "Renewable energy analysis pipeline",
            "generate_report": True,  # Flag to generate a report
            "workflow": {
                "steps": [
                    {"name": "data_collection", "action": "gather_renewable_data"},
                    {"name": "analysis", "action": "statistical_analysis"},
                    {"name": "report", "action": "generate_report"}
                ]
            }
        }
    )
    print(f"    Assigned workflow task ID: {workflow_task_id}")

    print("\nWaiting for initial tasks to complete...")
    time.sleep(5)  # Wait for 5 seconds to allow tasks to process

    print("\nEntering continuous processing loop (Ctrl+C to stop)...")
    try:
        while True:
            # Check for new task files
            json_files = [f for f in os.listdir(tasks_input_dir) if f.endswith('.json')]
            if json_files:
                print(f"\nFound {len(json_files)} task file(s) to process")
                for filename in json_files:
                    filepath = os.path.join(tasks_input_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # Handle both single task and list of tasks
                        tasks = data if isinstance(data, list) else [data]

                        for i, task_spec in enumerate(tasks):
                            task_type = task_spec.get("type")
                            payload = task_spec.get("payload", {})
                            if not task_type:
                                print(f"  Skipping task {i} in {filename}: missing 'type'")
                                continue

                            print(f"  Assigning task: {task_type} from {filename}")
                            task_id = supervisor.assign_task(task_type, payload)
                            print(f"    Assigned task ID: {task_id}")

                            # Map task type to agent instance for synchronous execution
                            agent_map = {
                                "research": researcher,
                                "data_processing": data_agent,
                                "workflow_execution": workflow_agent,
                                "summary": summary_agent,
                                "file_operations": file_agent,
                                "communication": comm_agent,
                                "monitoring": monitor_agent
                            }
                            agent = agent_map.get(task_type)
                            if agent is None:
                                print(f"  No agent mapped for task type {task_type}")
                                continue

                            # Prepare payload as expected by agent.execute_task: include task_id, task_type, and the original payload
                            task_payload = {
                                "task_id": task_id,
                                "task_type": task_type,
                                **payload
                            }
                            print(f"  Executing task {task_id} directly on {task_type} agent...")
                            agent.execute_task(task_payload)
                            # Agent will update blackboard and send completion message via supervisor

                        # Move processed file to archive
                        archive_path = os.path.join(tasks_archive_dir, filename)
                        shutil.move(filepath, archive_path)
                        print(f"  Moved {filename} to archive")

                    except Exception as e:
                        print(f"  Error processing {filename}: {e}")
                        # Optionally move to error folder or leave for retry
            else:
                # No files, just idle
                pass

            # Sleep before next check
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nReceived shutdown signal...")
    finally:
        # Shutdown agents gracefully
        print("\nShutting down agents...")
        supervisor.shutdown()
        researcher.shutdown()
        data_agent.shutdown()
        workflow_agent.shutdown()
        file_agent.shutdown()
        comm_agent.shutdown()
        monitor_agent.shutdown()
        print("Service stopped.")

if __name__ == "__main__":
    main()