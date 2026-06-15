import time
import json
import os
from typing import Optional, Dict, Any
from agent import BaseAgent
from utils import get_logger

logger = get_logger("workflow_agent")

class WorkflowAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus = None):
        super().__init__(agent_id or f"workflow_{int(time.time())}", message_bus)
        self.capabilities = ["orchestration", "workflow_execution", "tool_usage", "report_generation"]

    def initialize(self):
        super().initialize()
        self.logger.info("Workflow agent initialized")
        self.publish_state("agent_capabilities", {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        })

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a workflow task"""
        task_id = payload.get("task_id", "unknown")
        task_type = payload.get("task_type", "workflow_execution")  # default to workflow_execution
        description = payload.get("description", "Unnamed workflow")
        workflow_def = payload.get("workflow", {})
        try:
            self.logger.info(f"Executing workflow task {task_id}: {description}")

            # Check if this is a report generation task
            is_report_task = (
                (task_type == "report_generation") or 
                (task_type == "workflow_execution" and payload.get("generate_report", False)) or 
                (task_type == "workflow_execution" and payload.get("task") == "generate_report") or 
                (task_type == "workflow_execution" and "report" in description.lower())
            )

            if is_report_task:
                self._generate_report(task_id, payload)
            else:
                self._execute_simulated_workflow(task_id, payload, workflow_def, description)

        except Exception as e:
            self.logger.error(f"Error processing workflow task {task_id}: {e}", exc_info=True)
            result = {
                "task_id": task_id,
                "task_type": task_type,
                "description": description,
                "status": "failed",
                "error": str(e),
                "_timestamp": time.time()
            }
            # Publish result
            self.publish_state(f"workflow_result_{task_id}", result)

            # Notify supervisor
            completion_message = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result,
                "timestamp": time.time()
            }
            self.message_bus.publish("task_completed", completion_message)

            self.logger.info(f"Workflow task {task_id} completed with status: {result.get('status')}")
            return

        # If we reach here, task succeeded
        result = {
            "task_id": task_id,
            "task_type": task_type,
            "description": description,
            "status": "completed",
            "_timestamp": time.time()
        }
        # Publish result
        self.publish_state(f"workflow_result_{task_id}", result)

        # Notify supervisor
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Workflow task {task_id} completed")

    def _generate_report(self, task_id: str, payload: Dict[str, Any]):
        """Generate a report from research and data results in the blackboard"""
        self.logger.info(f"Generating report for task {task_id}")

        # Ensure outputs directory exists
        outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(outputs_dir, exist_ok=True)

        # Read the blackboard to get research and data results
        blackboard_path = os.path.join(os.path.dirname(__file__), "blackboard.json")
        try:
            with open(blackboard_path, 'r', encoding='utf-8') as f:
                blackboard_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read blackboard: {e}")
            blackboard_data = {"blackboard": {}, "logs": []}

        blackboard = blackboard_data.get("blackboard", {})

        # Collect all research results
        research_results = []
        for key, value in blackboard.items():
            if key.startswith("research_result_") and isinstance(value, dict):
                research_results.append(value)

        # Collect all data results
        data_results = []
        for key, value in blackboard.items():
            if key.startswith("data_result_") and isinstance(value, dict):
                data_results.append(value)

        # Generate markdown report
        report_lines = []
        report_lines.append("# Market Research Report")
        report_lines.append(f"\n*Generated at: {time.ctime(time.time())}*\n")

        # Research section
        report_lines.append("## Research Findings")
        # Check for summary_results first
        summary_results = blackboard.get('summary_results')
        if summary_results and isinstance(summary_results, dict) and 'summary' in summary_results:
            summary_text = summary_results['summary']
            report_lines.append(summary_text)
            report_lines.append("")  # Add an empty line after the summary
        else:
            if research_results:
                for i, research_result in enumerate(research_results, 1):
                    query = research_result.get("query", "Unknown query")
                    summary = research_result.get("summary", "No summary available")
                    results = research_result.get("results", [])
                    report_lines.append(f"### Research #{i}: {query}")
                    report_lines.append(f"**Summary:** {summary}")
                    if results:
                        report_lines.append("\n**Results:**")
                        for j, res in enumerate(results[:5], 1):  # Top 5 results per research task
                            title = res.get("title", "No title")
                            url = res.get("url", "#")
                            snippet = res.get("snippet", "No snippet available")
                            report_lines.append(f"### {title}")
                            report_lines.append(f"*URL:* {url}")
                            report_lines.append(f"*Summary:* {snippet}")
                            report_lines.append("")
                    else:
                        report_lines.append("*No research results found*")
                    report_lines.append("")
            else:
                report_lines.append("*No research data available*")
            report_lines.append("")

        # Data section
        report_lines.append("## Data Analysis")
        if data_results:
            for i, data_result in enumerate(data_results, 1):
                operation = data_result.get("operation", "Unknown operation")
                input_size = data_result.get("input_size", 0)
                output = data_result.get("output", {})
                summary = output.get("summary", "No summary available")
                stats = output.get("statistics", {})
                report_lines.append(f"### Data Analysis #{i}: {operation}")
                report_lines.append(f"**Input Size:** {input_size} items")
                report_lines.append(f"**Summary:** {summary}")
                if stats and "columns" in stats:
                    report_lines.append("\n**Column Statistics:**")
                    for col_name, col_stats in stats["columns"].items():
                        report_lines.append(f"\n#### {col_name}")
                        if col_stats.get("type") == "numeric":
                            report_lines.append(f"- Count: {col_stats.get('count', 0)}")
                            report_lines.append(f"- Missing: {col_stats.get('missing', 0)}")
                            report_lines.append(f"- Min: {col_stats.get('min', 'N/A')}")
                            report_lines.append(f"- Max: {col_stats.get('max', 'N/A')}")
                            report_lines.append(f"- Mean: {col_stats.get('mean', 'N/A'):.2f}")
                            report_lines.append(f"- Median: {col_stats.get('median', 'N/A'):.2f}")
                            report_lines.append(f"- Std Dev: {col_stats.get('std', 'N/A'):.2f}")
                        elif col_stats.get("type") == "non-numeric":
                            report_lines.append(f"- Count: {col_stats.get('count', 0)}")
                            report_lines.append(f"- Missing: {col_stats.get('missing', 0)}")
                            report_lines.append(f"- Unique Values: {col_stats.get('unique_values', 0)}")
                        elif col_stats.get("type") == "empty":
                            report_lines.append(f"- Empty column (all missing)")
                        else:
                            report_lines.append(f"- Unknown data type")
                else:
                    report_lines.append("*No detailed statistics available*")
                report_lines.append("")  # Empty line between data tasks
        else:
            report_lines.append("*No data analysis available*")
        report_lines.append("")  # Empty line

        # Conclusion
        report_lines.append("## Conclusion")
        if research_results and data_results:
            report_lines.append("The system successfully gathered research insights from multiple sources and analyzed relevant data. ")
            report_lines.append("The research findings provide context and background, while the data analysis offers quantitative support for decision-making.")
            report_lines.append(f"\n*Total research tasks processed: {len(research_results)}*")
            report_lines.append(f"*Total data analysis tasks processed: {len(data_results)}*")
        elif research_results:
            report_lines.append("Research was completed, but no data analysis was available for this report.")
            report_lines.append(f"\n*Total research tasks processed: {len(research_results)}*")
        elif data_results:
            report_lines.append("Data analysis was completed, but no research insights were available to provide context.")
            report_lines.append(f"\n*Total data analysis tasks processed: {len(data_results)}*")
        else:
            report_lines.append("No research or data insights were available to generate a comprehensive report.")
        report_lines.append("\n---\n*Report generated by AI Agent Framework*")

        # Write the report to a file
        report_filename = f"market_research_report_{int(time.time())}.md"
        report_path = os.path.join(outputs_dir, report_filename)
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report_lines))
            self.logger.info(f"Report saved to {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to write report: {e}")
            report_path = None

        # Prepare the result
        result = {
            "task_id": task_id,
            "task_type": "report_generation",
            "description": payload.get("description", "Market research report"),
            "report_generated": report_path is not None,
            "report_path": report_path,
            "research_count": len(research_results),
            "data_count": len(data_results),
            "timestamp": time.time()
        }

        # Publish result
        self.publish_state(f"workflow_result_{task_id}", result)

        # Notify supervisor
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Workflow task {task_id} completed with report generation")

    def _execute_simulated_workflow(self, task_id: str, payload: Dict[str, Any], workflow_def: Dict, description: str):
        """Execute the original simulated workflow"""
        self.logger.info(f"Executing simulated workflow task {task_id}: {description}")

        # For now, simulate workflow execution
        time.sleep(3)
        steps = workflow_def.get("steps", [])
        if not steps:
            # Default simulated steps
            steps = [
                {"name": "step1", "action": "gather_data"},
                {"name": "step2", "action": "process_data"},
                {"name": "step3", "action": "generate_report"}
            ]

        results = []
        for i, step in enumerate(steps):
            self.logger.info(f"Executing step {i+1}: {step.get('name')}")
            time.sleep(0.5)  # Simulate step work
            step_result = {
                "step": step.get("name"),
                "status": "completed",
                "output": f"Completed {step.get('action')}",
                "timestamp": time.time()
            }
            results.append(step_result)

        result = {
            "task_id": task_id,
            "description": description,
            "steps_executed": len(results),
            "results": results,
            "output": f"Workflow '{description}' completed successfully",
            "timestamp": time.time()
        }

        # Publish result
        self.publish_state(f"workflow_result_{task_id}", result)

        # Notify supervisor
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Workflow task {task_id} completed")

    def handle_query(self, payload: Dict[str, Any]):
        """Handle workflow queries"""
        pass